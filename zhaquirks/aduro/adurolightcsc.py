"""ADUROLIGHT ADUROLIGHT_CSC device."""

import logging
from typing import Any, Optional, Union

from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef, ZCLHeader

from zhaquirks import Bus, EventableCluster
from zhaquirks.const import (
    ARGS,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TOGGLE,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)

ADUROLIGHT_REMOTE_CLUSTER_ID = 0xFCCC
ADUROLIGHT_REMOTE_COMMAND_BUTTON_EVENT = 0x00
SCENE_NO_GROUP = 0x0000


# Adurolight remote cluster implementation
class AdurolightRemoteCluster(EventableCluster):
    """Adurolight manufacturer specific cluster for remote."""

    cluster_id = ADUROLIGHT_REMOTE_CLUSTER_ID
    name = "Adurolight Remote Cluster"
    ep_attribute = "adurolight_remote_cluster"

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        button_event = ZCLCommandDef(
            id=ADUROLIGHT_REMOTE_COMMAND_BUTTON_EVENT,
            schema={
                "param1": t.uint8_t,
                "param2": t.uint8_t,
                "param3": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )

    def handle_cluster_request(
        self,
        hdr: ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        if hdr.command_id == ADUROLIGHT_REMOTE_COMMAND_BUTTON_EVENT:
            _LOGGER.info("Got button press on adurolight remote cluster: %s", args[1])
            self.endpoint.device.scenes_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, "view", [SCENE_NO_GROUP, args[1]]
            )
        else:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class AduroScenesCluster(Scenes, EventableCluster):
    """Scenes cluster to map preset buttons to the "view" command."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.scenes_bus.add_listener(self)


class AdurolightCSC(CustomDevice):
    """ADUROLIGHT ADUROLIGHT_CSC device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.scenes_bus = Bus()
        super().__init__(*args, **kwargs)

    class ScenesRemoteOnOffCluster(EventableCluster, OnOff):
        """ScenesRemoteOnOffCluster: fire events corresponding to press type."""

        # prevent creation of junk entities
        ep_attribute = "not_on_off"

        # as the device is battery powered, whether or not it thinks it is
        # on or off is irrelevant
        def _update_attribute(self, attrid, value):
            return

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49246 device_type=2064
        # device_version=2
        # input_clusters=[0, 1, 3, 4, 5, 6, 8, 768, 4096, 64716]
        # output_clusters=[0, 3, 4, 5, 6, 8, 768, 4096, 64716]>
        MODELS_INFO: [
            ("ADUROLIGHT", "ADUROLIGHT_CSC"),
            ("AduroSmart Eria", "ADUROLIGHT_CSC"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AdurolightRemoteCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AdurolightRemoteCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 1010,
                INPUT_CLUSTERS: [
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    AduroScenesCluster,
                    ScenesRemoteOnOffCluster,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AdurolightRemoteCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    AduroScenesCluster,
                    ScenesRemoteOnOffCluster,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    AdurolightRemoteCluster,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TOGGLE): {
            COMMAND: "view",
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            ARGS: [0, 0x0],
        },
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: "view",
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            ARGS: [0, 0x1],
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: "view",
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            ARGS: [0, 0x2],
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: "view",
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            ARGS: [0, 0x3],
        },
    }
