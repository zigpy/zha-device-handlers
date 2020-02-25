"""Samjin button device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from . import CLICK_TYPES, SAMJIN
from ..const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    COMMAND_ID,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)


class SamjinButton(CustomDevice):
    """Samjin button device."""

    class IASCluster(CustomCluster, IasZone):
        """Occupancy cluster."""

        cluster_id = IasZone.cluster_id

        def handle_cluster_request(self, tsn, command_id, args):
            """Handle a cluster command received on this cluster."""
            if command_id == 0:
                state = args[0] & 3
                event_args = {
                    PRESS_TYPE: CLICK_TYPES[state],
                    COMMAND_ID: command_id,
                    ARGS: args,
                }
                action = "button_{}".format(CLICK_TYPES[state])
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        # output_clusters=[3, 25]>
        MODELS_INFO: [(SAMJIN, BUTTON)],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IASCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IASCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_BUTTON_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_BUTTON_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_BUTTON_HOLD},
    }
