"""Tuya garage door opener."""

from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t

from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE608_fmemczv1", "TS0603")
    .tuya_dp_attribute(
        dp_id=1,
        attribute_name="garage_door_button",
        type=t.Bool,
    )
    .write_attr_button(
        attribute_name="garage_door_button",
        cluster_id=TUYA_CLUSTER_ID,
        attribute_value=0x01,
        translation_key="garage_door_button",
        fallback_name="Garage door button",
    )
    .tuya_binary_sensor(
        dp_id=3,
        device_class=BinarySensorDeviceClass.GARAGE_DOOR,
        attribute_name="garage_door",
        translation_key="garage_door",
        fallback_name="Garage door",
    )
    .skip_configuration()
    .add_to_registry()
)
