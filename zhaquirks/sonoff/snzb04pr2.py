"""Sonoff SNZB-04PR2 contact sensor."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class SonoffContactCluster(CustomCluster):
    """Sonoff manufacturer specific cluster of the SNZB-04PR2."""

    cluster_id = 0xFC11
    name = "Sonoff contact cluster"
    ep_attribute = "sonoff_contact_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Reported and read as uint8 without a manufacturer code.
        # 0: tamper switch pressed, 1: tamper switch released.
        tamper = ZCLAttributeDef(
            id=0x2000,
            type=t.uint8_t,
            manufacturer_code=None,
        )


(
    #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 32, 1280, 64529, 64599]
    #  output_clusters=[3, 25]>
    QuirkBuilder("SONOFF", "SNZB-04PR2")
    .replaces(SonoffContactCluster, endpoint_id=1)
    # No reporting config: the device rejects Configure Reporting for the tamper
    # attribute (UNSUPPORTED_ATTRIBUTE) but reports changes on its own.
    .binary_sensor(
        attribute_name=SonoffContactCluster.AttributeDefs.tamper.name,
        cluster_id=SonoffContactCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .add_to_registry()
)
