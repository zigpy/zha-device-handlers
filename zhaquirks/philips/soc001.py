"""Signify SOC001 device."""

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


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

    # catch when contact attribute is updated and forward to OnOff cluster
    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        on_off_cluster = self.endpoint.out_clusters[OnOff.cluster_id]
        if (
            attrid == self.AttributeDefs.contact.id
            and on_off_cluster.get(OnOff.AttributeDefs.on_off.id) != value
        ):
            # This seems to happen after the real OnOff attribute change,
            # so we can avoid a duplicate event by checking the current value.
            # We'll only update the OnOff cluster if the value is different then,
            # this is likely only the case when an update was missed, and we later
            # get an attribute report for the custom contact attribute.
            on_off_cluster.update_attribute(OnOff.AttributeDefs.on_off.id, value)


(
    #  <SimpleDescriptor endpoint=2 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 64518]
    #  output_clusters=[0, 3, 6, 25]>
    QuirkBuilder("Signify Netherlands B.V.", "SOC001")
    .replaces(PhilipsContactCluster, endpoint_id=2)
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
