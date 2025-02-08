"""Tuya Power Meter."""

from collections.abc import ByteString

from zigpy.quirks.v2 import SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
)
import zigpy.types as t
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.tuya import DPToAttributeMapping, TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


def dpToPower(data: ByteString) -> int:
    """Convert DP data to power value."""
    # Support negative power readings
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = data[7] | (data[6] << 8)
    if power > 0x7FFF:
        power = (0x999A - power) * -1
    return power


def dpToCurrent(data: ByteString) -> int:
    """Convert DP data to current value."""
    return (data[4] | (data[3] << 8)) / 1000


def dpToVoltage(data: ByteString) -> int:
    """Convert DP data to voltage value."""
    return (data[1] | (data[0] << 8)) / 10


class Tuya3PhaseElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
    """Tuya Electrical Measurement cluster."""


(
    TuyaQuirkBuilder("_TZE200_nslr42tt", "TS0601")
    .tuya_temperature(dp_id=0x85, scale=10)
    .tuya_sensor(
        dp_id=0x86,
        attribute_name="device_status",
        type=t.int32s,
        fallback_name="Device status",
        translation_key="device_status",
    )
    .tuya_dp(
        dp_id=0x84,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
    )
    # Energy
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy_consumed",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=0x65,
        attribute_name="energy_consumed_ph_a",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=0x6F,
        attribute_name="energy_consumed_ph_b",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=0x79,
        attribute_name="energy_consumed_ph_c",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=0x9,
        attribute_name="power",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        fallback_name="Total current",
    )
    .tuya_sensor(
        dp_id=0x83,
        attribute_name="current",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Total current",
    )
    .tuya_dp_multi(
        dp_id=0x6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=dpToPower,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=dpToVoltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=dpToCurrent,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=0x7,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_b",
                converter=dpToPower,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_b",
                converter=dpToVoltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_b",
                converter=dpToCurrent,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=0x8,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_c",
                converter=dpToPower,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_c",
                converter=dpToVoltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_c",
                converter=dpToCurrent,
            ),
        ],
    )
    .tuya_dp(
        dp_id=0x66,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_dp(
        dp_id=0x70,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_dp(
        dp_id=0x7A,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)
