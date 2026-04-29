"""Tuya contact sensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff

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


# TS0203: Standard Zigbee IAS Zone contact sensor (no Tuya MCU cluster).
# The On/Off output (client) cluster is intended for binding to lights, but
# ZHA creates a spurious "Opening" binary sensor from it. Suppress only that
# entity so any future legitimate entity from this cluster is unaffected.
(
    QuirkBuilder("_TZ3000_au1rjicn", "TS0203")
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .add_to_registry()
)
