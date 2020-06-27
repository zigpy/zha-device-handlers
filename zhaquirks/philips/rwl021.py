"""Phillips RWL021 device."""
import logging

from zigpy.profiles import zha, zll
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)

from ..const import (
    ARGS,
    COMMAND_ID,
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF_WITH_EFFECT,
    COMMAND_ON,
    COMMAND_STEP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
_LOGGER = logging.getLogger(__name__)


class BasicCluster(CustomCluster, Basic):
    """Phillips Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes.update({0x0031: ("phillips", t.bitmap16)})

    attr_config = {0x0031: 0x000B}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=0x100B)
        return result


class PhillipsCluster(CustomCluster):
    """Phillips Basic cluster."""

    cluster_id = 64512
    name = "PhillipsCluster"
    ep_attribute = "phillips_cluster"
    attributes = {}
    server_commands = {}
    client_commands = {
        0x0000: (
            "notification",
            (t.uint8_t, t.uint24_t, t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        )
    }
    BUTTONS = {1: "on", 2: "up", 3: "down", 4: "off"}
    PRESS_TYPES = {0: "press", 1: "hold", 2: "short_release", 3: "long_release"}

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        _LOGGER.info(
            "handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            tsn,
            command_id,
            args,
        )
        button = self.BUTTONS.get(args[0], args[0])
        press_type = self.PRESS_TYPES.get(args[2], args[2])

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
            COMMAND_ID: command_id,
            ARGS: args,
        }
        action = "{}_{}".format(button, press_type)
        self.listener_event(ZHA_SEND_EVENT, action, event_args)


class PhilipsRWL021(CustomDevice):
    """Phillips RWL021 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2096
        #  device_version=2
        #  input_clusters=[0]
        #  output_clusters=[0, 3, 4, 6, 8, 5]>
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.SCENE_CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=12
            #  device_version=0
            #  input_clusters=[0, 1, 3, 15, 64512]
            #  output_clusters=[25]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    64512,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        }
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            2: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PhillipsCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF_WITH_EFFECT},
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [0, 30, 9],
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [0, 56, 9],
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [1, 30, 9],
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [1, 56, 9],
        },
    }
