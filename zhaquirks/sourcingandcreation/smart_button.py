"""Device handler for Sourcing & Creation EB-SB-1B (Boulanger Essentielb 8009289) smart button."""

from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STOP,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_ON,
)
from zhaquirks.legacy import CustomDevice


class SourcingAndCreationSmartButton(CustomDevice):
    """Custom device representing Sourcing & Creation smart button."""

    signature = {
        #  <SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=2048,
        #  device_version=1,
        #  input_clusters=[0, 1, 3, 2821, 4096, 64769],
        #  output_clusters=[3, 4, 6, 8, 25, 768, 4096])>
        MODELS_INFO: [("Sourcing & Creation", "EB-SB-1B")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,  # 260
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,  # 2048
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    Diagnostic.cluster_id,  # 2821
                    LightLink.cluster_id,  # 4096
                    0xFD01,  # 64769
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768
                    LightLink.cluster_id,  # 4096
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    Diagnostic.cluster_id,  # 2821
                    LightLink.cluster_id,  # 4096
                    0xFD01,  # 64769
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768
                    LightLink.cluster_id,  # 4096
                ],
            }
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            CLUSTER_ID: 6,  # OnOff.cluster_id
            ENDPOINT_ID: 1,
        },
        (LONG_PRESS, TURN_ON): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,  # LevelControl.cluster_id
            ENDPOINT_ID: 1,
        },
        (LONG_RELEASE, TURN_ON): {
            COMMAND: COMMAND_STOP,
            CLUSTER_ID: 8,  # LevelControl.cluster_id
            ENDPOINT_ID: 1,
        },
        (DOUBLE_PRESS, TURN_ON): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
        },
    }

    # The button tells single from double presses, and toggles with on and off.
    # It steps the level while held and stops when released. The short press
    # trigger matches every event of the on/off cluster, including the attribute
    # update ZHA relays for each command, so the commands are matched instead.
    button_event_entities = (
        ButtonEventMetadata(
            events=[
                *(
                    ButtonEvent(
                        event_type=ButtonEventType.SINGLE_PRESS,
                        event_data={
                            COMMAND: command,
                            CLUSTER_ID: OnOff.cluster_id,
                            ENDPOINT_ID: 1,
                        },
                    )
                    for command in (COMMAND_ON, COMMAND_OFF)
                ),
                ButtonEvent(
                    event_type=ButtonEventType.MULTI_PRESS,
                    trigger=(DOUBLE_PRESS, TURN_ON),
                    press_count=2,
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(LONG_PRESS, TURN_ON),
                    repeats=True,
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, TURN_ON),
                    while_held=True,
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        ),
    )
