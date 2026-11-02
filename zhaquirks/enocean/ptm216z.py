"""EnOcean PTM 216Z self-powered double rocker switch."""

from typing import Any

from zha.application.platforms.event import BaseEvent
from zha.zigbee.device import GreenPowerDevice
from zigpy.device import GreenPowerCommandReceived
from zigpy.zgp.types import DeviceID, GPDCommandID

from zhaquirks.builder import ButtonEventType, EventDeviceClass, GreenPowerQuirkBuilder

# The switch has two rockers, each with two contacts, reported as a bit in the 8-bit
# vector of the GPD press command. Bit 4 is the energy bar, which is not exposed. Bits
# 5-7 are unused.
CONTACT_A0 = 0b0001
CONTACT_A1 = 0b0010
CONTACT_B0 = 0b0100
CONTACT_B1 = 0b1000


class PTM216ZButton(BaseEvent):
    """Event entity for a single contact of the switch."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = [ButtonEventType.PRESS_START, ButtonEventType.PRESS_END]

    def __init__(
        self, device: GreenPowerDevice, *, contact: int, **kwargs: Any
    ) -> None:
        """Initialize the event entity for a single contact."""
        self._contact = contact
        self._pressed = False

        super().__init__(device, **kwargs)

    def on_add(self) -> None:
        """Subscribe to the commands sent by the switch."""
        super().on_add()
        self._on_remove_callbacks.append(
            self.device.device.on_event(
                GreenPowerCommandReceived.event_type, self._handle_contact_status
            )
        )

    def _handle_contact_status(self, event: GreenPowerCommandReceived) -> None:
        """Fire press and release events for this entity's own contact."""
        # zigpy reports a command it could not parse without its payload
        if event.command is None:
            return

        if event.command_id not in (
            GPDCommandID.Press8BitVector,
            GPDCommandID.Release8BitVector,
        ):
            return

        # Both commands carry the resulting state of every contact
        pressed = bool(event.command.contact_status & self._contact)

        if pressed == self._pressed:
            return

        self._pressed = pressed
        self._trigger_event(
            ButtonEventType.PRESS_START if pressed else ButtonEventType.PRESS_END,
            event.command.as_dict(),
        )


(
    GreenPowerQuirkBuilder()
    # The PTM 215ZE shares the SrcID block but is an on/off switch
    .applies_to(device_id=DeviceID.GenericSwitch)
    .src_id_range(0x01500000, 0x015FFFFF)
    .friendly_name(manufacturer="EnOcean", model="PTM 216Z")
    .adds_entity(
        PTM216ZButton,
        contact=CONTACT_A0,
        unique_id_suffix="button_a0",
        translation_key="rocker_top",
        translation_placeholders={"rocker": "A"},
        fallback_name="Rocker A top",
    )
    .adds_entity(
        PTM216ZButton,
        contact=CONTACT_A1,
        unique_id_suffix="button_a1",
        translation_key="rocker_bottom",
        translation_placeholders={"rocker": "A"},
        fallback_name="Rocker A bottom",
    )
    .adds_entity(
        PTM216ZButton,
        contact=CONTACT_B0,
        unique_id_suffix="button_b0",
        translation_key="rocker_top",
        translation_placeholders={"rocker": "B"},
        fallback_name="Rocker B top",
    )
    .adds_entity(
        PTM216ZButton,
        contact=CONTACT_B1,
        unique_id_suffix="button_b1",
        translation_key="rocker_bottom",
        translation_placeholders={"rocker": "B"},
        fallback_name="Rocker B bottom",
    )
    .add_to_registry()
)
