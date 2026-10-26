"""ZunZunBee button device."""

from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent, ClusterType
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON,
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
    LONG_PRESS,
    PRESS_TYPE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.zunzunbee import ZUNZUNBEE

PRESS_TYPES = {
    1: SHORT_PRESS,
    2: LONG_PRESS,
}

BUTTON_MAPPING = {
    2: BUTTON_1,
    4: BUTTON_2,
    8: BUTTON_3,
    16: BUTTON_4,
    32: BUTTON_5,
    64: BUTTON_6,
    128: BUTTON_7,
    256: BUTTON_8,
}


class ZunZunBeeIASCluster(CustomCluster, IasZone):
    """IAS cluster used for ZunZunBee button."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReportedEvent.event_type, self._handle_attribute_event)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_attribute_event)

    def _handle_attribute_event(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ) -> None:
        """Handle attribute report/update event to emit button press events."""
        if event.attribute_id != self.AttributeDefs.zone_status.id:
            return

        value = event.value
        # Ignore first bit for determining button id
        button_id = value & 0x01FE

        # Map to button presses, ignore invalid buttons
        button = BUTTON_MAPPING.get(button_id)
        if button is None:
            return

        # Only check first bit for press type
        press_id = (value & 1) + 1
        press_type = PRESS_TYPES[press_id]

        action = f"{button}_{press_type}"
        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
        }
        self.listener_event(ZHA_SEND_EVENT, action, event_args)


BUTTONS = (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
)


slate_switch_quirk = (
    QuirkBuilder(ZUNZUNBEE, "SSWZ8T")
    .replaces(ZunZunBeeIASCluster)
    .device_automation_triggers(
        {
            (press_type, button): {
                COMMAND: f"{button}_{press_type}",
                CLUSTER_ID: IasZone.cluster_id,
            }
            for press_type in (SHORT_PRESS, LONG_PRESS)
            for button in BUTTONS
        }
    )
)

# The switch reports each press once, as short or long. A short press can only be
# told apart from a long one on release. The long press is taken as reported at the
# hold threshold, as the switch sends no release.
for number, button in enumerate(BUTTONS, start=1):
    slate_switch_quirk.button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, button),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, button),
            ),
        ],
        cluster_id=IasZone.cluster_id,
        cluster_type=ClusterType.Server,
        unique_id_suffix=button,
        translation_key="numbered_button",
        translation_placeholders={"button_number": str(number)},
        fallback_name=f"Button {number}",
    )

slate_switch_quirk.add_to_registry()
