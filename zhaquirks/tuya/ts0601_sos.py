"""(MOES) Tuya SOS button."""

import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration

from zhaquirks import CustomDevice
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.tuya import TuyaManufClusterAttributes

_LOGGER = logging.getLogger(__name__)

# Constants for Tuya Data Points
TUYA_DP_ID_SMART_EVENT = 1024  # Base DP for events
HEARTBEAT_EVENT = "heartbeat"


class TuyaSOSButtonCluster(TuyaManufClusterAttributes):
    """Manufacturer specific cluster for Tuya SOS button."""

    def handle_cluster_request(self, hdr, args):
        """Handle Tuya cluster requests and translate to ZHA events."""
        try:
            payload = args[0]
            dp_id = getattr(payload, "command_id", "unknown")

            # Mapping Data Points to actions
            if dp_id == 1050:
                action = SHORT_PRESS
            elif dp_id == 1051:
                action = DOUBLE_PRESS
            elif dp_id == 1053:
                action = LONG_PRESS
            elif dp_id == 515:
                # Periodic 4-hour keep-alive signal
                action = HEARTBEAT_EVENT
                _LOGGER.debug("Heartbeat received from SOS button (DP 515)")
            else:
                action = f"button_{dp_id}"

            # Fire ZHA event only for physical interactions, filtering heartbeats
            if action != HEARTBEAT_EVENT:
                _LOGGER.info("Firing ZHA event for action: %s", action)
                self.listener_event("zha_send_event", action, {"unique_id": dp_id})

        except Exception as e:
            _LOGGER.error("Error handling Tuya SOS cluster request: %s", str(e))

        super().handle_cluster_request(hdr, args)


class TuyaSOSButton(CustomDevice):
    """Quirk for Tuya SOS button _TZE200_vrcfo4i0."""

    signature = {
        MODELS_INFO: [("_TZE200_vrcfo4i0", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 1026,  # IAS_ZONE
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    0x0500,  # IAS_ZONE
                    0xEF00,  # Tuya Manufacturer Specific
                ],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TuyaSOSButtonCluster,
                ],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {COMMAND: SHORT_PRESS},
        (DOUBLE_PRESS, BUTTON): {COMMAND: DOUBLE_PRESS},
        (LONG_PRESS, BUTTON): {COMMAND: LONG_PRESS},
    }
