"""Quirk for TS0207 rain sensors."""

import zigpy.types as t
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    LIGHT_LUX,
    BinarySensorDeviceClass,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import TUYA_CLUSTER_ID, BatterySize, TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


class TuyaRainPowerConfiguration(CustomCluster, PowerConfiguration):
    """Power configuration for rain sensors.

    The battery level is reported over ZCL, so this is a real cluster that ZHA can
    bind, configure reporting on and read. Tuya DP 4 is still mapped onto it.
    """

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: BatterySize.Other,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 1,
        PowerConfiguration.AttributeDefs.battery_rated_voltage.id: 30,
    }


class TuyaIasZone(IasZone, TuyaLocalCluster):
    """IAS Zone for rain sensors."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Water_Sensor
    }


(
    TuyaQuirkBuilder("_TZ3210_tgvtvdoc", "TS0207")
    .applies_to("_TZ3210_p68kms0l", "TS0207")
    .tuya_battery(dp_id=4, power_cfg=TuyaRainPowerConfiguration)
    .tuya_illuminance(dp_id=101)
    .tuya_sensor(
        dp_id=102,
        attribute_name="average_light_intensity_20mins",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ILLUMINANCE,
        unit=LIGHT_LUX,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="average_light_intensity_20mins",
        fallback_name="Average light intensity last 20 min",
    )
    .tuya_sensor(
        dp_id=103,
        attribute_name="todays_max_light_intensity",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ILLUMINANCE,
        unit=LIGHT_LUX,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="todays_max_light_intensity",
        fallback_name="Today's max light intensity",
    )
    .tuya_binary_sensor(
        dp_id=104,
        attribute_name="cleaning_reminder",
        device_class=BinarySensorDeviceClass.PROBLEM,
        fallback_name="Cleaning reminder",
    )
    .tuya_dp_multi(
        dp_id=105,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaIasZone.ep_attribute,
                attribute_name=TuyaIasZone.AttributeDefs.zone_status.name,
                converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x > 100 else 0,
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaMCUCluster.ep_attribute,
                attribute_name="rain_intensity",
            ),
        ],
    )
    .tuya_attribute(
        dp_id=105,
        attribute_name="rain_intensity",
        type=t.uint32_t,
        is_manufacturer_specific=True,
    )
    .sensor(
        "rain_intensity",
        TUYA_CLUSTER_ID,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.MILLIVOLT,
        entity_type=EntityType.STANDARD,
        fallback_name="Rain intensity",
    )
    .adds(TuyaIasZone)
    .add_to_registry()
)
