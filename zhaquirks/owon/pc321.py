"""Quirk for Owon PC321."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
import zigpy.types as t
from zigpy.zcl.clusters.smartenergy import Metering


class OwonPC321MeteringCluster(CustomCluster, Metering):
    """OwonPC321MeteringCluster cluster."""

    cluster_id = 0x0702
    name = "OwonPC321Metering"
    ep_attribute = "smartenergy_metering"

    attributes = Metering.attributes.copy()
    attributes.update(
        {
            0x2000: ("phase_1_power", t.uint24_t, True),
            0x2001: ("phase_2_power", t.uint24_t, True),
            0x2002: ("phase_3_power", t.uint24_t, True),
            0x2100: ("phase_1_reactive_power", t.uint24_t, True),
            0x2101: ("phase_2_reactive_power", t.uint24_t, True),
            0x2102: ("phase_3_reactive_power", t.uint24_t, True),
            0x2103: ("reactive_power_summation_of_the_3_phases", t.uint24_t, True),
            0x3000: ("phase_1_voltage", t.uint24_t, True),
            0x3001: ("phase_2_voltage", t.uint24_t, True),
            0x3002: ("phase_3_voltage", t.uint24_t, True),
            0x3100: ("phase_1_current", t.uint24_t, True),
            0x3101: ("phase_2_current", t.uint24_t, True),
            0x3102: ("phase_3_current", t.uint24_t, True),
            0x3103: ("current_summation_of_the_3_phases", t.uint24_t, True),
            0x3104: ("leakage_current", t.uint24_t, True),
            0x4000: ("phase_1_energy_consumption", t.uint48_t, True),
            0x4001: ("phase_2_energy_consumption", t.uint48_t, True),
            0x4002: ("phase_3_energy_consumption", t.uint48_t, True),
            0x4100: ("phase_1_reactive_energy_consumption", t.uint48_t, True),
            0x4101: ("phase_2_reactive_energy_consumption", t.uint48_t, True),
            0x4102: ("phase_3_reactive_energy_consumption", t.uint48_t, True),
            0x4103: ("reactive_energy_summation_of_the_3_phases", t.uint48_t, True),
        }
    )


(
    QuirkBuilder("OWON Technology Inc.", "PC321")
    .replaces(OwonPC321MeteringCluster)
    .sensor(
        "phase_1_power",
        OwonPC321MeteringCluster.cluster_id,
        unit=UnitOfPower.WATT,
        translation_key="active_power_phase_1",
        fallback_name="Active power phase 1",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_2_power",
        OwonPC321MeteringCluster.cluster_id,
        unit=UnitOfPower.WATT,
        translation_key="active_power_phase_2",
        fallback_name="Active power phase 2",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_3_power",
        OwonPC321MeteringCluster.cluster_id,
        unit=UnitOfPower.WATT,
        translation_key="active_power_phase_3",
        fallback_name="Active power phase 3",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_1_current",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="current_phase_1",
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current phase 1",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_2_current",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="current_phase_2",
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current phase 2",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_3_current",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="current_phase_3",
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current phase 3",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_1_energy_consumption",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="energy_consumption_1",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy consumption 1",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        divisor=1000,
    )
    .sensor(
        "phase_2_energy_consumption",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="energy_consumption_2",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy consumption 2",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        divisor=1000,
    )
    .sensor(
        "phase_3_energy_consumption",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="energy_consumption_3",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy consumption 3",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        divisor=1000,
    )
    .sensor(
        "phase_1_voltage",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="voltage_1",
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage 1",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        divisor=10,
    )
    .sensor(
        "phase_2_voltage",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="voltage_2",
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage 2",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        divisor=10,
    )
    .sensor(
        "phase_3_voltage",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="voltage_3",
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage 3",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        divisor=10,
    )
    .sensor(
        "phase_1_reactive_power",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_power_1",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive power 1",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_2_reactive_power",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_power_2",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive power 2",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_3_reactive_power",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_power_3",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive power 3",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "reactive_power_summation_of_the_3_phases",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_power_summation",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive power summation",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "leakage_current",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="leakage_current",
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Leakage current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_1_reactive_energy_consumption",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_energy_consumption_1",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive energy consumption 1",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_2_reactive_energy_consumption",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_energy_consumption_2",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive energy consumption 2",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "phase_3_reactive_energy_consumption",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_energy_consumption_3",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive energy consumption 3",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .sensor(
        "reactive_energy_summation_of_the_3_phases",
        OwonPC321MeteringCluster.cluster_id,
        translation_key="reactive_energy_consumption_summation",
        unit=UnitOfPower.WATT,
        fallback_name="Reactive energy consumption summation",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .add_to_registry()
)
