"""Device handler for Nimly Smart Locks."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.nimly import NIMLY

# clears the mains powered mac capability flag
NIMLY_LOCK_NODE_DESCRIPTOR = NodeDescriptor(
    logical_type=2,
    complex_descriptor_available=0,
    user_descriptor_available=0,
    reserved=0,
    aps_flags=0,
    frequency_band=8,
    manufacturer_code=4660,
    maximum_buffer_size=108,
    maximum_incoming_transfer_size=127,
    server_mask=11264,
    maximum_outgoing_transfer_size=127,
    descriptor_capability_field=0,
    mac_capability_flags=NodeDescriptor.MACCapabilityFlags.AllocateAddress
    | NodeDescriptor.MACCapabilityFlags.RxOnWhenIdle,
)


class NimlyDoorLock(CustomCluster, DoorLock):
    """Nimly Door Lock cluster."""

    class AttributeDefs(DoorLock.AttributeDefs):
        """Nimly Door Lock attribute definitions."""

        nimly_last_lock_unlock_source: Final = ZCLAttributeDef(
            id=0x100,
            type=t.bitmap32,
            access="r",
            is_manufacturer_specific=True,
        )
        nimly_last_pin_code: Final = ZCLAttributeDef(
            id=0x101,
            type=t.LVBytes,
            access="r",
            is_manufacturer_specific=True,
        )


def last_action_source_converter(value: int) -> str:
    """Extract last action source value."""
    value_hex = hex(value)[2:].zfill(8)
    sources = {
        "00": "zigbee",
        "02": "keypad",
        "03": "fingerprint",
        "04": "rfid",
        "0a": "self",
    }
    return sources.get(value_hex[0:2])


def last_action_converter(value: int) -> str:
    """Extract last action value."""
    value_hex = hex(value)[2:].zfill(8)
    actions = {
        "01": "lock",
        "02": "unlock",
    }
    return actions.get(value_hex[2:4])


def last_action_user_converter(value: int) -> int:
    """Extract last action user value."""
    value_hex = hex(value)[2:].zfill(8)
    user_id = int(value_hex[4:8], 16)
    return user_id


(
    QuirkBuilder(NIMLY, "EasyFingerTouch")
    .applies_to(NIMLY, "EasyCodeTouch")
    .applies_to(NIMLY, "easyCodeTouch_v1")
    .node_descriptor(NIMLY_LOCK_NODE_DESCRIPTOR)
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source.name,
        unique_id_suffix="last_action_source",
        attribute_converter=last_action_source_converter,
        device_class=SensorDeviceClass.ENUM,
        translation_key="last_action_source",
        fallback_name="Last action source",
    )
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source.name,
        unique_id_suffix="last_action",
        attribute_converter=last_action_converter,
        device_class=SensorDeviceClass.ENUM,
        translation_key="last_action",
        fallback_name="Last action",
    )
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source.name,
        unique_id_suffix="last_action_user",
        attribute_converter=last_action_user_converter,
        translation_key="last_action_user",
        fallback_name="Last action user",
    )
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_pin_code.name,
        unique_id_suffix="last_pin_code",
        attribute_converter=lambda value: value.hex(),
        initially_disabled=True,
        translation_key="last_pin_code",
        fallback_name="Last PIN code",
    )
    .switch(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.auto_relock_time.name,
        translation_key="auto_relock",
        fallback_name="Autorelock",
    )
    .number(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.sound_volume.name,
        min_value=0,
        max_value=2,
        step=1,
        translation_key="sound_volume",
        fallback_name="Sound volume",
    )
    .add_to_registry()
)


(
    QuirkBuilder(NIMLY, "NimlyPRO24")
    .applies_to(NIMLY, "NimlyPRO")
    .applies_to(NIMLY, "NimlyCode")
    .applies_to(NIMLY, "NimlyTouch")
    .applies_to(NIMLY, "NimlyIn")
    .node_descriptor(NIMLY_LOCK_NODE_DESCRIPTOR)
    .replaces(DoublingPowerConfigurationCluster, endpoint_id=11)
    .replaces(NimlyDoorLock, endpoint_id=11)
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source.name,
        unique_id_suffix="last_action_source",
        attribute_converter=last_action_source_converter,
        device_class=SensorDeviceClass.ENUM,
        translation_key="last_action_source",
        fallback_name="Last action source",
    )
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source.name,
        unique_id_suffix="last_action",
        attribute_converter=last_action_converter,
        device_class=SensorDeviceClass.ENUM,
        translation_key="last_action",
        fallback_name="Last action",
    )
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source.name,
        unique_id_suffix="last_action_user",
        attribute_converter=last_action_user_converter,
        translation_key="last_action_user",
        fallback_name="Last action user",
    )
    .sensor(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.nimly_last_pin_code.name,
        unique_id_suffix="last_pin_code",
        attribute_converter=lambda value: value.hex(),
        initially_disabled=True,
        translation_key="last_pin_code",
        fallback_name="Last PIN code",
    )
    .switch(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.auto_relock_time.name,
        translation_key="auto_relock",
        fallback_name="Autorelock",
    )
    .number(
        endpoint_id=11,
        cluster_id=NimlyDoorLock.cluster_id,
        attribute_name=NimlyDoorLock.AttributeDefs.sound_volume.name,
        min_value=0,
        max_value=2,
        step=1,
        translation_key="sound_volume",
        fallback_name="Sound volume",
    )
    .add_to_registry()
)
