"""Tuya contact sensors."""

from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_pay2byax", "TS0601")  # Cusam ZG-102ZL
    .applies_to("_TZE200_n8dljorx", "TS0601")
    .tuya_illuminance(dp_id=101)
    .tuya_contact(dp_id=1)
    .tuya_battery(dp_id=2, battery_type=BatterySize.CR2032, battery_qty=1)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_kzm5w4iz", "TS0601")
    .tuya_contact(dp_id=1)
    .tuya_battery(dp_id=3, battery_type=BatterySize.AAA, battery_qty=2)
    .tuya_vibration(dp_id=10)
    .skip_configuration()
    .add_to_registry()
)


# HOBEIAN ZG-102ZM — door + vibration sensor (Tuya EF00).
# Reports as HOBEIAN/ZG-102ZM but data comes via Tuya DPs on cluster 0xEF00.
# The HOBEIAN/ZG-102ZM signature also has an IAS Zone (0x0500), but it
# only handles contact and conflates entities; the Tuya DPs provide
# separated data, so the default IAS Zone entity is disabled.
#
# Two known hardware revisions share the HOBEIAN/ZG-102ZM signature
# (one quirk covers both):
#   - door + vibration, 1× CR2032 (IAS zone_type 0x0015)
#   - vibration only,   2× AAA    (IAS zone_type 0x002D)
# On the vibration-only revision the Contact entity never triggers
# and can be disabled in the HA entity registry.
#
# The TS0601 variants (_TZE200_wzk0x7fq, _TZE200_jfw0a4aa) have no
# IAS Zone cluster and use the same Tuya DPs.
#
# Tuya DPs (from Z2M zigbee-herdsman-converters):
#   DP 1:   vibration (bool, 1=vibrating)
#   DP 4:   battery (0-100%)
#   DP 6:   sensitivity (1-50, writable)
#   DP 101: contact (1=open, 0=closed — matches HA OPENING device class)
(
    TuyaQuirkBuilder("HOBEIAN", "ZG-102ZM")
    .applies_to("_TZE200_wzk0x7fq", "TS0601")
    .applies_to("_TZE200_jfw0a4aa", "TS0601")
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
    .tuya_battery(dp_id=4)
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
    # Disable the default IAS Zone entity (HOBEIAN signature only); it
    # shows as "opening" and conflates contact + vibration. No-op on
    # the TS0601 variants which have no IAS Zone cluster.
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        unique_id_suffix="1-1280",
        new_entity_registry_enabled_default=False,
    )
    .tuya_enchantment(read_attr_spell=True)
    .add_to_registry()
)
