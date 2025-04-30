"""Tuya Din Power Meter."""

from zigpy.quirks.v2 import SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfEnergy, UnitOfTime
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class Tuya3PhaseElectricalMeasurementV1_5(ElectricalMeasurement, TuyaLocalCluster):
    """
    Tuya Electrical Measurement cluster:
        - Model: SDM01V1.5
        - Description: Smart energy monitor for 3P+N system
        - Manufacturer: Zemismart
    """

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
    }


(
    TuyaQuirkBuilder("_TZE204_gomuk3dc", "TS0601")
    .applies_to("_TZE284_gomuk3dc", "TS0601")
    .applies_to("_TZE200_gomuk3dc", "TS0601")
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy_consumed",
        type=t.uint32_t,
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
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="total_active_power",
    )
    .tuya_dp(
        dp_id=32,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="ac_frequency",
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
        translation_key="update_frequency",
        fallback_name="Update frequency",
        access=foundation.ZCLAttributeAccess.Write,
    )
    .tuya_dp(
        dp_id=103,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="rms_voltage_ph_a",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="rms_current_ph_a",
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="active_power_ph_a",
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="power_factor_ph_a",
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
    .tuya_dp(
        dp_id=112,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="rms_voltage_ph_b",
    )
    .tuya_dp(
        dp_id=113,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="rms_current_ph_b",
    )
    .tuya_dp(
        dp_id=114,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="active_power_ph_b",
    )
    .tuya_dp(
        dp_id=117,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
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
    .tuya_dp(
        dp_id=121,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="rms_voltage_ph_c",
    )
    .tuya_dp(
        dp_id=122,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="rms_current_ph_c",
    )
    .tuya_dp(
        dp_id=123,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
        attribute_name="active_power_ph_c",
    )
    .tuya_dp(
        dp_id=126,
        ep_attribute=Tuya3PhaseElectricalMeasurementV1_5.ep_attribute,
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
    .adds(Tuya3PhaseElectricalMeasurementV1_5)
    # .skip_configuration()
    .add_to_registry()
)
