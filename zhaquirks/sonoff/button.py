"""Device handler for Sonoff buttons."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_TOGGLE,
    DOUBLE_PRESS,
    LONG_PRESS,
    SHORT_PRESS,
)

(
    QuirkBuilder("eWeLink", "WB01")
    .also_applies_to("eWeLink", "SNZB-01P")
    .also_applies_to("eWeLink", "CK-TLSR8656-SS5-01(7000)")
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE},
            (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_ON},
            (LONG_PRESS, BUTTON): {COMMAND: COMMAND_OFF},
        }
    )
    # The button counts its presses, so its single press is a resolved gesture. The
    # long press is one event with no release, classified as sent on release.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, BUTTON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, BUTTON),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_PRESS, BUTTON),
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
