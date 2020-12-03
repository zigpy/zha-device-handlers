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

    def handle_message(self, hdr, args):
        """Handle a message on this cluster."""
        self.debug("ZCL request header: %s", hdr)
        self.debug("ZCL request 0x%04x: %s", hdr.command_id, args)
    
    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default command and log the stuff."""
        self.debug("command_id: %s args: %s", command_id, args)


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
                    KonkeTestCluster,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            },
        },
    }


