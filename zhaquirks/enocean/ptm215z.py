"""EnOcean PTM 215Z self-powered double rocker switch, used in Friends of Hue switches."""

from typing import Any

from zha.application.platforms.event import BaseEvent
from zha.zigbee.device import GreenPowerDevice
from zigpy.device import GreenPowerCommandReceived
from zigpy.zgp.types import DeviceID, GPDCommandID

from zhaquirks.builder import ButtonEventType, EventDeviceClass, GreenPowerQuirkBuilder
from zhaquirks.enocean import CONTACT_A0, CONTACT_A1, CONTACT_B0, CONTACT_B1

# The contacts each command reports, and whether they were pressed or released. Only
# both top or both bottom contacts can be pressed together. The energy bar is not
# exposed.
COMMANDS: dict[GPDCommandID, tuple[int, bool]] = {
    GPDCommandID.RecallScene0: (CONTACT_A0, True),
    GPDCommandID.RecallScene4: (CONTACT_A0, False),
    GPDCommandID.RecallScene1: (CONTACT_A1, True),
    GPDCommandID.RecallScene5: (CONTACT_A1, False),
    GPDCommandID.RecallScene3: (CONTACT_B0, True),
    GPDCommandID.RecallScene7: (CONTACT_B0, False),
    GPDCommandID.RecallScene2: (CONTACT_B1, True),
    GPDCommandID.RecallScene6: (CONTACT_B1, False),
    GPDCommandID.Press2of2: (CONTACT_A0 | CONTACT_B0, True),
    GPDCommandID.Release2of2: (CONTACT_A0 | CONTACT_B0, False),
    GPDCommandID.Press1of2: (CONTACT_A1 | CONTACT_B1, True),
    GPDCommandID.Release1of2: (CONTACT_A1 | CONTACT_B1, False),
}


class PTM215ZButton(BaseEvent):
    """Event entity for a single contact of the switch."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = [ButtonEventType.PRESS_START, ButtonEventType.PRESS_END]

    def __init__(
        self, device: GreenPowerDevice, *, contact: int, **kwargs: Any
    ) -> None:
        """Initialize the event entity for a single contact."""
        self._contact = contact

        super().__init__(device, **kwargs)

    def on_add(self) -> None:
        """Subscribe to the commands sent by the switch."""
        super().on_add()
        self._on_remove_callbacks.append(
            self.device.device.on_event(
                GreenPowerCommandReceived.event_type, self._handle_command
            )
        )

    def _handle_command(self, event: GreenPowerCommandReceived) -> None:
        """Fire press and release events for this entity's own contact."""
        if event.command_id not in COMMANDS:
            return

        contacts, pressed = COMMANDS[event.command_id]

        if not contacts & self._contact:
            return

        self._trigger_event(
            ButtonEventType.PRESS_START if pressed else ButtonEventType.PRESS_END
        )


(
    GreenPowerQuirkBuilder()
    # The PTM 215ZE is also an on/off switch, but its SrcID block and commands differ
    .applies_to(device_id=DeviceID.OnOffSwitch)
    .src_id_range(0x01700000, 0x017FFFFF)
    .src_id_range(0x01A40000, 0x01A4FFFF)
    .friendly_name(manufacturer="EnOcean", model="PTM 215Z")
    .adds_entity(
        PTM215ZButton,
        contact=CONTACT_A0,
        unique_id_suffix="button_a0",
        translation_key="rocker_top",
        translation_placeholders={"rocker": "A"},
        fallback_name="Rocker A top",
    )
    .adds_entity(
        PTM215ZButton,
        contact=CONTACT_A1,
        unique_id_suffix="button_a1",
        translation_key="rocker_bottom",
        translation_placeholders={"rocker": "A"},
        fallback_name="Rocker A bottom",
    )
    .adds_entity(
        PTM215ZButton,
        contact=CONTACT_B0,
        unique_id_suffix="button_b0",
        translation_key="rocker_top",
        translation_placeholders={"rocker": "B"},
        fallback_name="Rocker B top",
    )
    .adds_entity(
        PTM215ZButton,
        contact=CONTACT_B1,
        unique_id_suffix="button_b1",
        translation_key="rocker_bottom",
        translation_placeholders={"rocker": "B"},
        fallback_name="Rocker B bottom",
    )
    .add_to_registry()
)
