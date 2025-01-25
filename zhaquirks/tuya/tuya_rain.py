"""Quirk for TS0207 rain sensors."""

from zigpy.quirks.v2.homeassistant import LIGHT_LUX, EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.tuya import BatterySize, TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaIasZone(IasZone, TuyaLocalCluster):
    """IAS Zone for rain sensors."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Water_Sensor
    }


(
    TuyaQuirkBuilder("_TZ3210_tgvtvdoc", "TS0207")
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
        translation_key="cleaning_reminder",
        fallback_name="Cleaning reminder",
    )
    .tuya_dp(
        dp_id=105,
        ep_attribute=TuyaIasZone.ep_attribute,
        attribute_name=TuyaIasZone.AttributeDefs.zone_status.name,
        converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x > 100 else 0,
    )
    # .sensor(
    #     type=t.uint32_t,
    #     attribute_name=TuyaIasZone.AttributeDefs.zone_status.name,
    #     device_class=SensorDeviceClass.VOLTAGE,
    #     unit=UnitOfElectricPotential.MILLIVOLT,
    #     fallback_name="Rain Intensity",
    # )
    .adds(TuyaIasZone)
    .skip_configuration()
    .add_to_registry()
)
