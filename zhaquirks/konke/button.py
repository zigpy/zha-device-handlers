"""Konke Button Remote."""

from typing import Optional, Union
from zigpy.zcl import foundation
import zigpy.types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, PowerConfiguration


from .. import PowerConfigurationCluster, CustomCluster, CustomDevice
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

KONKE_CLUSTER_ID = 0xFCC0

class KonkeTestCluster(CustomCluster, OnOff):
    """Konke Test cluster implementation."""

    cluster_id = 6
    ep_attribute = "custom_on_off"
    attributes = {}
    server_commands = {}
    client_commands = {}

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        _LOGGER.debug(
            "Konke - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            tsn,
            command_id,
            args,
        )
        
    def handle_cluster_general_request(self, header, args):
        """Handle the cluster command."""
        _LOGGER.debug(
            "Konke general request - handle_cluster_request: header: %s - args: [%s]",
            header,
            args,
        )  



class KonkeButtonRemote(CustomDevice):
    """Konke 1-button remote device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2
        # device_version=0
        # input_clusters=[0, 1, 3, 6, 64704]
        # output_clusters=[3, 64704]>
        MODELS_INFO: [("KONKE", "3AFE170100510001"),("KONKE", "3AFE280100510001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KonkeTestCluster, KONKE_CLUSTER_ID],
            },
        },
    }


