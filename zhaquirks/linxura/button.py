"""Linxura button device."""


from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.security import IasZone
from zhaquirks.linxura import LinxuraIASCluster

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)

# from __init__ import LINXURA, LinxuraIASCluster
from zhaquirks.linxura import LINXURA

# DOUBLE = 2
# HOLD = 3
# # LINXURA = "Linxura"
# SINGLE = 1

# CLICK_TYPES = {SINGLE: "single", DOUBLE: "double", HOLD: "hold"}

BTN_1 = "Button 1"
BTN_2 = "Button 2"
BTN_3 = "Button 3"
BTN_4 = "Button 4"


# class LinxuraIASCluster(CustomCluster, zigpy.zcl.clusters.security.IasZone):
#     """Occupancy cluster."""

#     def handle_cluster_request(
#         self,
#         hdr: foundation.ZCLHeader,
#         args: list[Any],
#         *,
#         dst_addressing: Optional[
#             Union[Addressing.Group, Addressing.IEEE, Addressing.NWK]
#         ] = None,
#     ):
#         """Handle a cluster command received on this cluster."""
#         # self.info(
#         #    "Linxura general request - handle_cluster_general_request: header: %s - args: [%s]",
#         #    hdr,
#         #    args,
#         # )
#         if hdr.command_id == 0:
#             # self.info(
#             #    "Linxura general request - state: %s",
#             #    args[0],
#             # )
#             state = args[0]
#             if state >= 4:
#                 return
#             else:
#                 event_args = {
#                     PRESS_TYPE: CLICK_TYPES[state],
#                     COMMAND_ID: hdr.command_id,
#                     ARGS: args,
#                 }
#                 action = f"button_{CLICK_TYPES[state]}"
#                 self.listener_event(ZHA_SEND_EVENT, action, event_args)


class LinxuraButton(CustomDevice):
    """Linxura button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 3, 1280]=>input_clusters=[0, 1280]
        # output_clusters=[3]>=>output_clusters=[]
        MODELS_INFO: [(LINXURA, "Smart Controller")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LinxuraIASCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LinxuraIASCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LinxuraIASCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LinxuraIASCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, BTN_1): {
            COMMAND: COMMAND_BUTTON_DOUBLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BTN_1): {
            COMMAND: COMMAND_BUTTON_SINGLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 1,
        },
        (LONG_PRESS, BTN_1): {
            COMMAND: COMMAND_BUTTON_HOLD,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 1,
        },
        (DOUBLE_PRESS, BTN_2): {
            COMMAND: COMMAND_BUTTON_DOUBLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 2,
        },
        (SHORT_PRESS, BTN_2): {
            COMMAND: COMMAND_BUTTON_SINGLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 2,
        },
        (LONG_PRESS, BTN_2): {
            COMMAND: COMMAND_BUTTON_HOLD,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 2,
        },
        (DOUBLE_PRESS, BTN_3): {
            COMMAND: COMMAND_BUTTON_DOUBLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 3,
        },
        (SHORT_PRESS, BTN_3): {
            COMMAND: COMMAND_BUTTON_SINGLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 3,
        },
        (LONG_PRESS, BTN_3): {
            COMMAND: COMMAND_BUTTON_HOLD,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 3,
        },
        (DOUBLE_PRESS, BTN_4): {
            COMMAND: COMMAND_BUTTON_DOUBLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 4,
        },
        (SHORT_PRESS, BTN_4): {
            COMMAND: COMMAND_BUTTON_SINGLE,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 4,
        },
        (LONG_PRESS, BTN_4): {
            COMMAND: COMMAND_BUTTON_HOLD,
            CLUSTER_ID: IasZone.cluster_id,
            ENDPOINT_ID: 4,
        },
    }
