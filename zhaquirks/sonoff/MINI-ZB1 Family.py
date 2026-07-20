"""Sonoff MINI-ZB1GSP - Zigbee Smart Plug."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    foundation,
)
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster

# from zhaquirks.units import UnitOfTemperature
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_SINGLE,
    ENDPOINT_ID,
    ZHA_SEND_EVENT,
)

FAST_SCENE_PACKET_MODIFY = 0x00
FAST_SCENE_PACKET_REPORT = 0x01
FAST_SCENE_ARRAY_ITEM_TYPE = foundation.DataTypeId.uint8
FAST_SCENE_VOLTAGE_ENABLE_BIT = 0x80000000
FAST_SCENE_VOLTAGE_VALUE_MASK = 0x7FFFFFFF
PROTECTION_CURRENT_MIN_MA = 100
PROTECTION_CURRENT_MAX_MA = 16000
PROTECTION_POWER_MIN_MW = 2000
PROTECTION_POWER_MAX_MW = 3840000
PROTECTION_VOLTAGE_MIN_MV = 85000
PROTECTION_VOLTAGE_MAX_MV = 277000


def _u32_le(data: bytes) -> int:
    """Decode an unsigned little-endian 32-bit integer."""

    return int.from_bytes(data[:4], "little")


def _put_u32_le(value: int) -> list[int]:
    """Encode an unsigned little-endian 32-bit integer."""

    return list(int(value).to_bytes(4, "little"))


def _convert_signed_power(value: int) -> float:
    """Convert uint32_t two's complement power value to signed watts.

    The device reports power as a uint32_t where negative values use
    two's complement encoding (MSB = 1). The raw unit is milliwatts.
    """

    if value >= 0x80000000:
        value -= 0x100000000
    return value / 1000.0


@dataclass
class FastSceneProtection:
    """Electrical protection fast scene."""

    scene_switch: int = 1
    over_current_ma: int = 0
    over_load_mw: int = 0
    only_ext_mode_restore: int = 0
    over_voltage_mv: int = 0
    over_voltage_en: int = 0
    under_voltage_mv: int = 0
    under_voltage_en: int = 0
    auto_recover_en: int = 0
    notify_en: int = 0


@dataclass
class FastSceneState:
    """Decoded Sonoff fast scene state."""

    packet_type: int = FAST_SCENE_PACKET_REPORT
    total_num: int = 1
    current_data_index: int = 1
    protection: FastSceneProtection = field(default_factory=FastSceneProtection)


def fast_scene_array_from_payload(payload: bytes | list[int]) -> foundation.Array:
    """Wrap a fast scene payload in a ZCL array value."""

    return foundation.Array(
        type=FAST_SCENE_ARRAY_ITEM_TYPE,
        value=t.LVList[t.uint8_t, t.uint16_t](payload),
    )


def fast_scene_payload_from_array(value: Any) -> bytes:
    """Extract the fast scene payload bytes from a decoded ZCL array value."""

    if isinstance(value, foundation.Array):
        if value.value is None:
            raise ValueError("Fast scene payload is empty")
        return bytes(value.value)
    if isinstance(value, (bytes, bytearray)):
        if len(value) >= 3 and value[0] == FAST_SCENE_ARRAY_ITEM_TYPE:
            length = int.from_bytes(value[1:3], "little")
            return bytes(value[3 : 3 + length])
        return bytes(value)
    if isinstance(value, list):
        return bytes(value)
    if isinstance(value, t.LVList):
        return bytes(value)
    raise ValueError("Unsupported fast scene payload value")


def _decode_voltage(raw_value: int) -> tuple[int, int]:
    """Split a firmware voltage threshold into value and enable flag."""

    return raw_value & FAST_SCENE_VOLTAGE_VALUE_MASK, int(
        bool(raw_value & FAST_SCENE_VOLTAGE_ENABLE_BIT)
    )


def _encode_voltage(value: int, enabled: int) -> int:
    """Combine a voltage threshold value and enable flag."""

    raw_value = value & FAST_SCENE_VOLTAGE_VALUE_MASK
    if enabled:
        raw_value |= FAST_SCENE_VOLTAGE_ENABLE_BIT
    return raw_value


def decode_fast_scene_payload(
    payload: bytes | list[int] | foundation.Array,
) -> FastSceneState:
    """Decode a Sonoff fast scene payload."""

    data = fast_scene_payload_from_array(payload)
    if len(data) < 3:
        raise ValueError("Fast scene payload is too short")

    state = FastSceneState(
        packet_type=data[0],
        total_num=data[1],
        current_data_index=data[2],
    )
    idx = 3

    while idx < len(data):
        if idx + 2 > len(data):
            if all(byte == 0 for byte in data[idx:]):
                break
            raise ValueError("Fast scene TLV header is incomplete")

        scene_type = data[idx]
        scene_len = data[idx + 1]
        idx += 2

        if idx + scene_len > len(data):
            if scene_type == 0 and all(byte == 0 for byte in data[idx - 2 :]):
                break
            raise ValueError("Fast scene TLV length exceeds payload")

        scene_data = data[idx : idx + scene_len]
        idx += scene_len

        if not scene_data:
            continue

        if scene_type == 2 and len(scene_data) >= 20:
            scene_switch = scene_data[0]
            over_voltage_mv, over_voltage_en = _decode_voltage(
                _u32_le(scene_data[10:14])
            )
            under_voltage_mv, under_voltage_en = _decode_voltage(
                _u32_le(scene_data[14:18])
            )
            state.protection = FastSceneProtection(
                scene_switch=scene_switch,
                over_current_ma=_u32_le(scene_data[1:5]),
                over_load_mw=_u32_le(scene_data[5:9]),
                only_ext_mode_restore=scene_data[9],
                over_voltage_mv=over_voltage_mv,
                over_voltage_en=over_voltage_en,
                under_voltage_mv=under_voltage_mv,
                under_voltage_en=under_voltage_en,
                auto_recover_en=scene_data[18],
                notify_en=scene_data[19],
            )

    return state


def encode_fast_scene_payload(
    state: FastSceneState,
    packet_type: int = FAST_SCENE_PACKET_MODIFY,
) -> bytes:
    """Encode a Sonoff fast scene payload."""

    payload: list[int] = [
        packet_type,
        state.total_num,
        state.current_data_index,
    ]
    protection = state.protection
    payload.extend(
        [
            0x02,
            20,
            protection.scene_switch,
            *_put_u32_le(protection.over_current_ma),
            *_put_u32_le(protection.over_load_mw),
            protection.only_ext_mode_restore,
            *_put_u32_le(
                _encode_voltage(protection.over_voltage_mv, protection.over_voltage_en)
            ),
            *_put_u32_le(
                _encode_voltage(
                    protection.under_voltage_mv, protection.under_voltage_en
                )
            ),
            protection.auto_recover_en,
            protection.notify_en,
        ]
    )

    return bytes(payload)


class SonoffErrorCodeType(types.bitmap32):
    """Fault Code Type."""

    Normal = (0x07020000,)
    Overheat = (0x07020001,)
    Overload = (0x07020004,)
    Overload_And_Overheat = (0x07020005,)


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_cluster"
    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(
            name="network_led",
            id=0x0001,
            type=t.Bool,
        )
        fault_code = ZCLAttributeDef(
            id=0x0010,
            type=SonoffErrorCodeType,
            access="rp",
        )
        turbo_mode = ZCLAttributeDef(
            name="turbo_mode",
            id=0x0012,
            type=t.int16s,
        )
        delayed_power_on_state = ZCLAttributeDef(
            name="delayed_power_on_state",
            id=0x0014,
            type=t.Bool,
        )
        delayed_power_on_time = ZCLAttributeDef(
            name="delayed_power_on_time",
            id=0x0015,
            type=t.uint16_t,
        )
        external_trigger_mode = ZCLAttributeDef(
            name="external_trigger_mode",
            id=0x0016,
            type=t.uint8_t,
        )
        detach_relay = ZCLAttributeDef(
            name="detach_relay",
            id=0x0019,
            type=t.bitmap8,
        )
        local_fast_scene_configuration = ZCLAttributeDef(
            name="local_fast_scene_configuration",
            id=0x7016,
            type=foundation.Array,
        )
        accurrent_current_value = ZCLAttributeDef(
            name="accurrent_current_value",
            id=0x7004,
            type=t.uint32_t,
        )
        accurrent_voltage_value = ZCLAttributeDef(
            name="accurrent_voltage_value",
            id=0x7005,
            type=t.uint32_t,
        )
        accurrent_power_value = ZCLAttributeDef(
            name="accurrent_power_value",
            id=0x7006,
            type=t.uint32_t,
        )
        daily_forward_energy = ZCLAttributeDef(
            name="daily_forward_energy",
            id=0x7009,
            type=t.uint32_t,
        )
        monthly_forward_energy = ZCLAttributeDef(
            name="monthly_forward_energy",
            id=0x700A,
            type=t.uint32_t,
        )
        daily_reverse_energy = ZCLAttributeDef(
            name="daily_reverse_energy",
            id=0x7018,
            type=t.uint32_t,
        )
        monthly_reverse_energy = ZCLAttributeDef(
            name="monthly_reverse_energy",
            id=0x7019,
            type=t.uint32_t,
        )
        daily_run_time = ZCLAttributeDef(
            name="daily_run_time",
            id=0x701C,
            type=t.uint32_t,
        )
        total_run_time = ZCLAttributeDef(
            name="total_run_time",
            id=0x701D,
            type=t.uint32_t,
        )
        total_forward_energy = ZCLAttributeDef(
            name="total_forward_energy",
            id=0x701E,
            type=t.uint32_t,
        )
        total_reverse_energy = ZCLAttributeDef(
            name="total_reverse_energy",
            id=0x701F,
            type=t.uint32_t,
        )
        voltage_frequency = ZCLAttributeDef(
            name="voltage_frequency",
            id=0x7029,
            type=t.uint32_t,
        )
        external_trigger_event = ZCLAttributeDef(
            name="external_trigger_event",
            id=0x0028,
            type=t.uint8_t,
        )

    def __init__(self, *args, **kwargs):
        """Init and listen for fast scene attribute changes."""
        super().__init__(*args, **kwargs)
        self._fast_scene_state = FastSceneState()
        self.on_event(AttributeReadEvent.event_type, self._handle_fast_scene_change)
        self.on_event(AttributeReportedEvent.event_type, self._handle_fast_scene_change)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_fast_scene_change)
        self.on_event(AttributeWrittenEvent.event_type, self._handle_fast_scene_change)

    def _handle_fast_scene_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync fast scene state to the local config cluster."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if event.attribute_id != self.AttributeDefs.local_fast_scene_configuration.id:
            return

        values = [event.value]
        if isinstance(event, AttributeReadEvent) and event.raw_value is not event.value:
            values.append(event.raw_value)

        for value in values:
            try:
                self._fast_scene_state = decode_fast_scene_payload(value)
                break
            except (TypeError, ValueError):
                continue
        else:
            return

        if hasattr(self.endpoint, "sonoff_fast_scene_config"):
            self.endpoint.sonoff_fast_scene_config.update_fast_scene_state(
                self._fast_scene_state
            )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read fast scene configuration during pairing to populate entities."""
        await self.read_attributes(
            [self.AttributeDefs.local_fast_scene_configuration.id]
        )

    @property
    def _is_manuf_specific(self):
        return False

    def _update_attribute(self, attrid, value):
        """Fire ZHA events for external trigger action reports."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.external_trigger_event.id:
            action = EXTERNAL_ACTION_MAP.get(value)
            if action:
                self.listener_event(ZHA_SEND_EVENT, action, {"value": value})


class SonoffFastSceneConfigCluster(LocalDataCluster):
    """Local cluster for individual fast scene configuration entities."""

    cluster_id = 0xFBFD
    ep_attribute = "sonoff_fast_scene_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        protection_over_current_ma: Final = ZCLAttributeDef(id=0x0010, type=t.uint32_t)
        protection_over_load_mw: Final = ZCLAttributeDef(id=0x0011, type=t.uint32_t)
        protection_only_ext_mode_restore: Final = ZCLAttributeDef(
            id=0x0012, type=t.Bool
        )
        protection_over_voltage_mv: Final = ZCLAttributeDef(id=0x0013, type=t.uint32_t)
        protection_over_voltage_enabled: Final = ZCLAttributeDef(id=0x0014, type=t.Bool)
        protection_under_voltage_mv: Final = ZCLAttributeDef(id=0x0015, type=t.uint32_t)
        protection_under_voltage_enabled: Final = ZCLAttributeDef(
            id=0x0016, type=t.Bool
        )
        protection_auto_recover: Final = ZCLAttributeDef(id=0x0017, type=t.Bool)
        protection_notify: Final = ZCLAttributeDef(id=0x0018, type=t.Bool)

    def __init__(self, *args, **kwargs):
        """Init with conservative default fast scene state."""
        super().__init__(*args, **kwargs)
        self._fast_scene_state = FastSceneState()

    def update_fast_scene_state(self, state: FastSceneState) -> None:
        """Update local attributes from decoded fast scene state."""
        self._fast_scene_state = state
        protection = state.protection

        updates = {
            self.AttributeDefs.protection_over_current_ma.id: protection.over_current_ma,
            self.AttributeDefs.protection_over_load_mw.id: protection.over_load_mw,
            self.AttributeDefs.protection_only_ext_mode_restore.id: bool(
                protection.only_ext_mode_restore
            ),
            self.AttributeDefs.protection_over_voltage_mv.id: protection.over_voltage_mv,
            self.AttributeDefs.protection_over_voltage_enabled.id: bool(
                protection.over_voltage_en
            ),
            self.AttributeDefs.protection_under_voltage_mv.id: protection.under_voltage_mv,
            self.AttributeDefs.protection_under_voltage_enabled.id: bool(
                protection.under_voltage_en
            ),
            self.AttributeDefs.protection_auto_recover.id: bool(
                protection.auto_recover_en
            ),
            self.AttributeDefs.protection_notify.id: bool(protection.notify_en),
        }
        for attr_id, value in updates.items():
            self._update_attribute(attr_id, value)

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Merge local writes into the real fast scene aggregate attribute."""
        state = self.endpoint.sonoff_cluster._fast_scene_state

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == self.AttributeDefs.protection_over_current_ma.id:
                state.protection.over_current_ma = int(value)
            elif attr_id == self.AttributeDefs.protection_over_load_mw.id:
                state.protection.over_load_mw = int(value)
            elif attr_id == self.AttributeDefs.protection_only_ext_mode_restore.id:
                state.protection.only_ext_mode_restore = int(bool(value))
            elif attr_id == self.AttributeDefs.protection_over_voltage_mv.id:
                state.protection.over_voltage_mv = int(value)
            elif attr_id == self.AttributeDefs.protection_over_voltage_enabled.id:
                state.protection.over_voltage_en = int(bool(value))
            elif attr_id == self.AttributeDefs.protection_under_voltage_mv.id:
                state.protection.under_voltage_mv = int(value)
            elif attr_id == self.AttributeDefs.protection_under_voltage_enabled.id:
                state.protection.under_voltage_en = int(bool(value))
            elif attr_id == self.AttributeDefs.protection_auto_recover.id:
                state.protection.auto_recover_en = int(bool(value))
            elif attr_id == self.AttributeDefs.protection_notify.id:
                state.protection.notify_en = int(bool(value))

        payload = encode_fast_scene_payload(state)
        zcl_array = fast_scene_array_from_payload(payload)
        result = await self.endpoint.sonoff_cluster.write_attributes(
            {SonoffCluster.AttributeDefs.local_fast_scene_configuration.id: zcl_array}
        )
        if self._write_succeeded(result):
            self.update_fast_scene_state(state)
        return result

    @staticmethod
    def _write_succeeded(result: list) -> bool:
        """Return whether a Zigpy write_attributes response succeeded."""
        try:
            records = result[0]
        except (IndexError, TypeError):
            return False
        return all(record.status == Status.SUCCESS for record in records)


