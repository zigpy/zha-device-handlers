"""Signify SOC001 device."""

from zigpy.quirks.v2 import QuirkBuilder, ClusterType, BinarySensorDeviceClass
import zigpy.types as types
from zigpy.quirks import CustomCluster


class PhilipsContactCluster(CustomCluster):
    """Philips manufacturer specific cluster for contact sensor."""

    cluster_id = 64518  # 0xfc06
    name = "Philips contact cluster"
    ep_attribute = "philips_contact_cluster"
    attributes = {
        0x0100: ("contact", types.enum8, True),
        0x0101: ("last_contact_change", types.uint32_t, True),
        0x0102: ("tamper", types.enum8, True),
        0x0103: ("last_tamper_change", types.uint32_t, True),
    }


(
    #  <SimpleDescriptor endpoint=2 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 64518]
    #  output_clusters=[0, 3, 6, 25]>
    QuirkBuilder("Signify Netherlands B.V.", "SOC001")
    .removes(cluster_id=6, endpoint_id=2, cluster_type=ClusterType.Client)
    .replaces(
        replacement_cluster_class=PhilipsContactCluster, cluster_id=64518, endpoint_id=2
    )
    .binary_sensor(
        attribute_name="contact",
        cluster_id=64518,  # 0xfc06
        endpoint_id=2,
        device_class=BinarySensorDeviceClass.OPENING,
    )
    .binary_sensor(
        attribute_name="tamper",
        cluster_id=64518,  # 0xfc06
        endpoint_id=2,
        device_class=BinarySensorDeviceClass.TAMPER,
    )
    .add_to_registry()
)
