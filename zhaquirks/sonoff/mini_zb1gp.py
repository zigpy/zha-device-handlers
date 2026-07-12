"""SONOFF MINI-ZB1GP power monitoring sensor."""

from __future__ import annotations

from typing import Any

import zigpy.types as t
from zigpy.zcl import AttributeReadEvent, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class SonoffExternalSwitchTriggerType(t.enum8):
    """External switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


class SonoffMiniZb1gpCluster(CustomCluster):
    """SONOFF/eWeLink manufacturer cluster for MINI-ZB1GP measurements."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            manufacturer_code=None,
        )
        fault_code = ZCLAttributeDef(
            id=0x0010,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            manufacturer_code=None,
        )
        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=SonoffExternalSwitchTriggerType,
            manufacturer_code=None,
        )
        current = ZCLAttributeDef(
            id=0x7004,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        voltage = ZCLAttributeDef(
            id=0x7005,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        power = ZCLAttributeDef(
            id=0x7006,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        energy_today = ZCLAttributeDef(
            id=0x7009,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        energy_month = ZCLAttributeDef(
            id=0x700A,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        energy_yesterday = ZCLAttributeDef(
            id=0x700B,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        protection_configuration = ZCLAttributeDef(
            id=0x7016,
            type=foundation.Array,
            manufacturer_code=None,
        )
        output_energy_today = ZCLAttributeDef(
            id=0x7018,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        output_energy_month = ZCLAttributeDef(
            id=0x7019,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        daily_run_time = ZCLAttributeDef(
            id=0x701C,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        total_run_time = ZCLAttributeDef(
            id=0x701D,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        total_energy = ZCLAttributeDef(
            id=0x701E,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        total_output_energy = ZCLAttributeDef(
            id=0x701F,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        voltage_frequency = ZCLAttributeDef(
            id=0x7029,
            type=t.uint32_t,
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Listen for raw protection configuration read results."""

        super().__init__(*args, **kwargs)
        self.on_event(AttributeReadEvent.event_type, self._handle_attribute_read)

    def _handle_attribute_read(self, event: AttributeReadEvent) -> None:
        """Cache a raw protection array when normal decoding did not succeed."""

        if event.attribute_id != self.AttributeDefs.protection_configuration.id:
            return
        if _protection_data(event.value) is not None:
            return
        if _protection_data(event.raw_value) is not None:
            self._update_attribute(event.attribute_id, event.raw_value)

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Read the composite protection configuration during setup."""

        await self.read_attributes([self.AttributeDefs.protection_configuration.id])


def signed_int32_milli_to_value(value: int) -> float:
    """Convert SONOFF signed 32-bit millivalue encoded in a uint32."""

    if value & 0x80000000:
        value -= 0x100000000
    return value / 1000


def milli_to_value(value: int) -> float:
    """Convert SONOFF unsigned millivalue to a native unit."""

    return value / 1000


def centi_to_value(value: int) -> float:
    """Convert a SONOFF centivalue to its native unit."""

    return value / 100


def _protection_data(value: Any) -> bytes | None:
    """Extract the protection TLV from a SONOFF fast-scene array."""

    if isinstance(value, foundation.Array):
        if value.value is None:
            return None
        payload = bytes(value.value)
    elif isinstance(value, (bytes, bytearray, list, t.LVList)):
        payload = bytes(value)
        if len(payload) >= 3 and payload[0] == foundation.DataTypeId.uint8:
            length = int.from_bytes(payload[1:3], "little")
            payload = payload[3 : 3 + length]
    else:
        return None

    if len(payload) < 3:
        return None

    index = 3
    while index + 2 <= len(payload):
        scene_type = payload[index]
        scene_length = payload[index + 1]
        index += 2
        if index + scene_length > len(payload):
            return None
        scene_data = payload[index : index + scene_length]
        index += scene_length
        if scene_type == 0x02:
            return scene_data if scene_length == 20 else None

    return None


def _protection_u32(value: Any, offset: int) -> int | None:
    """Decode a little-endian uint32 from the protection TLV."""

    data = _protection_data(value)
    if data is None:
        return None
    return int.from_bytes(data[offset : offset + 4], "little")


def protection_over_current(value: Any) -> float | None:
    """Decode the configured over-current threshold in amperes."""

    raw_value = _protection_u32(value, 1)
    return None if raw_value is None else milli_to_value(raw_value)


def protection_overload(value: Any) -> float | None:
    """Decode the configured overload threshold in watts."""

    raw_value = _protection_u32(value, 5)
    return None if raw_value is None else milli_to_value(raw_value)


def protection_external_switch_restore(value: Any) -> bool | None:
    """Decode whether protection restores the external switch mode."""

    data = _protection_data(value)
    return None if data is None else bool(data[9])


def _protection_voltage(value: Any, offset: int) -> float | None:
    """Decode a voltage threshold in volts without its enable flag."""

    raw_value = _protection_u32(value, offset)
    return None if raw_value is None else milli_to_value(raw_value & 0x7FFFFFFF)


def _protection_voltage_enabled(value: Any, offset: int) -> bool | None:
    """Decode a voltage threshold enable flag."""

    raw_value = _protection_u32(value, offset)
    return None if raw_value is None else bool(raw_value & 0x80000000)


def protection_over_voltage(value: Any) -> float | None:
    """Decode the configured over-voltage threshold in volts."""

    return _protection_voltage(value, 10)


def protection_over_voltage_enabled(value: Any) -> bool | None:
    """Decode whether over-voltage protection is enabled."""

    return _protection_voltage_enabled(value, 10)


def protection_under_voltage(value: Any) -> float | None:
    """Decode the configured under-voltage threshold in volts."""

    return _protection_voltage(value, 14)


def protection_under_voltage_enabled(value: Any) -> bool | None:
    """Decode whether under-voltage protection is enabled."""

    return _protection_voltage_enabled(value, 14)


def protection_auto_recover(value: Any) -> bool | None:
    """Decode whether automatic recovery is enabled."""

    data = _protection_data(value)
    return None if data is None else bool(data[18])


def protection_notification(value: Any) -> bool | None:
    """Decode whether protection notifications are enabled."""

    data = _protection_data(value)
    return None if data is None else bool(data[19])


def fault_code_bit_is_set(value: int, bit: int) -> bool:
    """Return whether a MINI-ZB1GP fault bit is set."""

    fault_type = (value >> 24) & 0xFF
    fault_length = (value >> 16) & 0xFF
    if fault_type != 0x07 or fault_length != 0x02:
        return False

    return bool((value & 0xFFFF) & bit)


def metering_communication_error(value: int) -> bool:
    """Return whether the metering communication error fault bit is set."""

    return fault_code_bit_is_set(value, 0b010)


def overheat_protection(value: int) -> bool:
    """Return whether the overheat protection fault bit is set."""

    return fault_code_bit_is_set(value, 0b001)


def overload_protection(value: int) -> bool:
    """Return whether the overload protection fault bit is set."""

    return fault_code_bit_is_set(value, 0b100)


power_reporting = ReportingConfig(
    min_interval=5,
    max_interval=900,
    reportable_change=100,
)

current_reporting = ReportingConfig(
    min_interval=5,
    max_interval=900,
    reportable_change=10,
)

voltage_reporting = ReportingConfig(
    min_interval=5,
    max_interval=900,
    reportable_change=100,
)

energy_reporting = ReportingConfig(
    min_interval=60,
    max_interval=3600,
    reportable_change=1,
)

fault_reporting = ReportingConfig(
    min_interval=5,
    max_interval=900,
    reportable_change=1,
)


common_quirk = (
    QuirkBuilder()
    .replaces(SonoffMiniZb1gpCluster)
    # The standard metering clusters expose sentinel values; the real
    # measurements are in the eWeLink manufacturer cluster 0xFC11 below.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=Metering.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1, cluster_id=ElectricalMeasurement.cluster_id
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.power.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=signed_int32_milli_to_value,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        reporting_config=power_reporting,
        unique_id_suffix="2820-active_power",
        translation_key="power",
        fallback_name="Power",
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.current.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        reporting_config=current_reporting,
        unique_id_suffix="2820-rms_current",
        translation_key="current",
        fallback_name="Current",
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.voltage.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        reporting_config=voltage_reporting,
        unique_id_suffix="2820-rms_voltage",
        translation_key="voltage",
        fallback_name="Voltage",
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.energy_today.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        reporting_config=energy_reporting,
        unique_id_suffix="energy_today",
        translation_key="energy_today",
        fallback_name="Energy today",
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.energy_month.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        reporting_config=energy_reporting,
        unique_id_suffix="energy_month",
        translation_key="energy_month",
        fallback_name="Energy this month",
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.output_energy_today.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        reporting_config=energy_reporting,
        unique_id_suffix="output_energy_today",
        translation_key="output_energy_today",
        fallback_name="Export energy today",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.output_energy_month.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        reporting_config=energy_reporting,
        unique_id_suffix="output_energy_month",
        translation_key="output_energy_month",
        fallback_name="Export energy this month",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.total_energy.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        reporting_config=energy_reporting,
        unique_id_suffix="1794-summation_delivered",
        translation_key="total_energy",
        fallback_name="Total energy",
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.total_output_energy.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=milli_to_value,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        reporting_config=energy_reporting,
        unique_id_suffix="total_output_energy",
        translation_key="total_output_energy",
        fallback_name="Total export energy",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.daily_run_time.name,
        SonoffMiniZb1gpCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfTime.SECONDS,
        reporting_config=energy_reporting,
        translation_key="daily_run_time",
        fallback_name="Daily run time",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.total_run_time.name,
        SonoffMiniZb1gpCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfTime.SECONDS,
        reporting_config=energy_reporting,
        translation_key="total_run_time",
        fallback_name="Total run time",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.voltage_frequency.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=centi_to_value,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfFrequency.HERTZ,
        reporting_config=voltage_reporting,
        translation_key="voltage_frequency",
        fallback_name="Voltage frequency",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_over_current,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_over_current",
        translation_key="protection_over_current",
        fallback_name="Protection over-current threshold",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_overload,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_overload",
        translation_key="protection_overload",
        fallback_name="Protection overload threshold",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_over_voltage,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_over_voltage",
        translation_key="protection_over_voltage",
        fallback_name="Protection over-voltage threshold",
        initially_disabled=True,
    )
    .sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_under_voltage,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_under_voltage",
        translation_key="protection_under_voltage",
        fallback_name="Protection under-voltage threshold",
        initially_disabled=True,
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_external_switch_restore,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_external_switch_restore",
        translation_key="protection_external_switch_restore",
        fallback_name="Protection external switch restore",
        initially_disabled=True,
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_over_voltage_enabled,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_over_voltage_enabled",
        translation_key="protection_over_voltage_enabled",
        fallback_name="Over-voltage protection enabled",
        initially_disabled=True,
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_under_voltage_enabled,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_under_voltage_enabled",
        translation_key="protection_under_voltage_enabled",
        fallback_name="Under-voltage protection enabled",
        initially_disabled=True,
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_auto_recover,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_auto_recover",
        translation_key="protection_auto_recover",
        fallback_name="Protection auto recover",
        initially_disabled=True,
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.protection_configuration.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=protection_notification,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        unique_id_suffix="protection_notification",
        translation_key="protection_notification",
        fallback_name="Protection notification",
        initially_disabled=True,
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.fault_code.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=metering_communication_error,
        reporting_config=fault_reporting,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="metering_communication_error",
        translation_key="metering_communication_error",
        fallback_name="Metering communication error",
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.fault_code.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=overheat_protection,
        reporting_config=fault_reporting,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="overheat_protection",
        translation_key="overheat_protection",
        fallback_name="Overheat protection error",
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.fault_code.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=overload_protection,
        reporting_config=fault_reporting,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="overload_protection",
        translation_key="overload_protection",
        fallback_name="Overload protection error",
    )
    .switch(
        SonoffMiniZb1gpCluster.AttributeDefs.network_led.name,
        SonoffMiniZb1gpCluster.cluster_id,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .switch(
        SonoffMiniZb1gpCluster.AttributeDefs.turbo_mode.name,
        SonoffMiniZb1gpCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
)

(
    common_quirk.clone()
    .applies_to("SONOFF", "MINI-ZB1GP")
    # This model is a monitor, so its OnOff cluster is not a relay entity.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
    .add_to_registry()
)

(
    common_quirk.clone()
    .applies_to("SONOFF", "MINI-ZB1GSP")
    .enum(
        SonoffMiniZb1gpCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffMiniZb1gpCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .add_to_registry()
)
