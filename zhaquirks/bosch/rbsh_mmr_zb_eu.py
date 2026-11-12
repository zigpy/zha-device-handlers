"""Device handler for the Bosch Relay (potential free), RBSH-MMR-ZB-EU (BMCT-RZ)."""

from typing import Any, Final

from zigpy import types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    WriteAttributesStatusRecord,
    ZCLAttributeDef,
    ZCLCommandDef,
    ZCLHeader,
)

from zhaquirks.bosch import BOSCH
from zhaquirks.builder import QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    COMMAND,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

BOSCH_MFG_CODE = 0x1209

SWITCH = "switch"
COMMAND_PRESS_RELEASED = "press_released"
COMMAND_HOLD = "hold"
COMMAND_HOLD_RELEASED = "hold_released"
COMMAND_CLOSED = "closed"
COMMAND_OPENED = "opened"
DURATION = "duration"

# Pulse length (tenths of a second) used when switching to pulsed mode for the
# first time, same default as Zigbee2MQTT
DEFAULT_PULSE_LENGTH = 10

# Switch status byte of the manufacturer specific input commands.
STATUS_PRESS_RELEASED = 0
STATUS_HOLD = 1
STATUS_CLOSED = 2
STATUS_OPENED = 3


class BoschSwitchType(t.enum8):
    """Type of the switch wired to the input."""

    Not_connected = 0x00
    Button = 0x05
    Rocker_switch = 0x07


class BoschDeviceMode(t.enum8):
    """Relay mode, derived from the pulse length (0 is switch, above 0 is pulsed)."""

    Switch = 0x00
    Pulsed = 0x01


class BoschActuatorType(t.enum8):
    """Type of the actuator connected to the relay output."""

    Normally_closed = 0x00
    Normally_open = 0x01


