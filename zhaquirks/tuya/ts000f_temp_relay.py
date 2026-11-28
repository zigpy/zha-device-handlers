"""Tuya TS000F relay with a temperature probe reported over the Tuya MCU cluster.

Mumubiz TYZGTH1CH-D1RF (_TZ3218_7fiyo3kv). The relay itself is the standard ZCL OnOff
cluster; the probe and settings use Tuya datapoints (Zigbee2MQTT model TYZGTH1CH-D1RF):
102 temperature (0.1 C), 108 temperature calibration (0.1 C, -10..10), 111 child lock.
Writes use the Tuya "send data" (0x04) command, as Zigbee2MQTT does for this device.
"""

import zigpy.types as t

from zhaquirks.builder import EntityType, UnitOfTemperature
from zhaquirks.tuya import TUYA_SEND_DATA
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZ3218_7fiyo3kv", "TS000F")
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    .tuya_temperature(dp_id=102, scale=10)
    .tuya_number(
        dp_id=108,
        attribute_name="temperature_calibration",
        type=t.int16s,
        min_value=-10,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .tuya_switch(
        dp_id=111,
        attribute_name="child_lock",
        entity_type=EntityType.CONFIG,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .add_to_registry(mcu_write_command=TUYA_SEND_DATA)
)
