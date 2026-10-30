"""Philips Hue Tap self-powered four button switch."""

from typing import Any

from zha.application.platforms.event import BaseEvent
from zha.zigbee.device import GreenPowerDevice
from zigpy.device import GreenPowerCommandReceived
from zigpy.zgp.types import DeviceID, GPDCommandID

from zhaquirks.builder import ButtonEventType, EventDeviceClass, GreenPowerQuirkBuilder


class HueTapButton(BaseEvent):
    """Event entity for a single button of the switch."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = [ButtonEventType.PRESS_START]

    def __init__(
        self, device: GreenPowerDevice, *, command_id: GPDCommandID, **kwargs: Any
    ) -> None:
        """Initialize the event entity for a single button."""
        self._command_id = command_id

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
        """Fire a press event for this entity's own button."""
        if event.command_id != self._command_id:
            return

        # The switch sends one command when the button goes down and none on release
        self._trigger_event(ButtonEventType.PRESS_START)


(
    GreenPowerQuirkBuilder()
    .applies_to(device_id=DeviceID.OnOffSwitch)
    .src_id_range(0x00400000, 0x004FFFFF)
    .friendly_name(manufacturer="Philips", model="Hue Tap")
    .adds_entity(
        HueTapButton,
        command_id=GPDCommandID.Toggle,
        unique_id_suffix="button_1",
        translation_key="button_numbered",
        translation_placeholders={"number": "1"},
        fallback_name="Button 1",
    )
    .adds_entity(
        HueTapButton,
        command_id=GPDCommandID.RecallScene0,
        unique_id_suffix="button_2",
        translation_key="button_numbered",
        translation_placeholders={"number": "2"},
        fallback_name="Button 2",
    )
    .adds_entity(
        HueTapButton,
        command_id=GPDCommandID.RecallScene1,
        unique_id_suffix="button_3",
        translation_key="button_numbered",
        translation_placeholders={"number": "3"},
        fallback_name="Button 3",
    )
    .adds_entity(
        HueTapButton,
        command_id=GPDCommandID.RecallScene2,
        unique_id_suffix="button_4",
        translation_key="button_numbered",
        translation_placeholders={"number": "4"},
        fallback_name="Button 4",
    )
    .add_to_registry()
)