class BoschRelayControl(CustomCluster):
    """Manufacturer specific cluster of the Bosch relay (BMCT-RZ)."""

    cluster_id: Final[t.uint16_t] = 0xFCA0

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        switch_type = ZCLAttributeDef(
            id=0x0001,
            type=BoschSwitchType,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        auto_off_enabled = ZCLAttributeDef(
            id=0x0006,
            type=t.Bool,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        # Seconds
        auto_off_time = ZCLAttributeDef(
            id=0x0007,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        child_lock = ZCLAttributeDef(
            id=0x0008,
            type=t.Bool,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        # Tenths of a second, 0 means the relay follows the switch state
        pulse_length = ZCLAttributeDef(
            id=0x0024,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        # 0 is coupled, 1 is decoupled (a uint8 on the wire, not a bool)
        decoupled_mode = ZCLAttributeDef(
            id=0x0031,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        actuator_type = ZCLAttributeDef(
            id=0x0034,
            type=BoschActuatorType,
            access="rwp",
            manufacturer_code=BOSCH_MFG_CODE,
        )

        # Not a device attribute: derived from and written through pulse_length
        device_mode = ZCLAttributeDef(
            id=0xF000,
            type=BoschDeviceMode,
            access="rwp",
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Commands sent by the relay when the wired switch changes."""

        switch_event = ZCLCommandDef(
            id=0x03,
            schema={"status": t.uint8_t, "duration": t.uint8_t},
            manufacturer_code=BOSCH_MFG_CODE,
        )

        # Second input of the dual input models (BMCT-DZ), handled like the first
        switch_event_right = ZCLCommandDef(
            id=0x04,
            schema={"status": t.uint8_t, "duration": t.uint8_t},
            manufacturer_code=BOSCH_MFG_CODE,
        )

    _last_pulse_length: int = DEFAULT_PULSE_LENGTH

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Keep the device mode in sync with reported and read pulse lengths."""
        super()._update_attribute(attrid, value)

        if attrid == self.AttributeDefs.pulse_length.id:
            self._sync_device_mode(value)

    def _sync_device_mode(self, pulse_length: int | None) -> None:
        """Derive the device mode from the pulse length."""
        if pulse_length is None:
            return

        if pulse_length:
            self._last_pulse_length = pulse_length

        self.update_attribute(
            self.AttributeDefs.device_mode.id,
            BoschDeviceMode.Pulsed if pulse_length else BoschDeviceMode.Switch,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs: Any,
    ) -> list[list[WriteAttributesStatusRecord]]:
        """Write the device mode as a pulse length.

        Pulsed restores the last pulse length, switch writes 0. An explicit
        pulse length in the same call takes precedence over the mode. Writes
        update the zigpy cache directly, so the mode is synced after the write.
        """
        remaining = {}
        mode = None
        has_pulse_length = False

        for key, value in attributes.items():
            try:
                attr_id = self.find_attribute(key).id
            except KeyError:
                attr_id = None

            if attr_id == self.AttributeDefs.device_mode.id:
                mode = BoschDeviceMode(value)
                continue

            has_pulse_length |= attr_id == self.AttributeDefs.pulse_length.id
            remaining[key] = value

        if mode is None:
            remaining = attributes
        elif not has_pulse_length:
            remaining[self.AttributeDefs.pulse_length.name] = (
                self._last_pulse_length if mode == BoschDeviceMode.Pulsed else 0
            )

        result = await super().write_attributes(remaining, **kwargs)
        self._sync_device_mode(self.get(self.AttributeDefs.pulse_length.name))
        return result

    def handle_cluster_request(
        self,
        hdr: ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Turn the raw switch status into named events."""
        if hdr.command_id not in (
            self.ClientCommandDefs.switch_event.id,
            self.ClientCommandDefs.switch_event_right.id,
        ):
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
            return

        status, duration = args
        # The duration is reported in tenths of a second
        seconds = duration / 10

        if status == STATUS_PRESS_RELEASED:
            action = COMMAND_PRESS_RELEASED
        elif status == STATUS_HOLD:
            action = COMMAND_HOLD if duration else COMMAND_HOLD_RELEASED
        elif status == STATUS_CLOSED:
            action = COMMAND_CLOSED
        elif status == STATUS_OPENED:
            action = COMMAND_OPENED
        else:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
            return

        self.listener_event(ZHA_SEND_EVENT, action, {DURATION: seconds})


(
    QuirkBuilder(BOSCH, "RBSH-MMR-ZB-EU")
    .friendly_name(manufacturer=BOSCH, model="BMCT-RZ")
    .replaces(BoschRelayControl)
    .enum(
        BoschRelayControl.AttributeDefs.switch_type.name,
        BoschSwitchType,
        BoschRelayControl.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .switch(
        BoschRelayControl.AttributeDefs.decoupled_mode.name,
        BoschRelayControl.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="decoupled_mode",
        fallback_name="Decoupled mode",
    )
    .enum(
        BoschRelayControl.AttributeDefs.actuator_type.name,
        BoschActuatorType,
        BoschRelayControl.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="actuator_type",
        fallback_name="Actuator type",
    )
    .switch(
        BoschRelayControl.AttributeDefs.child_lock.name,
        BoschRelayControl.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .enum(
        BoschRelayControl.AttributeDefs.device_mode.name,
        BoschDeviceMode,
        BoschRelayControl.cluster_id,
        translation_key="device_mode",
        fallback_name="Device mode",
    )
    .number(
        BoschRelayControl.AttributeDefs.pulse_length.name,
        BoschRelayControl.cluster_id,
        # Only used in pulsed mode, it reads 0 in switch mode (setting a pulse
        # length in switch mode turns the pulsed mode on)
        min_value=0.5,
        max_value=20,
        # ZHA writes int(value / multiplier), which loses a tenth for about a
        # third of the 0.1 s steps (0.6 / 0.1 is 5.999...), so use half seconds
        step=0.5,
        unit=UnitOfTime.SECONDS,
        mode="slider",
        multiplier=0.1,
        attribute_initialized_from_cache=False,
        translation_key="pulse_length",
        fallback_name="Pulse length",
    )
    .switch(
        BoschRelayControl.AttributeDefs.auto_off_enabled.name,
        BoschRelayControl.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="auto_off",
        fallback_name="Auto-off",
    )
    .number(
        BoschRelayControl.AttributeDefs.auto_off_time.name,
        BoschRelayControl.cluster_id,
        min_value=0,
        max_value=43200,
        step=1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        attribute_initialized_from_cache=False,
        translation_key="auto_off_time",
        fallback_name="Auto-off time",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, SWITCH): {
                COMMAND: COMMAND_PRESS_RELEASED,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, SWITCH): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 1},
            (LONG_RELEASE, SWITCH): {COMMAND: COMMAND_HOLD_RELEASED, ENDPOINT_ID: 1},
            (COMMAND_CLOSED, SWITCH): {COMMAND: COMMAND_CLOSED, ENDPOINT_ID: 1},
            (COMMAND_OPENED, SWITCH): {COMMAND: COMMAND_OPENED, ENDPOINT_ID: 1},
        }
    )
    .add_to_registry()
)
