"""Module for Tuya based devices."""

import logging

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff

TUYA = "Tuya"
ATTR_ON_OFF = 0x0000
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xEF00  # Decimal: 61184
_LOGGER = logging.getLogger(__name__)

class TuyaSwitchCluster(CustomCluster,OnOff):
    """Tuya Switch Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    ep_attribute = "on_off"
    name = "Tuya Switch"
    attributes = OnOff.attributes.copy()

    manufacturer_server_commands = {
        0x0000: (
            "write_state",
            (
                foundation.Status,
                t.uint8_t,   # transactionId
                t.uint16_t,  # attribute
                t.uint8_t,   # always 0
                t.uint8_t,   # length of data
                t.Bool       # data
            ),
            False,
        ),
        0x0001: (
            "read_state",
            (
                foundation.Status,
                t.uint8_t,   # transactionId
                t.uint16_t,  # attribute
                t.uint8_t,   # always 0
                t.uint8_t,   # length of data
                t.Bool,      # data
            ),
            False,
        )
    }

    manufacturer_client_commands = {
        0x0001: (
            "read_state_rsp",
            (
                foundation.Status,
                t.uint8_t,   # transactionId
                t.uint16_t,  # attribute
                t.uint8_t,   # always 0
                t.uint8_t,   # length of data
                t.Bool,      # data
            ),
            False,
        ),
        0x0002: (
            "state_change_ntfy",
            (
                foundation.Status,
                t.uint8_t,   # transactionId
                t.uint16_t,  # attribute
                t.uint8_t,   # always 0
                t.uint8_t,   # length of data
                t.Bool,      # data
            ),
            False,
        ),
    }

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        _LOGGER.debug(
            "TuyaSwitchCluster - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            tsn,
            command_id,
            args,
        )

        if( command_id == 0x0002):
            _LOGGER.debug("Endpoint ID: %d", self._endpoint.endpoint_id)
            super()._update_attribute(ATTR_ON_OFF, args[5])

