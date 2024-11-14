"""Signify SOC001 device."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    BinarySensorDeviceClass,
    ClusterType,
    EntityType,
    QuirkBuilder,
)
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class PhilipsOnOffCluster(CustomCluster, OnOff):
    """Philips OnOff cluster for contact sensor."""

    """Prevents the creation of the on_off entity."""

    cluster_id = 6  # 0x0006
    name = "Philips OnOff cluster"
    ep_attribute = "philips_onoff_cluster"
    SKIP_CONFIGURATION = True


class PhilipsContactCluster(CustomCluster):
    """Philips manufacturer specific cluster for contact sensor."""

    cluster_id = 64518  # 0xfc06
    name = "Philips contact cluster"
    ep_attribute = "philips_contact_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        contact = ZCLAttributeDef(
            id=0x0100,
            type=types.enum8,
            is_manufacturer_specific=True,
        )
        last_contact_change = ZCLAttributeDef(
            id=0x0101,
            type=types.uint32_t,
            is_manufacturer_specific=True,
        )
        tamper = ZCLAttributeDef(
            id=0x0102,
            type=types.enum8,
            is_manufacturer_specific=True,
        )
        last_tamper_change = ZCLAttributeDef(
            id=0x0103,
            type=types.uint32_t,
            is_manufacturer_specific=True,
        )


(
    #  <SimpleDescriptor endpoint=2 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 64518]
    #  output_clusters=[0, 3, 6, 25]>
    QuirkBuilder("Signify Netherlands B.V.", "SOC001")
    .replaces(
        PhilipsOnOffCluster,
        cluster_type=ClusterType.Client,
        endpoint_id=2,
    )
    .replaces(PhilipsContactCluster, endpoint_id=2)
    .binary_sensor(
        "contact",
        PhilipsContactCluster.cluster_id,
        endpoint_id=2,
        device_class=BinarySensorDeviceClass.OPENING,
        entity_type=EntityType.STANDARD,
        fallback_name="Contact",
    )
    .binary_sensor(
        "tamper",
        PhilipsContactCluster.cluster_id,
        endpoint_id=2,
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .add_to_registry()
)
