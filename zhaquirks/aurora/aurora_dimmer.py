"""Device handler for Aurora dimmer switch, battery powered."""

from zigpy.profiles import zgp, zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Identify,
    LevelControl,
    OnOff,
    Ota,
)
from zigpy.zcl.clusters.lighting import Color

from zhaquirks import EventableCluster, PowerConfigurationCluster
from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
)
from zhaquirks.legacy import CustomDevice

COLOR_UP = "color_up"
COLOR_DOWN = "color_down"


class AuroraDimmerBatteryPowered(CustomDevice):
    """Aurora dimmer switch, battery powered."""

    class WallSwitchOnOffCluster(EventableCluster, OnOff):
        """WallSwitchOnOffCluster: fire events corresponding to press type."""

        # prevent creation of junk entities
        ep_attribute = "not_on_off"

        # as the device is battery powered, whether or not it thinks it is
        # on or off is irrelevant
        def _update_attribute(self, attrid, value):
            return

    class WallSwitchLevelControlCluster(EventableCluster, LevelControl):
        """WallSwitchLevelControlCluster: fire events corresponding to level changes."""

        def handle_cluster_general_request(
            self,
            hdr: foundation.ZCLHeader,
            args: list,
            *,
            dst_addressing: t.AddrMode | None = None,
        ) -> None:
            """Throw away the device's current_level reports.

            The device reports current_level after each step, and the value is
            always 254, so it would only fire a meaningless attribute event.
            """
            if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
                args = args.replace(
                    attribute_reports=[
                        attr
                        for attr in args.attribute_reports
                        if attr.attrid != self.AttributeDefs.current_level.id
                    ]
                )

            super().handle_cluster_general_request(
                hdr, args, dst_addressing=dst_addressing
            )

    class WallSwitchColorCluster(EventableCluster, Color):
        """WallSwitchColorCluster: fire events corresponding to color changes."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=261
        #  device_version=0 input_clusters=[0, 1, 3, 6, 8, 768]
        #  output_clusters=[3, 6, 8, 25, 768]>
        MODELS_INFO: [("Aurora", "2GBatteryDimmer50AU")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=261
            #  device_version=0 input_clusters=[0, 3, 6, 8, 768]
            #  output_clusters=[3, 6, 8, 768]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0 input_clusters=[] output_clusters=[33])
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    WallSwitchOnOffCluster,
                    WallSwitchLevelControlCluster,
                    WallSwitchColorCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    WallSwitchOnOffCluster,
                    WallSwitchLevelControlCluster,
                    WallSwitchColorCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (DIM_UP, RIGHT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (DIM_DOWN, RIGHT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (COLOR_UP, RIGHT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 3},
        },
        (COLOR_DOWN, RIGHT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (DIM_UP, LEFT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
            PARAMS: {"step_mode": 0},
        },
        (DIM_DOWN, LEFT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
            PARAMS: {"step_mode": 1},
        },
        (COLOR_UP, LEFT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 3},
        },
        (COLOR_DOWN, LEFT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (SHORT_PRESS, RIGHT): {
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        (SHORT_PRESS, LEFT): {
            CLUSTER_ID: 6,
            ENDPOINT_ID: 2,
            ARGS: [],
        },
    }

    # Pressing a knob reports one command per press. Turning it stays a trigger.
    button_event_entities = (
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.SINGLE_PRESS,
                    trigger=(SHORT_PRESS, RIGHT),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=1,
            unique_id_suffix="button_right",
            translation_key="right_button",
            fallback_name="Right button",
        ),
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.SINGLE_PRESS,
                    trigger=(SHORT_PRESS, LEFT),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=2,
            unique_id_suffix="button_left",
            translation_key="left_button",
            fallback_name="Left button",
        ),
    )
