"""Tuya Power Meter."""

from zigpy.quirks.v2 import EntityType, SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping


def dp_to_power(data: bytes) -> int:
    """Convert DP data to power value."""
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = int(data)
    if power > 0x0FFFFFFF:
        power = (0x1999999C - power) * -1
    return power


def multi_dp_to_power(data: bytes) -> int:
    """Convert DP data to power value."""
    # Support negative power readings
    # From https://github.com/Koenkk/zigbee2mqtt/issues/18603#issuecomment-2277697295
    power = data[7] | (data[6] << 8)
    if power > 0x7FFF:
        power = (0x999A - power) * -1
    return power


def multi_dp_to_current(data: bytes) -> int:
    """Convert DP data to current value."""
    return data[4] | (data[3] << 8)


def multi_dp_to_voltage(data: bytes) -> int:
    """Convert DP data to voltage value."""
    return data[1] | (data[0] << 8)


class Tuya3PhaseElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
    """Tuya Electrical Measurement cluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
    }


(
    TuyaQuirkBuilder("_TZE200_nslr42tt", "TS0601")
    .tuya_temperature(dp_id=133, scale=10)
    .tuya_sensor(
        dp_id=134,
        attribute_name="device_status",
        type=t.int32s,
        fallback_name="Device status",
        translation_key="device_status",
    )
    .tuya_dp(
        dp_id=132,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
    )
    # Energy
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="energy_ph_a",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=111,
        attribute_name="energy_ph_b",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=121,
        attribute_name="energy_ph_c",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=9,
        attribute_name="power",
        type=t.int32s,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        fallback_name="Total power",
        converter=dp_to_power,
    )
    .tuya_sensor(
        dp_id=131,
        attribute_name="current",
        type=t.int32s,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Total current",
    )
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=7,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_b",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_b",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_b",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp_multi(
        dp_id=8,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="active_power_ph_c",
                converter=multi_dp_to_power,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_voltage_ph_c",
                converter=multi_dp_to_voltage,
            ),
            DPToAttributeMapping(
                ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                attribute_name="rms_current_ph_c",
                converter=multi_dp_to_current,
            ),
        ],
    )
    .tuya_dp(
        dp_id=102,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_dp(
        dp_id=112,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .removes(LevelControl.cluster_id)
    .removes(OnOff.cluster_id)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_dikb3dp6", "TS0601")
    .applies_to("_TZE204_dikb3dp6", "TS0601")
    .applies_to("_TZE284_dikb3dp6", "TS0601")
    .applies_to("_TZE284_wbhaespm", "TS0601")  # reported in #4277
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.int32s,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Total energy",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="energy_produced",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced",
        fallback_name="Energy produced",
    )
    .tuya_dp(
        dp_id=29,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=32,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="ac_frequency",
        converter=lambda x: x / 100,
    )
    .tuya_sensor(
        dp_id=50,
        attribute_name="power_factor",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        unit=PERCENTAGE,
        translation_key="total_power_factor",
        fallback_name="Total power factor",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="update_frequency",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=3600,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="update_frequency",
        fallback_name="Update frequency",
    )
    # Phase A
    .tuya_dp(
        dp_id=103,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor",
    )
    .tuya_sensor(
        dp_id=109,
        attribute_name="energy_consumed_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_a",
        fallback_name="Energy phase A",
    )
    .tuya_sensor(
        dp_id=110,
        attribute_name="energy_produced_ph_a",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_a",
        fallback_name="Energy produced phase A",
    )
    # Phase B
    .tuya_dp(
        dp_id=112,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_b",
    )
    .tuya_dp(
        dp_id=113,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_b",
    )
    .tuya_dp(
        dp_id=114,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_b",
    )
    .tuya_dp(
        dp_id=117,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_b",
    )
    .tuya_sensor(
        dp_id=118,
        attribute_name="energy_consumed_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_b",
        fallback_name="Energy phase B",
    )
    .tuya_sensor(
        dp_id=119,
        attribute_name="energy_produced_ph_b",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_b",
        fallback_name="Energy produced phase B",
    )
    # Phase C
    .tuya_dp(
        dp_id=121,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage_ph_c",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="rms_current_ph_c",
    )
    .tuya_dp(
        dp_id=123,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="active_power_ph_c",
    )
    .tuya_dp(
        dp_id=126,
        ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
        attribute_name="power_factor_ph_c",
    )
    .tuya_sensor(
        dp_id=127,
        attribute_name="energy_consumed_ph_c",
        divisor=100,
        type=t.uint32_t,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_ph_c",
        fallback_name="Energy phase C",
    )
    .tuya_sensor(
        dp_id=128,
        attribute_name="energy_produced_ph_c",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_produced_ph_c",
        fallback_name="Energy produced phase C",
    )
    .adds(Tuya3PhaseElectricalMeasurement)
    .skip_configuration()
    .add_to_registry()
)
