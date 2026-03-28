"""HOBEIAN ZG-102ZM door and vibration sensor."""

from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder

# ZG-102ZM: Tuya-based door + vibration sensor.
# Despite reporting as HOBEIAN/ZG-102ZM, data comes via Tuya DPs on
# cluster 0xEF00. The device also has IAS Zone (0x0500) but it only
# handles contact — vibration requires Tuya DP handling.
#
# Tuya DPs (from Z2M converter in zigbee-herdsman-converters):
#   DP 1:   vibration (bool, 1=vibrating)
#   DP 4:   battery (0-100%)
#   DP 6:   sensitivity (1-50, writable)
#   DP 101: contact (bool, inverted: 0=closed, 1=open)
(
    TuyaQuirkBuilder("HOBEIAN", "ZG-102ZM")
    .tuya_binary_sensor(
        dp_id=1,
        attribute_name="vibration",
        device_class=BinarySensorDeviceClass.VIBRATION,
        entity_type=EntityType.STANDARD,
        fallback_name="Vibration",
    )
    .tuya_binary_sensor(
        dp_id=101,
        attribute_name="contact",
        device_class=BinarySensorDeviceClass.OPENING,
        entity_type=EntityType.STANDARD,
        fallback_name="Contact",
    )
    .tuya_battery(dp_id=4, battery_type=BatterySize.CR2032, battery_qty=1)
    .tuya_number(
        dp_id=6,
        type=t.uint8_t,
        attribute_name="sensitivity_level",
        min_value=1,
        max_value=50,
        step=1,
        translation_key="sensitivity_level",
        fallback_name="Sensitivity level",
    )
    # Disable the default IAS Zone entity which shows as "opening"
    # and conflates contact + vibration into a single binary sensor.
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        unique_id_suffix="1-1280",
        new_entity_registry_enabled_default=False,
    )
    .skip_configuration()
    .add_to_registry()
)
