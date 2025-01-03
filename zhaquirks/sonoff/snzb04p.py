"""Sonoff SNZB-04 device."""

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


class SonoffOnOffCluster(CustomCluster, OnOff):
    """Sonoff OnOff cluster for contact sensor."""

    """Prevents the creation of the on_off entity since it is not functionnal."""

    cluster_id = 6  # 0x0006
    name = "Sonoff OnOff cluster"
    ep_attribute = "sonoff_onoff_cluster"
    SKIP_CONFIGURATION = True


class SonoffContactCluster(CustomCluster):
    """Sonoff manufacturer specific cluster for contact sensor."""

    cluster_id = 64529  # 0xfc11
    name = "Sonoff contact cluster"
    ep_attribute = "sonoff_contact_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        tamper = ZCLAttributeDef(
            id=0x2000,
            type=types.Bool,
            is_manufacturer_specific=True,
        )


(
    #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 32, 1280, 64529, 64567]
    #  output_clusters=[3, 6, 25]>
    QuirkBuilder("eWeLink", "SNZB-04P")
    .replaces(
        SonoffOnOffCluster,
        cluster_type=ClusterType.Client,
        endpoint_id=1,
    )
    .replaces(SonoffContactCluster, endpoint_id=1)
    .binary_sensor(
        "tamper",
        SonoffContactCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .add_to_registry()
)
