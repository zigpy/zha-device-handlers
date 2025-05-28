"""Tuya pool sensor."""

from typing import Final

from zigpy.quirks.v2.homeassistant import (
    CONCENTRATION_PARTS_PER_MILLION,
    CONDUCTIVITY,
    UnitOfConductivity,
    UnitOfElectricPotential,
)
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya import TuyaNewManufCluster
from zhaquirks.tuya.builder import BatterySize, TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

CONCENTRATION_MICROGRAMS_PER_LITER: Final = "mg/L"


class TuyaPoolManufCluster(TuyaMCUCluster):
    """Tuya Pool Sensor Manufacturer cluster."""


(
    TuyaQuirkBuilder("_TZE200_v1jqz5cy", "TS0601")
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    .tuya_battery(
        dp_id=7, battery_type=BatterySize.Built_in, battery_qty=4, battery_voltage=36
    )
    .tuya_temperature(dp_id=2, scale=10)
    .tuya_sensor(
        dp_id=10,
        attribute_name="ph_measured_value",
        divisor=100,
        type=t.uint16_t,
        state_class=SensorStateClass.VOLTAGE,
        device_class=SensorDeviceClass.PH,
        fallback_name="pH",
    )
    .tuya_sensor(
        dp_id=1,
        attribute_name="total_dissolved_solids",
        type=t.uint16_t,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="total_dissolved_solids",
        fallback_name="Total dissolved solids",
    )
    .tuya_sensor(
        dp_id=11,
        attribute_name="ec_measured_value",
        type=t.uint16_t,
        unit=UnitOfConductivity.MICROSIEMENS_PER_CM,
        state_class=SensorStateClass.CONDUCTIVITY,
        fallback_name="Electrical conductivity",
    )
    .tuya_sensor(
        dp_id=117,
        attribute_name="salt_measured_value",
        type=t.uint16_t,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="salt_measured_value",
        fallback_name="Salt concentration",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="redox_potential",
        type=t.uint16_t,
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.VOLTAGE,
        translation_key="redox_potential",
        fallback_name="ORP level",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="cl_measured_value",
        type=t.uint16_t,
        unit=CONCENTRATION_MICROGRAMS_PER_LITER,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="cl_measured_value",
        fallback_name="Chlorine concentration",
    )
    # TODO: 103 enum ?  pH Calibration
    # TODO: 104 bool ?
    # TODO: 105 uint16
    .tuya_number(
        dp_id=106,
        attribute_name="ph_max_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=14,
        mode="box",
        device_class=NumberDeviceClass.PH,
        translation_key="ph_max_value",
        fallback_name="pH maximum value",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="ph_min_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=14,
        mode="box",
        device_class=NumberDeviceClass.PH,
        translation_key="ph_min_value",
        fallback_name="pH minimum value",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="ec_max_value",
        type=t.uint16_t,
        multiplier=11,
        step=1,
        min_value=0,
        max_value=20000,
        mode="box",
        unit=CONDUCTIVITY,
        device_class=SensorDeviceClass.VOLTAGE,
        translation_key="ec_max_value",
        fallback_name="EC maximum value",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="ec_min_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=0,
        max_value=20000,
        mode="box",
        unit=CONDUCTIVITY,
        device_class=SensorDeviceClass.VOLTAGE,
        translation_key="ec_min_value",
        fallback_name="EC minimum value",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="orp_max_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=-999,
        max_value=999,
        mode="box",
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="orp_max_value",
        fallback_name="ORP maximum value",
    )
    .tuya_number(
        dp_id=111,
        attribute_name="orp_min_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=-999,
        max_value=999,
        mode="box",
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="orp_min_value",
        fallback_name="ORP minimum value",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="cl_max_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=4,
        mode="box",
        unit=CONCENTRATION_MICROGRAMS_PER_LITER,
        translation_key="cl_max_value",
        fallback_name="Cl maximum value",
    )
    .tuya_number(
        dp_id=113,
        attribute_name="cl_min_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=4,
        mode="box",
        unit=CONCENTRATION_MICROGRAMS_PER_LITER,
        translation_key="cl_min_value",
        fallback_name="Cl minimum value",
    )
    # TODO: 114 uint16_t payload=0  pH Calibration
    # TODO: 115 uint16_t payload=0  EC Calibration
    # TODO: 116 uint16_t payload=0  ORP Calibration
    # TODO: 118 bool payload=0 (false)
    # Press button to manually refresh sensor data.
    .command_button(
        command_name="query_data",
        cluster_id=TuyaNewManufCluster.cluster_id,
        translation_key="Update",
        fallback_name="Update",
    )
    .add_to_registry(replacement_cluster=TuyaPoolManufCluster)
)
