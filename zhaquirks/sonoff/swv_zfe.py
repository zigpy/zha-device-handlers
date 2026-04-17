"""Sonoff SWV-ZNE/ZFE/ZNU/ZFU - Zigbee smart water valve."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    EntityType,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUnsupportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    foundation,
)
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster


class SWVZFEValveAlarmFlags(t.bitmap8):
    """Bit flags in valve_alarm_settings[0]."""

    AlarmWaterShortage = 0b00001
    AlarmWaterLeak = 0b00010
    FrostProtection = 0b00100
    WaterShortageAutoClose = 0b01000
    WaterLeakAutoClose = 0b10000


SWVZFE_VALVE_ALARM_KNOWN_MASK = int(
    SWVZFEValveAlarmFlags.AlarmWaterShortage
    | SWVZFEValveAlarmFlags.AlarmWaterLeak
    | SWVZFEValveAlarmFlags.FrostProtection
    | SWVZFEValveAlarmFlags.WaterShortageAutoClose
    | SWVZFEValveAlarmFlags.WaterLeakAutoClose
)


class SWVZFEValveAlarmSettingsPayload(
    t.LVList, item_type=t.uint8_t, length_type=t.uint16_t
):
    """ZCL array payload used by valve_alarm_settings."""

    def __init__(self, value=()):
        """Allow coercion from a decoded ZCL Array wrapper."""
        if isinstance(value, foundation.Array):
            value = value.value
        super().__init__(value)


def _swvzfe_uint8(value: Any, field_name: str) -> int:
    """Validate that a field is a uint8."""
    try:
        int_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc

    if not 0 <= int_value <= 0xFF:
        raise ValueError(f"{field_name} must be in the range 0..255")

    return int_value


def swvzfe_normalize_valve_alarm_settings(
    value: Any,
) -> SWVZFEValveAlarmSettingsPayload:
    """Normalize a valve_alarm_settings payload to a 4-byte uint8 array."""
    if value is None:
        raise ValueError("valve_alarm_settings cannot be None")

    if isinstance(value, foundation.Array):
        value = value.value

    try:
        payload = SWVZFEValveAlarmSettingsPayload(value)
    except TypeError as exc:
        raise ValueError(
            "valve_alarm_settings must be an iterable of four bytes"
        ) from exc

    if len(payload) != 4:
        raise ValueError(
            f"valve_alarm_settings must contain exactly 4 bytes, got {len(payload)}"
        )

    return SWVZFEValveAlarmSettingsPayload(
        [
            _swvzfe_uint8(item, f"valve_alarm_settings[{idx}]")
            for idx, item in enumerate(payload)
        ]
    )


def swvzfe_decode_valve_alarm_settings(value: Any) -> dict[str, bool | int]:
    """Decode the packed valve_alarm_settings payload into named fields."""
    payload = swvzfe_normalize_valve_alarm_settings(value)
    enable_bits = int(payload[0])

    return {
        "enable_alarm_water_shortage": bool(
            enable_bits & SWVZFEValveAlarmFlags.AlarmWaterShortage
        ),
        "enable_alarm_water_leak": bool(
            enable_bits & SWVZFEValveAlarmFlags.AlarmWaterLeak
        ),
        "enable_frost_protection": bool(
            enable_bits & SWVZFEValveAlarmFlags.FrostProtection
        ),
        "enable_water_shortage_auto_close": bool(
            enable_bits & SWVZFEValveAlarmFlags.WaterShortageAutoClose
        ),
        "enable_water_leak_auto_close": bool(
            enable_bits & SWVZFEValveAlarmFlags.WaterLeakAutoClose
        ),
        "alarm_water_shortage_duration": int(payload[1]),
        "alarm_water_leak_duration": int(payload[2]),
        "set_frost_temperature": int(payload[3]),
    }


def swvzfe_pack_valve_alarm_settings(
    *,
    enable_alarm_water_shortage: bool,
    enable_alarm_water_leak: bool,
    enable_frost_protection: bool,
    enable_water_shortage_auto_close: bool,
    enable_water_leak_auto_close: bool,
    alarm_water_shortage_duration: int,
    alarm_water_leak_duration: int,
    set_frost_temperature: int,
    extra_enable_bits: int = 0,
) -> SWVZFEValveAlarmSettingsPayload:
    """Pack named valve alarm settings into the device's 4-byte payload."""
    enable_bits = _swvzfe_uint8(extra_enable_bits, "extra_enable_bits")

    if enable_alarm_water_shortage:
        enable_bits |= SWVZFEValveAlarmFlags.AlarmWaterShortage
    if enable_alarm_water_leak:
        enable_bits |= SWVZFEValveAlarmFlags.AlarmWaterLeak
    if enable_frost_protection:
        enable_bits |= SWVZFEValveAlarmFlags.FrostProtection
    if enable_water_shortage_auto_close:
        enable_bits |= SWVZFEValveAlarmFlags.WaterShortageAutoClose
    if enable_water_leak_auto_close:
        enable_bits |= SWVZFEValveAlarmFlags.WaterLeakAutoClose

    return SWVZFEValveAlarmSettingsPayload(
        [
            enable_bits,
            _swvzfe_uint8(
                alarm_water_shortage_duration, "alarm_water_shortage_duration"
            ),
            _swvzfe_uint8(alarm_water_leak_duration, "alarm_water_leak_duration"),
            _swvzfe_uint8(set_frost_temperature, "set_frost_temperature"),
        ]
    )


