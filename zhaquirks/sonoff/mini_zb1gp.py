"""SONOFF MINI-ZB1GP power monitoring sensor."""

from __future__ import annotations

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from zhaquirks.clusters import CustomCluster


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


def signed_int32_milli_to_value(value: int) -> float:
    """Convert SONOFF signed 32-bit millivalue encoded in a uint32."""

    if value & 0x80000000:
        value -= 0x100000000
    return value / 1000


def milli_to_value(value: int) -> float:
    """Convert SONOFF unsigned millivalue to a native unit."""

    return value / 1000


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


(
    QuirkBuilder("SONOFF", "MINI-ZB1GP")
    .replaces(SonoffMiniZb1gpCluster)
    # The device exposes an OnOff cluster but is a monitor, not a relay.
    # Its standard metering clusters also expose sentinel values; the real
    # measurements are in the eWeLink manufacturer cluster 0xFC11 below.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
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
        primary=True,
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
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.fault_code.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=metering_communication_error,
        reporting_config=fault_reporting,
        unique_id_suffix="metering_communication_error",
        translation_key="metering_communication_error",
        fallback_name="Metering communication error",
    )
    .binary_sensor(
        SonoffMiniZb1gpCluster.AttributeDefs.fault_code.name,
        SonoffMiniZb1gpCluster.cluster_id,
        attribute_converter=overload_protection,
        reporting_config=fault_reporting,
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
    .add_to_registry()
)
