"""Linxura button device."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    PRESS_TYPE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.linxura import LINXURA

PRESS_TYPES = {
    1: SHORT_PRESS,
    2: DOUBLE_PRESS,
    3: LONG_PRESS,
}


class LinxuraIASCluster(CustomCluster, IasZone):
    """IAS cluster used for Linxura button."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReportedEvent.event_type, self._handle_attribute_event)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_attribute_event)

    def _handle_attribute_event(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ) -> None:
        """Handle attribute report/update event."""
        if event.attribute_id == self.AttributeDefs.zone_status.id:
            value = event.value
            if 0 < value < 24:
                if 0 < value < 6:
                    button = BUTTON_1
                    press_type = PRESS_TYPES[value // 2 + 1]
                elif 6 < value < 12:
                    button = BUTTON_2
                    press_type = PRESS_TYPES[value // 2 - 3 + 1]
                elif 12 < value < 18:
                    button = BUTTON_3
                    press_type = PRESS_TYPES[value // 2 - 6 + 1]
                elif 18 < value < 24:
                    button = BUTTON_4
                    press_type = PRESS_TYPES[value // 2 - 9 + 1]
                else:
                    # discard invalid values: 0, 6, 12, 18
                    return

                action = f"{button}_{press_type}"
                event_args = {
                    BUTTON: button,
                    PRESS_TYPE: press_type,
                }
                self.listener_event(ZHA_SEND_EVENT, action, event_args)


(
    QuirkBuilder(LINXURA, "Smart Controller")
    .replaces(LinxuraIASCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (press_type, button): {
                COMMAND: f"{button}_{press_type}",
                CLUSTER_ID: IasZone.cluster_id,
            }
            for press_type in (SHORT_PRESS, DOUBLE_PRESS, LONG_PRESS)
            for button in (BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4)
        }
    )
    .add_to_registry()
)
