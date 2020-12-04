"""Konke Button Remote."""
import logging
from typing import Optional, Union
from zigpy.zcl import foundation
import zigpy.types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, PowerConfiguration


from .. import PowerConfigurationCluster, CustomCluster, CustomDevice
from ..const import (
    ARGS,
    COMMAND_ID,
    COMMAND_SINGLE,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)

KONKE_CLUSTER_ID = 0xFCC0

_LOGGER = logging.getLogger(__name__)


class KonkeOnOFFCluster(CustomCluster, OnOff):
    """Konke Test cluster implementation."""

    PRESS_TYPES = {0x0080: COMMAND_SINGLE, 0x0081: COMMAND_DOUBLE, 0x0082: COMMAND_HOLD}
    cluster_id = 6
    ep_attribute = "custom_on_off"
    attributes = {}
    server_commands = {}
    client_commands = {}

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        self.info(
            "Konke - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            tsn,
            command_id,
            args,
        )

        event_args = {
            PRESS_TYPE: PRESS_TYPES.get(command_id, command_id),
            COMMAND_ID: command_id,
            ARGS: args,
        }
        self.listener_event(ZHA_SEND_EVENT, event_args[PRESS_TYPE], event_args)


class KonkeButtonRemote(CustomDevice):
    """Konke 1-button remote device."""

    def handle_message(self, profile, cluster, src_ep, dst_ep, message):
        """Handle a device message."""
        if (
            profile == 260
            and cluster == 6
            and len(message) == 7
            and message[0] == 0x08
            and message[2] == 0x0A
        ):

            _LOGGER.info("byte 1: %s", message[0])
            _LOGGER.info("byte 2: %s", message[1])
            _LOGGER.info("byte 3: %s", message[2])
            _LOGGER.info("byte 4: %s", message[3])
            _LOGGER.info("byte 5: %s", message[4])
            _LOGGER.info("byte 6: %s", message[5])
            _LOGGER.info("byte 7: %s", message[6])

            # use the 7th byte as command_id
            new_message = bytearray(4)
            new_message[0] = message[0]
            new_message[1] = message[1]
            new_message[2] = message[6]
            new_message[3] = 0
            message = type(message)(new_message)
            super().handle_message(profile, cluster, src_ep, dst_ep, message)


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
                    KonkeOnOFFCluster,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            },
        },
    }

