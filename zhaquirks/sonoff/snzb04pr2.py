"""Sonoff SNZB-04PR2 device."""

# Changes compared with the SONOFF-provided ZHA quirk:
#
# SONOFF's original quirk defined the tamper attribute on cluster 0xFC11,
# attribute 0x2000, as a manufacturer-specific Bool:
#
#   type=types.Bool
#   is_manufacturer_specific=True
#
# Device logs show that the SNZB-04PR2 actually reports this attribute as a
# normal ZCL Report Attributes frame on the manufacturer-specific cluster:
#
#   cluster_id=0xFC11
#   attribute_id=0x2000
#   type=uint8_t
#   manufacturer_code=None
#   value=0/1
#
# Therefore this quirk changes the attribute definition to types.uint8_t and
# removes is_manufacturer_specific=True. The cluster remains manufacturer-
# specific, but the attribute report itself is not manufacturer-coded.
#
# Additionally, live tamper reports were received and decoded by ZHA but did not
# reliably update the binary sensor state. handle_cluster_general_request()
# catches Report Attributes command 0x0A for attribute 0x2000 and updates the
# attribute cache with the actual reported 0/1 value, so live tamper changes
# update immediately without double-processing the report.

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffContactCluster(CustomCluster):
    """Sonoff manufacturer specific cluster for contact sensor."""

    cluster_id = 64529  # 0xfc11
    name = "Sonoff contact cluster"
    ep_attribute = "sonoff_contact_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # SONOFF-provided version:
        #
        # tamper = ZCLAttributeDef(
        #     id=0x2000,
        #     type=types.Bool,
        #     is_manufacturer_specific=True,
        # )

        tamper = ZCLAttributeDef(
            id=0x2000,
            type=types.uint8_t,
            access="rp",
        )

    def handle_cluster_general_request(self, hdr, args, *extra, **kwargs):
        """Handle reported tamper attribute updates."""
        if hdr.command_id == 0x0A:  # Report Attributes
            for attr in getattr(args, "attribute_reports", []):
                if attr.attrid == self.AttributeDefs.tamper.id:
                    self._update_attribute(attr.attrid, int(attr.value.value))
                    return

        super().handle_cluster_general_request(hdr, args, *extra, **kwargs)


(
    #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 32, 1280, 64529, 64567]
    #  output_clusters=[3, 6, 25]>
    # QuirkBuilder("eWeLink", "SNZB-04PR2")
    QuirkBuilder("SONOFF", "SNZB-04PR2")
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
    .replaces(SonoffContactCluster, endpoint_id=1)
    .binary_sensor(
        "tamper",
        SonoffContactCluster.cluster_id,
        endpoint_id=1,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=1,
        ),
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .add_to_registry()
)
