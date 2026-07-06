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
        unique_id_suffix="power",
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
        unique_id_suffix="current",
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
        unique_id_suffix="voltage",
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
        fallback_name="Energy this month",
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
        unique_id_suffix="total_energy",
        fallback_name="Total energy",
    )
    .switch(
        SonoffMiniZb1gpCluster.AttributeDefs.network_led.name,
        SonoffMiniZb1gpCluster.cluster_id,
        translation_key="network_led",
        fallback_name="Network indicator",
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