class SonoffExternalTriggerMode(types.enum8):
    """External trigger mode attribute values."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


class SonoffExternalAction(types.enum8):
    """External trigger action event values (attribute 0x0028)."""

    Single_click = 0x01
    Double_click = 0x02
    Long_press = 0x03
    Switch_on = 0x04
    Switch_off = 0x05


COMMAND_SWITCH_ON = "switch_on"
COMMAND_SWITCH_OFF = "switch_off"

EXTERNAL_ACTION_MAP = {
    SonoffExternalAction.Single_click: COMMAND_SINGLE,
    SonoffExternalAction.Double_click: COMMAND_DOUBLE,
    SonoffExternalAction.Long_press: COMMAND_HOLD,
    SonoffExternalAction.Switch_on: COMMAND_SWITCH_ON,
    SonoffExternalAction.Switch_off: COMMAND_SWITCH_OFF,
}

EXTERNAL_TRIGGER_MAP = {
    COMMAND_SINGLE: ("Single Click", "external_switch"),
    COMMAND_DOUBLE: ("Double Click", "external_switch"),
    COMMAND_HOLD: ("Long Press", "external_switch"),
    COMMAND_SWITCH_ON: (COMMAND_ON, "external_switch"),
    COMMAND_SWITCH_OFF: (COMMAND_OFF, "external_switch"),
}

(
    QuirkBuilder("SONOFF", "MINI-ZB1GSP")
    .replaces(SonoffCluster)
    .adds(SonoffFastSceneConfigCluster)
    .removes(0x0B04)
    .removes(0x0702)
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.delayed_power_on_state.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="delayed_power_on_state",
        fallback_name="Delayed power on state",
    )
    .number(
        SonoffCluster.AttributeDefs.delayed_power_on_time.name,
        SonoffCluster.cluster_id,
        min_value=0.5,
        max_value=3599.5,
        step=0.5,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        multiplier=0.5,
        translation_key="delayed_power_on_time",
        fallback_name="Delayed power on time",
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalTriggerMode,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_current_ma.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_CURRENT_MIN_MA,
        max_value=PROTECTION_CURRENT_MAX_MA,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mA",
        translation_key="overcurrent_monitoring_ma",
        fallback_name="Overcurrent monitoring threshold",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_load_mw.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_POWER_MIN_MW,
        max_value=PROTECTION_POWER_MAX_MW,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mW",
        translation_key="overload_monitoring_mw",
        fallback_name="Overload monitoring",
    )
    .switch(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_only_ext_mode_restore.name,
        SonoffFastSceneConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="protection_only_ext_mode_restore",
        fallback_name="Protection external switch restore",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_voltage_mv.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_VOLTAGE_MIN_MV,
        max_value=PROTECTION_VOLTAGE_MAX_MV,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mV",
        translation_key="over_voltage_monitoring_threshold_mv",
        fallback_name="Overvoltage monitoring threshold",
    )
    .switch(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_voltage_enabled.name,
        SonoffFastSceneConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="over_voltage_enabled",
        fallback_name="Overvoltage monitoring enabled",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_under_voltage_mv.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_VOLTAGE_MIN_MV,
        max_value=PROTECTION_VOLTAGE_MAX_MV,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mV",
        translation_key="under_voltage_monitoring_threshold_mv",
        fallback_name="Undervoltage monitoring threshold",
    )
    .switch(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_under_voltage_enabled.name,
        SonoffFastSceneConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="under_voltage_enabled",
        fallback_name="Undervoltage monitoring enabled",
    )
    .switch(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_auto_recover.name,
        SonoffFastSceneConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="protection_auto_recover",
        fallback_name="Protection auto recover",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_current_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        divisor=1000,
        translation_key="accurrent_current_value",
        fallback_name="Current",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_voltage_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        divisor=1000,
        translation_key="accurrent_voltage_value",
        fallback_name="Voltage",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_power_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        attribute_converter=_convert_signed_power,
        translation_key="accurrent_power_value",
        fallback_name="Power",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.daily_forward_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="daily_forward_energy",
        fallback_name="Daily forward energy",
        divisor=1000,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.monthly_forward_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="monthly_forward_energy",
        fallback_name="Monthly forward energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.daily_reverse_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="daily_reverse_energy",
        fallback_name="Daily reverse energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.monthly_reverse_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="monthly_reverse_energy",
        fallback_name="Monthly reverse energy",
        divisor=1000,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.total_forward_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="total_forward_energy",
        fallback_name="Total forward energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.total_reverse_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="total_reverse_energy",
        fallback_name="Total reverse energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.total_run_time.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfTime.SECONDS,
        translation_key="total_run_time",
        fallback_name="Total run time",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.daily_run_time.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfTime.SECONDS,
        translation_key="daily_run_time",
        fallback_name="Daily run time",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.voltage_frequency.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfFrequency.HERTZ,
        translation_key="voltage_frequency",
        fallback_name="Voltage frequency",
    )
    .enum(
        SonoffCluster.AttributeDefs.fault_code.name,
        SonoffErrorCodeType,
        SonoffCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault_code",
        fallback_name="Fault code",
    )
    .device_automation_triggers(
        {
            trigger_tuple: {COMMAND: command, ENDPOINT_ID: 1}
            for command, trigger_tuple in EXTERNAL_TRIGGER_MAP.items()
        }
    )
    .add_to_registry()
)

(
    QuirkBuilder("SONOFF", "MINI-ZB1GS")
    .replaces(SonoffCluster)
    .adds(SonoffFastSceneConfigCluster)
    .removes(0x0B04)
    .removes(0x0702)
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.delayed_power_on_state.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="delayed_power_on_state",
        fallback_name="Delayed power on state",
    )
    .number(
        SonoffCluster.AttributeDefs.delayed_power_on_time.name,
        SonoffCluster.cluster_id,
        min_value=0.5,
        max_value=3599.5,
        step=0.5,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        multiplier=0.5,
        translation_key="delayed_power_on_time",
        fallback_name="Delayed power on time",
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalTriggerMode,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="detach_relay",
        fallback_name="Detach relay",
    )
    .enum(
        SonoffCluster.AttributeDefs.fault_code.name,
        SonoffErrorCodeType,
        SonoffCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault_code",
        fallback_name="Fault code",
    )
    .device_automation_triggers(
        {
            trigger_tuple: {COMMAND: command, ENDPOINT_ID: 1}
            for command, trigger_tuple in EXTERNAL_TRIGGER_MAP.items()
        }
    )
    .add_to_registry()
)

(
    QuirkBuilder("SONOFF", "MINI-ZB1GP")
    .replaces(SonoffCluster)
    .adds(SonoffFastSceneConfigCluster)
    .removes(0x0B04)
    .removes(0x0702)
    .removes(0x0006)
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_current_ma.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_CURRENT_MIN_MA,
        max_value=PROTECTION_CURRENT_MAX_MA,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mA",
        translation_key="overcurrent_monitoring_ma",
        fallback_name="Overcurrent monitoring threshold",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_load_mw.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_POWER_MIN_MW,
        max_value=PROTECTION_POWER_MAX_MW,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mW",
        translation_key="overload_monitoring_mw",
        fallback_name="Overload monitoring",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_voltage_mv.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_VOLTAGE_MIN_MV,
        max_value=PROTECTION_VOLTAGE_MAX_MV,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mV",
        translation_key="over_voltage_monitoring_threshold_mv",
        fallback_name="Overvoltage monitoring threshold",
    )
    .switch(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_over_voltage_enabled.name,
        SonoffFastSceneConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="over_voltage_enabled",
        fallback_name="Overvoltage monitoring enabled",
    )
    .number(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_under_voltage_mv.name,
        SonoffFastSceneConfigCluster.cluster_id,
        min_value=PROTECTION_VOLTAGE_MIN_MV,
        max_value=PROTECTION_VOLTAGE_MAX_MV,
        step=1,
        entity_type=EntityType.CONFIG,
        unit="mV",
        translation_key="under_voltage_monitoring_threshold_mv",
        fallback_name="Undervoltage monitoring threshold",
    )
    .switch(
        SonoffFastSceneConfigCluster.AttributeDefs.protection_under_voltage_enabled.name,
        SonoffFastSceneConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="under_voltage_enabled",
        fallback_name="Undervoltage monitoring enabled",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_current_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="accurrent_current_value",
        fallback_name="Current",
        divisor=1000,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_voltage_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        divisor=1000,
        translation_key="accurrent_voltage_value",
        fallback_name="Voltage",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_power_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        attribute_converter=_convert_signed_power,
        translation_key="accurrent_power_value",
        fallback_name="Power",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.daily_forward_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="daily_forward_energy",
        fallback_name="Daily forward energy",
        divisor=1000,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.monthly_forward_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="monthly_forward_energy",
        fallback_name="Monthly forward energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.daily_reverse_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="daily_reverse_energy",
        fallback_name="Daily reverse energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.monthly_reverse_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="monthly_reverse_energy",
        fallback_name="Monthly reverse energy",
        divisor=1000,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.total_forward_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="total_forward_energy",
        fallback_name="Total forward energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.total_reverse_energy.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        divisor=1000,
        translation_key="total_reverse_energy",
        fallback_name="Total reverse energy",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.total_run_time.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="total_run_time",
        fallback_name="Total run time",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.daily_run_time.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="daily_run_time",
        fallback_name="Daily run time",
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.voltage_frequency.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfFrequency.HERTZ,
        translation_key="voltage_frequency",
        fallback_name="Voltage frequency",
    )
    .enum(
        SonoffCluster.AttributeDefs.fault_code.name,
        SonoffErrorCodeType,
        SonoffCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault_code",
        fallback_name="Fault code",
    )
    .add_to_registry()
)
