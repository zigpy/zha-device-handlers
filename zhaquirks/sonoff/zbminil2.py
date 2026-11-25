"""Sonoff ZBMINIL2 - Zigbee no-neutral switch."""

from zigpy import types
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster

# Firmware 1.1.2 (OTA file version 0x00001102) added the eWeLink cluster with a
# configurable external switch trigger mode. Older firmware only allows changing
# the mode by pressing the device button three times.
ZBMINIL2_TRIGGER_MODE_FW_VERSION = 0x00001102


class SonoffZBMiniL2TriggerType(types.enum8):
    """External switch trigger type supported by the ZBMINIL2."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01


class SonoffZBMiniL2Cluster(CustomCluster):
    """Sonoff/eWeLink cluster of the ZBMINIL2."""

    cluster_id = 0xFC11
    name = "SONOFF eWeLink cluster"
    ep_attribute = "ewelink"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=SonoffZBMiniL2TriggerType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )


zbminil2_base_quirk = (
    QuirkBuilder("SONOFF", "ZBMINIL2")
    # The device reads the coordinator's KeepAlive server but does not advertise the
    # client side of the cluster. Unanswered reads make the device attempt a Trust
    # Center rejoin and eventually leave the network.
    .adds(KeepAlive, cluster_type=ClusterType.Client, endpoint_id=1)
)

(
    # older firmware, and devices not reporting a firmware version at all
    zbminil2_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(
        max_version=ZBMINIL2_TRIGGER_MODE_FW_VERSION, allow_missing=True
    )
    .add_to_registry()
)

(
    # newer firmware exposes the external switch trigger mode
    zbminil2_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(
        min_version=ZBMINIL2_TRIGGER_MODE_FW_VERSION, allow_missing=False
    )
    .replaces(SonoffZBMiniL2Cluster)
    .enum(
        SonoffZBMiniL2Cluster.AttributeDefs.external_trigger_mode.name,
        SonoffZBMiniL2TriggerType,
        SonoffZBMiniL2Cluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .add_to_registry()
)
