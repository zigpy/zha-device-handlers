"""Modules for Yokis remote."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    CLUSTER_ID,
    COMMAND,
    COMMAND_TOGGLE,
    ENDPOINT_ID,
    SHORT_PRESS,
)

(
    QuirkBuilder("YOKIS", "TLC1-UP")
    .applies_to("YOKIS", "TLM1-UP")
    .applies_to("YOKIS", "TLM1T503-UP")
    .applies_to("YOKIS", "TLM1TNO-UP")
    .applies_to("YOKIS", "TLM1TDK-UP")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
        }
    )
    # The button reports a press as a toggle command. When in the press it is sent
    # is not known, so it is mapped as a single press.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, BUTTON_1),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )
    .add_to_registry()
)

two_button_quirk = (
    QuirkBuilder("YOKIS", "TLC2-UP")
    .applies_to("YOKIS", "TLM2-UP")
    .applies_to("YOKIS", "TLM2T503-UP")
    .applies_to("YOKIS", "E2BP-UP")
    .applies_to("YOKIS", "MONITOR2-UP")
    .applies_to("YOKIS", "TLM2TNO-UP")
    .applies_to("YOKIS", "E2BPA-UP")
    .applies_to("YOKIS", "A2BP-UP")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 2,
            },
        }
    )
)

four_button_quirk = (
    QuirkBuilder("YOKIS", "TLC4-UP")
    .applies_to("YOKIS", "TLM4-UP")
    .applies_to("YOKIS", "TLM4T503-UP")
    .applies_to("YOKIS", "E4BP-UP")
    .applies_to("YOKIS", "E4BPX-UP")
    .applies_to("YOKIS", "GALET4-UP")
    .applies_to("YOKIS", "TLM4TNO-UP")
    .applies_to("YOKIS", "TLM4TDK-UP")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 2,
            },
            (SHORT_PRESS, BUTTON_3): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 3,
            },
            (SHORT_PRESS, BUTTON_4): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 4,
            },
        }
    )
)

eight_button_quirk = (
    QuirkBuilder("YOKIS", "TLC8-UP")
    .applies_to("YOKIS", "MONITOR-UP")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 2,
            },
            (SHORT_PRESS, BUTTON_3): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 3,
            },
            (SHORT_PRESS, BUTTON_4): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 4,
            },
            (SHORT_PRESS, BUTTON_5): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 5,
            },
            (SHORT_PRESS, BUTTON_6): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 6,
            },
            (SHORT_PRESS, BUTTON_7): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 7,
            },
            (SHORT_PRESS, BUTTON_8): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 8,
            },
        }
    )
)

# Each button reports a press as a toggle command of its endpoint. When in the press
# it is sent is not known, so it is mapped as a single press.
for quirk, buttons in (
    (two_button_quirk, 2),
    (four_button_quirk, 4),
    (eight_button_quirk, 8),
):
    for number in range(1, buttons + 1):
        quirk.button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.SINGLE_PRESS,
                    trigger=(SHORT_PRESS, f"button_{number}"),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=number,
            unique_id_suffix=f"button_{number}",
            translation_key="numbered_button",
            translation_placeholders={"button_number": str(number)},
            fallback_name=f"Button {number}",
        )

    quirk.add_to_registry()
