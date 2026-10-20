"""Osram Smart+ Switch Mini device."""

from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.legacy import CustomDevice
from zhaquirks.osram import OSRAM

OSRAM_CLUSTER = 0xFD00


class OsramSwitchMini(CustomDevice):
    """Osram Smart+ Switch Mini device."""

    signature = {
        MODELS_INFO: [(OSRAM, "Lightify Switch Mini")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=2064
            # device_version=1
            # input_clusters=[0, 1, 20, 4096, 64758]
            # output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=1
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id, LightLink.cluster_id, OSRAM_CLUSTER],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=1
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id, LightLink.cluster_id, OSRAM_CLUSTER],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {**signature}
    replacement.pop(MODELS_INFO)

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_MOVE_ON_OFF, ENDPOINT_ID: 1},
        (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP_ON_OFF, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
            ENDPOINT_ID: 3,
        },
        (LONG_PRESS, BUTTON_2): {COMMAND: "move_to_saturation", ENDPOINT_ID: 3},
        (LONG_RELEASE, BUTTON_2): {COMMAND: "move_hue", ENDPOINT_ID: 3},
        (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 2},
        (LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 2},
        (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
    }

    # Each button sends its commands from its own endpoint: up (button 1) on
    # endpoint 1, the circle (button 2) on endpoint 3 and down (button 3) on
    # endpoint 2. A short press is sent on release, as the buttons can be held.
    button_event_entities = (
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, BUTTON_1),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(LONG_PRESS, BUTTON_1),
                ),
                # The device stops with `stop`, the trigger expects `stop_with_on_off`
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    event_data={
                        COMMAND: COMMAND_STOP,
                        CLUSTER_ID: LevelControl.cluster_id,
                        ENDPOINT_ID: 1,
                    },
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, BUTTON_1),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=1,
            unique_id_suffix="button_1",
            translation_key="numbered_button",
            translation_placeholders={"button_number": "1"},
            fallback_name="Button 1",
        ),
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, BUTTON_2),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(LONG_PRESS, BUTTON_2),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, BUTTON_2),
                ),
            ],
            cluster_id=LevelControl.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=3,
            unique_id_suffix="button_2",
            translation_key="numbered_button",
            translation_placeholders={"button_number": "2"},
            fallback_name="Button 2",
        ),
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, BUTTON_3),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(LONG_PRESS, BUTTON_3),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, BUTTON_3),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=2,
            unique_id_suffix="button_3",
            translation_key="numbered_button",
            translation_placeholders={"button_number": "3"},
            fallback_name="Button 3",
        ),
    )
