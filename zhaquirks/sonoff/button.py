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

EWELINK_BUTTON_TRIGGERS = {
    (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE},
    (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_ON},
    (LONG_PRESS, BUTTON): {COMMAND: COMMAND_OFF},
}


def _ewelink_button_events(*, hold: bool) -> list[ButtonEvent]:
    """Return the button events of an eWeLink/SONOFF wireless button.

    The button counts its presses, so its single press is a resolved gesture. The
    long press is one event with no release; on the SNZB-01P it is sent when the hold
    reaches its threshold, so it starts the hold.
    """
    events = [
        ButtonEvent(
            event_type=ButtonEventType.SINGLE_PRESS,
            trigger=(SHORT_PRESS, BUTTON),
        ),
        ButtonEvent(
            event_type=ButtonEventType.MULTI_PRESS,
            trigger=(DOUBLE_PRESS, BUTTON),
            press_count=2,
        ),
    ]
    if hold:
        events.append(
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, BUTTON),
            )
        )
    return events


(
    QuirkBuilder("eWeLink", "SNZB-01P")
    .device_automation_triggers(EWELINK_BUTTON_TRIGGERS)
    .button_event(
        events=_ewelink_button_events(hold=True),
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )
    .add_to_registry()
)

(
    QuirkBuilder("eWeLink", "WB01")
    .also_applies_to("eWeLink", "CK-TLSR8656-SS5-01(7000)")
    .device_automation_triggers(EWELINK_BUTTON_TRIGGERS)
    # When these send the long press is not confirmed on hardware, so the hold is
    # left out of the button event entity for now
    .button_event(
        events=_ewelink_button_events(hold=False),
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )
    .add_to_registry()
)
