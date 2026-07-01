"""Quirk for TS0207 rain sensors."""

from zigpy.quirks.v2.homeassistant import LIGHT_LUX, EntityType, UnitOfElectricPotential
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.tuya import TUYA_CLUSTER_ID, BatterySize, TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster


class TuyaIasZone(IasZone, TuyaLocalCluster):
    """IAS Zone for rain sensors."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Water_Sensor
    }


(
    TuyaQuirkBuilder("_TZ3210_tgvtvdoc", "TS0207")
    .applies_to("_TZ3210_p68kms0l", "TS0207")
    .tuya_battery(
        dp_id=4, battery_type=BatterySize.Other, battery_qty=1, battery_voltage=30
    )
    .tuya_illuminance(dp_id=101)
    .tuya_sensor(
        dp_id=102,
        attribute_name="average_light_intensity_20mins",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
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
        device_class=SensorDeviceClass.DURATION,
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
    .skip_configuration()
    .add_to_registry()
)
