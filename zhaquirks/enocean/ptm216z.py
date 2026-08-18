"""EnOcean PTM 216Z self-powered double rocker switch."""

from zigpy.device import GreenPowerCommandReceived
from zigpy.zgp.types import GPDCommandID

from zhaquirks.builder import (
    EventDeviceClass,
    GreenPowerEventTrigger,
    GreenPowerQuirkBuilder,
)
from zhaquirks.builder.green_power import GreenPowerEventEntity

# The switch has two rockers, each with two contacts, reported as a bit in the 8-bit
# vector of the GPD press command. Bits 4-7 are unused.
CONTACT_A0 = 0b0001
CONTACT_A1 = 0b0010
CONTACT_B0 = 0b0100
CONTACT_B1 = 0b1000


class PTM216ZButtonEvent(GreenPowerEventEntity):
    """Event entity for a single contact of the switch."""

    _contact: int
    _pressed: bool = False

    def _handle_gp_command_received(self, event: GreenPowerCommandReceived) -> None:
        """Fire the entity's events for presses and releases of its own contact."""
        if event.command is None:
            return

        if event.command_id == GPDCommandID.Press8BitVector:
            if not event.command.contact_status & self._contact:
                return

            self._pressed = True
        elif event.command_id == GPDCommandID.Release8BitVector:
            if not self._pressed:
                return

            self._pressed = False
        else:
            return

        super()._handle_gp_command_received(event)


class RockerATopEvent(PTM216ZButtonEvent):
    """Top contact of rocker A."""

    _contact = CONTACT_A0


class RockerABottomEvent(PTM216ZButtonEvent):
    """Bottom contact of rocker A."""

    _contact = CONTACT_A1


class RockerBTopEvent(PTM216ZButtonEvent):
    """Top contact of rocker B."""

    _contact = CONTACT_B0


class RockerBBottomEvent(PTM216ZButtonEvent):
    """Bottom contact of rocker B."""

    _contact = CONTACT_B1


(
    GreenPowerQuirkBuilder()
    .src_id_range(0x01550000, 0x0155FFFF)
    .friendly_name(manufacturer="EnOcean", model="PTM 216Z")
    .event(
        event_types={
            "press": GreenPowerEventTrigger(GPDCommandID.Press8BitVector),
            "release": GreenPowerEventTrigger(GPDCommandID.Release8BitVector),
        },
        entity_class=RockerATopEvent,
        device_class=EventDeviceClass.BUTTON,
        unique_id_suffix="button_a0",
        fallback_name="Rocker A top",
        primary=True,
    )
    .event(
        event_types={
            "press": GreenPowerEventTrigger(GPDCommandID.Press8BitVector),
            "release": GreenPowerEventTrigger(GPDCommandID.Release8BitVector),
        },
        entity_class=RockerABottomEvent,
        device_class=EventDeviceClass.BUTTON,
        unique_id_suffix="button_a1",
        fallback_name="Rocker A bottom",
    )
    .event(
        event_types={
            "press": GreenPowerEventTrigger(GPDCommandID.Press8BitVector),
            "release": GreenPowerEventTrigger(GPDCommandID.Release8BitVector),
        },
        entity_class=RockerBTopEvent,
        device_class=EventDeviceClass.BUTTON,
        unique_id_suffix="button_b0",
        fallback_name="Rocker B top",
    )
    .event(
        event_types={
            "press": GreenPowerEventTrigger(GPDCommandID.Press8BitVector),
            "release": GreenPowerEventTrigger(GPDCommandID.Release8BitVector),
        },
        entity_class=RockerBBottomEvent,
        device_class=EventDeviceClass.BUTTON,
        unique_id_suffix="button_b1",
        fallback_name="Rocker B bottom",
    )
    .add_to_registry()
)
