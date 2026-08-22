"""EnOcean PTM 216Z self-powered double rocker switch."""

from typing import Any

from zha.application.platforms.event import BaseEvent
from zha.zigbee.device import GreenPowerDevice
from zigpy.device import GreenPowerCommandReceived
from zigpy.zgp.types import GPDCommandID

from zhaquirks.builder import ButtonEventType, EventDeviceClass, GreenPowerQuirkBuilder

# The switch has two rockers, each with two contacts, reported as a bit in the 8-bit
# vector of the GPD press command. Bits 4-7 are unused.
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

        if event.command_id == GPDCommandID.Press8BitVector:
            pressed = bool(event.command.contact_status & self._contact)
        elif event.command_id == GPDCommandID.Release8BitVector:
            # The switch only reports that every contact is open again
            pressed = False
        else:
            return

        if pressed == self._pressed:
            return

        self._pressed = pressed
        self._trigger_event(
            ButtonEventType.PRESS_START if pressed else ButtonEventType.PRESS_END,
            event.command.as_dict(),
        )


(
    GreenPowerQuirkBuilder()
    .src_id_range(0x01550000, 0x0155FFFF)
    .friendly_name(manufacturer="EnOcean", model="PTM 216Z")
    .entity(
        PTM216ZButton,
        contact=CONTACT_A0,
        unique_id_suffix="button_a0",
        fallback_name="Rocker A top",
        primary=True,
    )
    .entity(
        PTM216ZButton,
        contact=CONTACT_A1,
        unique_id_suffix="button_a1",
        fallback_name="Rocker A bottom",
    )
    .entity(
        PTM216ZButton,
        contact=CONTACT_B0,
        unique_id_suffix="button_b0",
        fallback_name="Rocker B top",
    )
    .entity(
        PTM216ZButton,
        contact=CONTACT_B1,
        unique_id_suffix="button_b1",
        fallback_name="Rocker B bottom",
    )
    .add_to_registry()
)
