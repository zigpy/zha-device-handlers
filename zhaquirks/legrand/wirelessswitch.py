"""Module for Legrand wireless switches (Radiant, NLD, NLT, NLW)."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.legrand import LEGRAND, LegrandPowerConfigurationCluster

(
    QuirkBuilder(f" {LEGRAND}", " Remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
            (LONG_PRESS, TURN_ON): {
                COMMAND: COMMAND_MOVE,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
            (LONG_PRESS, TURN_OFF): {
                COMMAND: COMMAND_MOVE,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON): {COMMAND: COMMAND_STOP},
        }
    )
    # Each half of the rocker is a button. The Z2M debug log in
    # Koenkk/zigbee2mqtt#32608 shows no on/off before a hold's move, so on/off is
    # sent once a press is known to be short, at release. A hold sends move and the
    # release after it a stop shared by both halves. The move is matched by its mode
    # only, as that device sends a different rate than the triggers expect.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, TURN_ON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={COMMAND: COMMAND_MOVE, PARAMS: {"move_mode": 0}},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_on",
        translation_key="on_button",
        fallback_name="On button",
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, TURN_OFF),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={COMMAND: COMMAND_MOVE, PARAMS: {"move_mode": 1}},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_off",
        translation_key="off_button",
        fallback_name="Off button",
    )
    .add_to_registry()
)

(
    QuirkBuilder(f" {LEGRAND}", " NLWO - Triple remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (TURN_ON, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
            (DIM_UP, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_1): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 1},
            (TURN_ON, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 2},
            (DIM_UP, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_2): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
            (TURN_ON, BUTTON_3): {COMMAND: COMMAND_ON, ENDPOINT_ID: 3},
            (DIM_UP, BUTTON_3): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 3,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_3): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_3): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 3,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 3},
        }
    )
    # Each half of each rocker is a button, see the single remote switch above. The
    # off triggers do not match the endpoint, so the off presses are matched here.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(TURN_ON, BUTTON_1),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 0},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_1),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=1,
        unique_id_suffix="button_1_on",
        translation_key="numbered_on_button",
        fallback_name="On button 1",
        translation_placeholders={"button_number": "1"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 1},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_1),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=1,
        unique_id_suffix="button_1_off",
        translation_key="numbered_off_button",
        fallback_name="Off button 1",
        translation_placeholders={"button_number": "1"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(TURN_ON, BUTTON_2),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 2,
                    PARAMS: {"move_mode": 0},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_2),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=2,
        unique_id_suffix="button_2_on",
        translation_key="numbered_on_button",
        fallback_name="On button 2",
        translation_placeholders={"button_number": "2"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_OFF, ENDPOINT_ID: 2},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 2,
                    PARAMS: {"move_mode": 1},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_2),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=2,
        unique_id_suffix="button_2_off",
        translation_key="numbered_off_button",
        fallback_name="Off button 2",
        translation_placeholders={"button_number": "2"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(TURN_ON, BUTTON_3),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 3,
                    PARAMS: {"move_mode": 0},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_3),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=3,
        unique_id_suffix="button_3_on",
        translation_key="numbered_on_button",
        fallback_name="On button 3",
        translation_placeholders={"button_number": "3"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_OFF, ENDPOINT_ID: 3},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 3,
                    PARAMS: {"move_mode": 1},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_3),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=3,
        unique_id_suffix="button_3_off",
        translation_key="numbered_off_button",
        fallback_name="Off button 3",
        translation_placeholders={"button_number": "3"},
    )
    .add_to_registry()
)

(
    QuirkBuilder(f" {LEGRAND}", " Double gangs remote switch")
    .replaces(LegrandPowerConfigurationCluster)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .device_automation_triggers(
        {
            (TURN_ON, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
            (DIM_UP, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_1): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_1): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 1},
            (TURN_ON, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 2},
            (DIM_UP, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 0, "rate": 255},
            },
            (TURN_OFF, BUTTON_2): {COMMAND: COMMAND_OFF},
            (DIM_DOWN, BUTTON_2): {
                COMMAND: COMMAND_MOVE,
                ENDPOINT_ID: 2,
                PARAMS: {"move_mode": 1, "rate": 255},
            },
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
        }
    )
    # Each half of each rocker is a button, see the single remote switch. The
    # off triggers do not match the endpoint, so the off presses are matched here.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(TURN_ON, BUTTON_1),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 0},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_1),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=1,
        unique_id_suffix="button_1_on",
        translation_key="numbered_on_button",
        fallback_name="On button 1",
        translation_placeholders={"button_number": "1"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 1},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_1),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=1,
        unique_id_suffix="button_1_off",
        translation_key="numbered_off_button",
        fallback_name="Off button 1",
        translation_placeholders={"button_number": "1"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(TURN_ON, BUTTON_2),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 2,
                    PARAMS: {"move_mode": 0},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_2),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=2,
        unique_id_suffix="button_2_on",
        translation_key="numbered_on_button",
        fallback_name="On button 2",
        translation_placeholders={"button_number": "2"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_OFF, ENDPOINT_ID: 2},
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    ENDPOINT_ID: 2,
                    PARAMS: {"move_mode": 1},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, BUTTON_2),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=2,
        unique_id_suffix="button_2_off",
        translation_key="numbered_off_button",
        fallback_name="Off button 2",
        translation_placeholders={"button_number": "2"},
    )
    .add_to_registry()
)