def swvzfe_be_swap(x: int | None) -> int | None:
    """Byte-swap a UINT32 the device sends big-endian over the ZCL (little-endian) frame."""
    if x is None:
        return None
    return int.from_bytes(x.to_bytes(4, "little"), "big")


def swvzfe_water_shortage(x: int | None) -> bool | None:
    """Extract water shortage flag (bit 0) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x01)


def swvzfe_water_leakage(x: int | None) -> bool | None:
    """Extract water leakage flag (bit 1) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x02)


def swvzfe_frost_protection(x: int | None) -> bool | None:
    """Extract frost protection active flag (bit 2) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x04)


def swvzfe_fail_safe(x: int | None) -> bool | None:
    """Extract fail-safe flag (bit 3) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x08)


class SWVZFECluster(CustomCluster):
    """Custom Sonoff cluster for the SWV-ZFE smart water valve."""

    cluster_id = 0xFC11
    ep_attribute = "swvzfe_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the private Sonoff cluster."""

        # 0x0000 - Child lock (on/off physical buttons on device)
        child_lock = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            manufacturer_code=None,
        )

        # 0x5006 - Real-time irrigation duration (seconds, big-endian UINT32)
        real_time_irrigation_duration = ZCLAttributeDef(
            id=0x5006,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x5007 - Real-time irrigation volume (litres, big-endian UINT32)
        real_time_irrigation_volume = ZCLAttributeDef(
            id=0x5007,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x500C - Valve abnormal state bitmask:
        #   bit 0 = water shortage, bit 1 = water leakage,
        #   bit 2 = frost protection, bit 3 = fail safe
        valve_abnormal_state = ZCLAttributeDef(
            id=0x500C,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        # 0x500F - Daily irrigation volume (litres)
        daily_irrigation_volume = ZCLAttributeDef(
            id=0x500F,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x5010 - Valve work state (True = valve is actively open/working)
        valve_work_state = ZCLAttributeDef(
            id=0x5010,
            type=t.Bool,
            manufacturer_code=None,
        )

        # 0x5016 - Device longitude (integer degrees, -180 to 180)
        longitude = ZCLAttributeDef(
            id=0x5016,
            type=t.int32s,
            manufacturer_code=None,
        )

        # 0x5017 - Device latitude (integer degrees, -90 to 90)
        latitude = ZCLAttributeDef(
            id=0x5017,
            type=t.int32s,
            manufacturer_code=None,
        )

        # 0x501A - Daily irrigation duration (minutes)
        daily_irrigation_duration = ZCLAttributeDef(
            id=0x501A,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x501B - Hourly irrigation volume (litres)
        hour_irrigation_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x501C - Hourly irrigation duration (minutes)
        hour_irrigation_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x5020 - Packed valve alarm settings uint8 array
        valve_alarm_settings = ZCLAttributeDef(
            id=0x5020,
            type=SWVZFEValveAlarmSettingsPayload,
            zcl_type=foundation.DataTypeId.array,
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Init and listen for valve_alarm_settings changes."""
        super().__init__(*args, **kwargs)
        self.on_event(
            AttributeReadEvent.event_type, self._handle_valve_alarm_settings_change
        )
        self.on_event(
            AttributeReportedEvent.event_type, self._handle_valve_alarm_settings_change
        )
        self.on_event(
            AttributeUpdatedEvent.event_type, self._handle_valve_alarm_settings_change
        )
        self.on_event(
            AttributeWrittenEvent.event_type, self._handle_valve_alarm_settings_change
        )

    def _repair_valve_alarm_settings_read_response(self, data: bytes) -> bytes | None:
        """Repair malformed 0x5020 read responses with a bad array element type."""
        try:
            hdr, payload = foundation.ZCLHeader.deserialize(data)
        except Exception:
            return None

        if (
            hdr.frame_control.frame_type != foundation.FrameType.GLOBAL_COMMAND
            or hdr.direction != foundation.Direction.Server_to_Client
            or hdr.command_id != foundation.GeneralCommand.Read_Attributes_rsp
        ):
            return None

        malformed_prefix = (
            SWVZFECluster.AttributeDefs.valve_alarm_settings.id.serialize()
            + foundation.Status.SUCCESS.serialize()
            + foundation.DataTypeId.array.serialize()
            + foundation.DataTypeId.array.serialize()
        )

        repaired_prefix = (
            SWVZFECluster.AttributeDefs.valve_alarm_settings.id.serialize()
            + foundation.Status.SUCCESS.serialize()
            + foundation.DataTypeId.array.serialize()
            + foundation.DataTypeId.uint8.serialize()
        )

        if malformed_prefix not in payload:
            return None

        repaired_payload = payload.replace(malformed_prefix, repaired_prefix)
        return hdr.serialize() + repaired_payload

    def deserialize(self, data: bytes):
        """Log raw frames when the private cluster payload cannot be parsed."""
        try:
            return super().deserialize(data)
        except Exception as exc:
            repaired_data = self._repair_valve_alarm_settings_read_response(data)
            if repaired_data is not None:
                return super().deserialize(repaired_data)

            self.warning(
                "Failed to deserialize SWV-ZF* cluster frame on endpoint %s: %s; raw=%s",
                self.endpoint.endpoint_id,
                exc,
                data.hex(" "),
            )
            raise

    def _handle_valve_alarm_settings_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync the packed alarm payload into the local config cluster."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return

        if event.attribute_id != self.AttributeDefs.valve_alarm_settings.id:
            return

        try:
            self.endpoint.swvzfe_valve_alarm_config.update_from_valve_alarm_settings(
                event.value
            )
        except ValueError as exc:
            self.warning(
                "Ignoring invalid valve_alarm_settings payload %r: %s",
                event.value,
                exc,
            )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read the packed alarm settings during pairing to populate entities."""
        try:
            await self.read_attributes([self.AttributeDefs.valve_alarm_settings.id])
        except Exception as exc:
            self.warning(
                "Unable to read valve_alarm_settings during configuration: %s; continuing without initialization",
                exc,
            )

    async def _write_valve_alarm_settings(
        self,
        value: Any,
        manufacturer: int | UndefinedType | None = UNDEFINED,
        *,
        update_cache: bool = True,
        **kwargs,
    ) -> list[foundation.WriteAttributesStatusRecord]:
        """Write the packed valve alarm settings using an explicit ZCL Array payload."""
        attr_def = self.find_attribute(
            self.AttributeDefs.valve_alarm_settings.id, manufacturer_code=manufacturer
        )
        manufacturer_code = self._get_effective_manufacturer_code(attr_def)
        payload = swvzfe_normalize_valve_alarm_settings(value)

        zcl_attr = foundation.Attribute(attr_def.id, foundation.TypeValue())
        zcl_attr.value.type = foundation.DataTypeId.array
        zcl_attr.value.value = foundation.Array(
            type=foundation.DataTypeId.uint8,
            value=payload,
        )

        result = await self.write_attributes_raw(
            [zcl_attr], manufacturer_code=manufacturer_code, **kwargs
        )

        if isinstance(result[0], list):
            if (
                len(result[0]) == 1
                and result[0][0].status == foundation.Status.SUCCESS
                and result[0][0].attrid is None
            ):
                records = [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS,
                        attrid=attr_def.id,
                    )
                ]
            elif result[0]:
                records = list(result[0])
            else:
                records = [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS,
                        attrid=attr_def.id,
                    )
                ]
        else:
            records = [
                foundation.WriteAttributesStatusRecord(
                    status=result[0],
                    attrid=attr_def.id,
                )
            ]

        if update_cache:
            for record in records:
                if record.status == foundation.Status.SUCCESS:
                    self._attr_cache.set_value(attr_def, payload)
                elif record.status == foundation.Status.UNSUPPORTED_ATTRIBUTE:
                    self.emit(
                        AttributeUnsupportedEvent.event_type,
                        AttributeUnsupportedEvent(
                            device_ieee=str(self.endpoint.device.ieee),
                            endpoint_id=self.endpoint.endpoint_id,
                            cluster_type=self._type,
                            cluster_id=self.cluster_id,
                            attribute_name=attr_def.name,
                            attribute_id=attr_def.id,
                            manufacturer_code=manufacturer_code,
                        ),
                    )

                self.emit(
                    AttributeWrittenEvent.event_type,
                    AttributeWrittenEvent(
                        device_ieee=str(self.endpoint.device.ieee),
                        endpoint_id=self.endpoint.endpoint_id,
                        cluster_type=self._type,
                        cluster_id=self.cluster_id,
                        attribute_name=attr_def.name,
                        attribute_id=attr_def.id,
                        manufacturer_code=manufacturer_code,
                        value=payload,
                        status=record.status,
                    ),
                )

        return records

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        *,
        update_cache: bool = True,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes, using a custom ZCL Array payload for valve_alarm_settings."""
        other_attributes: dict[str | int | foundation.ZCLAttributeDef, Any] = {}
        alarm_value: Any | None = None

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr, manufacturer_code=manufacturer)
            if attr_def.id == self.AttributeDefs.valve_alarm_settings.id:
                alarm_value = value
            else:
                other_attributes[attr] = value

        results: list[foundation.WriteAttributesStatusRecord] = []

        if other_attributes:
            results.extend(
                (
                    await super().write_attributes(
                        other_attributes,
                        manufacturer=manufacturer,
                        update_cache=update_cache,
                        **kwargs,
                    )
                )[0]
            )

        if alarm_value is not None:
            results.extend(
                await self._write_valve_alarm_settings(
                    alarm_value,
                    manufacturer=manufacturer,
                    update_cache=update_cache,
                    **kwargs,
                )
            )

        return [results]


class SWVZFEValveAlarmConfigCluster(LocalDataCluster):
    """Local cluster exposing the packed valve alarm settings as individual attrs."""

    cluster_id = 0xFBFD
    ep_attribute = "swvzfe_valve_alarm_config"

    class AttributeDefs(BaseAttributeDefs):
        """Virtual attributes mapped to valve_alarm_settings."""

        enable_alarm_water_shortage: Final = ZCLAttributeDef(id=0x0000, type=t.Bool)
        enable_alarm_water_leak: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        enable_frost_protection: Final = ZCLAttributeDef(id=0x0002, type=t.Bool)
        enable_water_shortage_auto_close: Final = ZCLAttributeDef(
            id=0x0003, type=t.Bool
        )
        enable_water_leak_auto_close: Final = ZCLAttributeDef(id=0x0004, type=t.Bool)
        alarm_water_shortage_duration: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint8_t
        )
        alarm_water_leak_duration: Final = ZCLAttributeDef(id=0x0006, type=t.uint8_t)
        set_frost_temperature: Final = ZCLAttributeDef(id=0x0007, type=t.uint8_t)

    _SETTING_ATTRS = (
        AttributeDefs.enable_alarm_water_shortage,
        AttributeDefs.enable_alarm_water_leak,
        AttributeDefs.enable_frost_protection,
        AttributeDefs.enable_water_shortage_auto_close,
        AttributeDefs.enable_water_leak_auto_close,
        AttributeDefs.alarm_water_shortage_duration,
        AttributeDefs.alarm_water_leak_duration,
        AttributeDefs.set_frost_temperature,
    )

    _VALID_ATTRIBUTES = {attr.id for attr in _SETTING_ATTRS}

    def __init__(self, *args, **kwargs):
        """Init the local cache for unknown future alarm bits."""
        super().__init__(*args, **kwargs)
        self._unknown_enable_bits = 0

    def update_from_valve_alarm_settings(self, value: Any) -> None:
        """Update local attributes from the packed valve_alarm_settings array."""
        payload = swvzfe_normalize_valve_alarm_settings(value)
        decoded = swvzfe_decode_valve_alarm_settings(payload)
        self._unknown_enable_bits = int(payload[0]) & ~SWVZFE_VALVE_ALARM_KNOWN_MASK

        for attr_name, attr_value in decoded.items():
            self._update_attribute(self.find_attribute(attr_name), attr_value)

    def _current_settings(self) -> dict[str, bool | int]:
        """Return the current local settings or fail fast when they are unknown."""
        settings: dict[str, bool | int] = {}

        for attr_def in self._SETTING_ATTRS:
            value = self.get(attr_def.id)
            if value is None:
                raise ValueError(
                    "valve_alarm_settings are not initialized yet; read the device first"
                )
            settings[attr_def.name] = value

        return settings

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list:
        """Translate local writes into a packed valve_alarm_settings write."""
        try:
            settings = self._current_settings()
        except ValueError:
            await self.endpoint.swvzfe_cluster.read_attributes(
                [SWVZFECluster.AttributeDefs.valve_alarm_settings.id]
            )
            settings = self._current_settings()

        for attr, value in attributes.items():
            attr_name = self.find_attribute(attr).name
            if attr_name.startswith("enable_"):
                settings[attr_name] = bool(value)
            else:
                settings[attr_name] = _swvzfe_uint8(value, attr_name)

        payload = swvzfe_pack_valve_alarm_settings(
            enable_alarm_water_shortage=bool(settings["enable_alarm_water_shortage"]),
            enable_alarm_water_leak=bool(settings["enable_alarm_water_leak"]),
            enable_frost_protection=bool(settings["enable_frost_protection"]),
            enable_water_shortage_auto_close=bool(
                settings["enable_water_shortage_auto_close"]
            ),
            enable_water_leak_auto_close=bool(settings["enable_water_leak_auto_close"]),
            alarm_water_shortage_duration=int(
                settings["alarm_water_shortage_duration"]
            ),
            alarm_water_leak_duration=int(settings["alarm_water_leak_duration"]),
            set_frost_temperature=int(settings["set_frost_temperature"]),
            extra_enable_bits=self._unknown_enable_bits,
        )

        return await self.endpoint.swvzfe_cluster.write_attributes(
            {SWVZFECluster.AttributeDefs.valve_alarm_settings.id: payload},
            **kwargs,
        )


(
    QuirkBuilder("SONOFF", "SWV-ZFE")
    .applies_to("SONOFF", "SWV-ZNE")
    .applies_to("SONOFF", "SWV-ZNU")
    .applies_to("SONOFF", "SWV-ZFU")
    .replaces(SWVZFECluster)
    .adds(SWVZFEValveAlarmConfigCluster)
    # Child lock - prevent accidental physical operation of the valve
    .switch(
        SWVZFECluster.AttributeDefs.child_lock.name,
        SWVZFECluster.cluster_id,
        on_value=1,
        off_value=0,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # Whether the valve is actively open and flowing
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_work_state.name,
        SWVZFECluster.cluster_id,
        translation_key="valve_work_state",
        fallback_name="Valve working",
    )
    .switch(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_alarm_water_shortage.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="enable_alarm_water_shortage",
        fallback_name="Water shortage alarm",
    )
    .switch(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_alarm_water_leak.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="enable_alarm_water_leak",
        fallback_name="Water leak alarm",
    )
    .switch(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_frost_protection.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="enable_frost_protection",
        fallback_name="Frost protection",
    )
    .switch(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_water_shortage_auto_close.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="enable_water_shortage_auto_close",
        fallback_name="Water shortage auto-close",
    )
    .switch(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_water_leak_auto_close.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="enable_water_leak_auto_close",
        fallback_name="Water leak auto-close",
    )
    .number(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.alarm_water_shortage_duration.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        min_value=0,
        max_value=10,
        step=1,
        mode="box",
        entity_type=EntityType.CONFIG,
        unit=UnitOfTime.MINUTES,
        translation_key="alarm_water_shortage_duration",
        fallback_name="Water shortage alarm duration",
    )
    .number(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.alarm_water_leak_duration.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        min_value=0,
        max_value=3,
        step=1,
        mode="box",
        entity_type=EntityType.CONFIG,
        unit=UnitOfTime.MINUTES,
        translation_key="alarm_water_leak_duration",
        fallback_name="Water leak alarm duration",
    )
    .number(
        SWVZFEValveAlarmConfigCluster.AttributeDefs.set_frost_temperature.name,
        SWVZFEValveAlarmConfigCluster.cluster_id,
        min_value=0,
        max_value=10,
        step=1,
        mode="box",
        entity_type=EntityType.CONFIG,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="set_frost_temperature",
        fallback_name="Frost protection temperature",
    )
    # Valve abnormal state - decomposed into individual binary sensors per bit
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_water_shortage,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="water_shortage",
        fallback_name="Water shortage",
    )
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_water_leakage,
        device_class=BinarySensorDeviceClass.MOISTURE,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="water_leakage",
        fallback_name="Water leakage",
    )
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_frost_protection,
        unique_id_suffix="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_fail_safe,
        device_class=BinarySensorDeviceClass.SAFETY,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="fail_safe",
        fallback_name="Fail safe",
    )
    # Real-time stats (note: big-endian byte-swap required per device firmware)
    .sensor(
        SWVZFECluster.AttributeDefs.real_time_irrigation_duration.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_be_swap,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="real_time_irrigation_duration",
        fallback_name="Real-time irrigation duration",
    )
    .sensor(
        SWVZFECluster.AttributeDefs.real_time_irrigation_volume.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_be_swap,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolume.LITERS,
        translation_key="real_time_irrigation_volume",
        fallback_name="Real-time irrigation volume",
    )
    # Daily totals
    .sensor(
        SWVZFECluster.AttributeDefs.daily_irrigation_volume.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfVolume.LITERS,
        translation_key="daily_irrigation_volume",
        fallback_name="Daily irrigation volume",
    )
    .sensor(
        SWVZFECluster.AttributeDefs.daily_irrigation_duration.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfTime.MINUTES,
        translation_key="daily_irrigation_duration",
        fallback_name="Daily irrigation duration",
    )
    # Hourly totals
    .sensor(
        SWVZFECluster.AttributeDefs.hour_irrigation_volume.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolume.LITERS,
        translation_key="hour_irrigation_volume",
        fallback_name="Hourly irrigation volume",
    )
    .sensor(
        SWVZFECluster.AttributeDefs.hour_irrigation_duration.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        translation_key="hour_irrigation_duration",
        fallback_name="Hourly irrigation duration",
    )
    # Device location (used by the device for weather-based irrigation adjustment)
    .number(
        SWVZFECluster.AttributeDefs.longitude.name,
        SWVZFECluster.cluster_id,
        min_value=-180,
        max_value=180,
        step=1,
        mode="box",
        translation_key="longitude",
        fallback_name="Longitude",
    )
    .number(
        SWVZFECluster.AttributeDefs.latitude.name,
        SWVZFECluster.cluster_id,
        min_value=-90,
        max_value=90,
        step=1,
        mode="box",
        translation_key="latitude",
        fallback_name="Latitude",
    )
    .add_to_registry()
)
