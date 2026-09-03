"""Sonoff ZBMINIR2 and MINI-ZBD - Zigbee Switches."""

from zigpy import types
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    DataTypeId,
    ZCLAttributeDef,
    Status,
    WriteAttributesStatusRecord,
    ZCLHeader,
    FrameControl,
    FrameType,
    Direction,
)
from zigpy.zcl.clusters.general import OnOff
import logging

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    ENDPOINT_ID,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)

# Attribute Define
RELAY_DETACH_ATTR_ID = 0x0028

# Inching related constants
INCHING_ENABLE_ATTR = 0xFF00
INCHING_MODE_ATTR = 0xFF01
INCHING_TIMEOUT_ATTR = 0xFF02
INCHING_CMD = 0x01
INCHING_SUBCMD = 0x17
INCHING_LENGTH = 7
INCHING_CHANNEL = 0x00

# Manufacturer code for SONOFF
SONOFF_MANUFACTURER_CODE = 0x1286


class SonoffExternalSwitchTriggerType(types.enum8):
    """External switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


class RelaySperaKeyAction(types.enum8):
    Unknown = 0x00
    Single_click = 0x01
    Double_click = 0x02
    Long_press = 0x03
    # Follow_on = 0x04
    # Follow_off = 0x05


class InchingModeBit(types.enum8):
    """Inching mode bit."""

    Auto_off = 0x00
    Auto_on = 0x01


class OnOff(OnOff):
    """Map a `toggle` command received by the gateway into a single-click event."""

    def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
        if hdr.command_id == OnOff.ServerCommandDefs.toggle.id:
            sonoff_cluster = self.endpoint.in_clusters.get(SonoffCluster.cluster_id)
            if sonoff_cluster is not None:
                # Equivalent to one `0x0028 = Single_click` attribute update from the
                # device: update_attribute -> SonoffCluster._update_attribute
                #   -> listener_event(ZHA_SEND_EVENT, "Single_click", {})
                sonoff_cluster.update_attribute(
                    RELAY_DETACH_ATTR_ID, RelaySperaKeyAction.Single_click.value
                )
        return super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=SonoffExternalSwitchTriggerType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        detach_relay = ZCLAttributeDef(
            id=0x0017,
            type=t.Bool,
            manufacturer_code=None,
        )
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            manufacturer_code=None,
        )
        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            manufacturer_code=None,
        )
        relay_spera_key_action_event = ZCLAttributeDef(
            id=RELAY_DETACH_ATTR_ID,
            type=RelaySperaKeyAction,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        # Inching attributes
        inching_enable = ZCLAttributeDef(
            id=INCHING_ENABLE_ATTR,
            type=t.Bool,
            manufacturer_code=None,
        )
        inching_mode = ZCLAttributeDef(
            id=INCHING_MODE_ATTR,
            type=InchingModeBit,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        inching_timeout = ZCLAttributeDef(
            id=INCHING_TIMEOUT_ATTR,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Power-on behavior delay attributes (renamed)
        power_on_behavior_delay_enable = ZCLAttributeDef(
            id=0x0014,
            type=t.Bool,
            manufacturer_code=None,
        )
        power_on_behavior_delay_time = ZCLAttributeDef(
            id=0x0015,
            type=t.uint16_t,
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inching_enable = False
        self._inching_mode_bit = 0   # alwaysClosed
        self._inching_timeout = 2
        self._cmd_seq = 0
        # Seed attribute cache with default values
        self._update_attribute(INCHING_ENABLE_ATTR, self._inching_enable)
        self._update_attribute(INCHING_MODE_ATTR, self._inching_mode_bit)
        self._update_attribute(INCHING_TIMEOUT_ATTR, self._inching_timeout)
        self._update_attribute(RELAY_DETACH_ATTR_ID, RelaySperaKeyAction(0).name)

    def _update_attribute(self, attrid, value):
        if attrid == RELAY_DETACH_ATTR_ID and isinstance(value, int):
            try:
                value = RelaySperaKeyAction(value).name
            except ValueError:
                pass

        super()._update_attribute(attrid, value)

        if attrid == RELAY_DETACH_ATTR_ID:
            try:
                self.listener_event(ZHA_SEND_EVENT, value, {})
            except Exception:
                pass

    async def write_attributes(self, attrs, manufacturer=None, **kwargs):
        """Override to handle inching attributes by name."""
        _LOGGER.debug("write_attributes called with attrs: %s", attrs)
        results = []
        real_attrs = {}

        for key, value in attrs.items():
            if key == "inching_enable":
                self._inching_enable = bool(value)
                await self._send_combined()
                results.append(WriteAttributesStatusRecord(Status.SUCCESS, INCHING_ENABLE_ATTR))
            elif key == "inching_mode":
                self._inching_mode_bit = value
                await self._send_combined()
                results.append(WriteAttributesStatusRecord(Status.SUCCESS, INCHING_MODE_ATTR))
            elif key == "inching_timeout":
                self._inching_timeout = value
                await self._send_combined()
                results.append(WriteAttributesStatusRecord(Status.SUCCESS, INCHING_TIMEOUT_ATTR))
                self._update_attribute(INCHING_TIMEOUT_ATTR, value)
            else:
                real_attrs[key] = value

        if real_attrs:
            parent_results = await super().write_attributes(real_attrs, manufacturer, **kwargs)
            if parent_results and isinstance(parent_results, list) and parent_results[0]:
                if isinstance(parent_results[0], list):
                    results.extend(parent_results[0])
                else:
                    results.extend(parent_results)

        _LOGGER.debug("write_attributes returning: %s", results)
        return [results]

    async def _send_combined(self):
        """Send combined inching configuration."""
        # Mode byte: bit7 = enable (1=on, 0=off), bit0 = mode (1=Normally Closed, 0=Normally Open)
        mode = (0x80 if self._inching_enable else 0x00) | (self._inching_mode_bit & 0x01)
        await self.set_inching(mode, INCHING_CHANNEL, self._inching_timeout)

    async def set_inching(self, mode: int, channel: int, timeout_units: int):
        """Send inching command (ZCL command ID 0x01, manufacturer-specific)."""
        timeout_units = max(0, min(timeout_units, 0xFFFFFFFF))
        timeout_low = timeout_units & 0xFFFF
        timeout_high = (timeout_units >> 16) & 0xFFFF
        payload = bytearray([INCHING_CMD, INCHING_SUBCMD, INCHING_LENGTH, 0x80, mode, channel])
        payload.extend(timeout_low.to_bytes(2, 'little'))
        payload.extend(timeout_high.to_bytes(2, 'little'))
        checksum = 0
        for b in payload:
            checksum ^= b
        payload.append(checksum)
        _LOGGER.debug("Sending inching payload: %s", payload.hex())

        self._cmd_seq = (self._cmd_seq + 1) & 0xFF
        if self._cmd_seq == 0:
            self._cmd_seq = 1

        # Build ZCL header with manufacturer-specific flag and correct manufacturer code
        hdr = ZCLHeader(
            frame_control=FrameControl(
                frame_type=FrameType.CLUSTER_COMMAND,
                is_manufacturer_specific=True,
                direction=Direction.Client_to_Server,
                disable_default_response=False,
                reserved=0,
            ),
            manufacturer=SONOFF_MANUFACTURER_CODE,
            tsn=self._cmd_seq,
            command_id=0x01,
        )
        data = hdr.serialize() + bytes(payload)

        try:
            await self.endpoint.request(
                cluster=self.cluster_id,
                sequence=self._cmd_seq,
                data=data,
                expect_reply=False,
                use_ieee=False,
            )
        except Exception as e:
            _LOGGER.error("Failed to send inching command: %s", e)
            raise

    def handle_message(self, hdr, args):
        """Handle incoming inching report messages (ZCL command ID 0x01)."""
        if (
            hdr.command_id == 0x01
            and hdr.frame_control.is_manufacturer_specific
            and hdr.manufacturer == SONOFF_MANUFACTURER_CODE
            and len(args) >= 2
            and args[0] == INCHING_CMD
            and args[1] == INCHING_SUBCMD
        ):
            try:
                inching_num = args[2]
                offset = 4
                if inching_num >= 1 and offset + 6 <= len(args):
                    channel = args[offset]
                    mode_byte = args[offset + 1]
                    timeout_units = int.from_bytes(args[offset + 2:offset + 6], 'little')
                    enable = (mode_byte & 0x80) != 0
                    mode_bit = mode_byte & 0x01
                    self._inching_enable = enable
                    self._inching_mode_bit = mode_bit
                    self._inching_timeout = timeout_units
                    self._update_attribute(INCHING_ENABLE_ATTR, enable)
                    self._update_attribute(INCHING_MODE_ATTR, mode_bit)
                    self._update_attribute(INCHING_TIMEOUT_ATTR, timeout_units)
            except Exception:
                _LOGGER.exception("Failed to process inching report")
            return
        else:
            return super().handle_message(hdr, args)


(
    QuirkBuilder("SONOFF", "ZBMINIR2")
    .applies_to("SONOFF", "MINI-ZBD")
    .replaces(SonoffCluster)
    .replaces(OnOff, cluster_id=0x0006)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        translation_key="detach_relay",
        fallback_name="Detach relay",
    )
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .switch(
        SonoffCluster.AttributeDefs.inching_enable.name,
        SonoffCluster.cluster_id,
        translation_key="inching_enable",
        fallback_name="Inching enable",
    )
    .enum(
        SonoffCluster.AttributeDefs.inching_mode.name,
        InchingModeBit,
        SonoffCluster.cluster_id,
        translation_key="inching_mode",
        fallback_name="Inching mode",
    )
    .number(
        SonoffCluster.AttributeDefs.inching_timeout.name,
        SonoffCluster.cluster_id,
        min_value=0.5,
        max_value=3599.5,
        step=0.5,
        mode="box",
        multiplier=0.5,
        translation_key="inching_timeout",
        fallback_name="Inching timeout (s)",
    )
    .switch(
        SonoffCluster.AttributeDefs.power_on_behavior_delay_enable.name,
        SonoffCluster.cluster_id,
        translation_key="power_on_behavior_delay",
        fallback_name="Power-on behavior delay",
    )
    .number(
        SonoffCluster.AttributeDefs.power_on_behavior_delay_time.name,
        SonoffCluster.cluster_id,
        min_value=0.5,
        max_value=3599.5,
        step=0.5,
        mode="box",
        multiplier=0.5,
        translation_key="power_on_behavior_delay_time",
        fallback_name="Power-on behavior delay time (s)",
    )
    .device_automation_triggers(
        {
            ("External Switch action", "Single Click"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Single_click",
            },
            ("External Switch action", "Double Click"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Double_click",
            },
            ("External Switch action", "Long Press"): {
                CLUSTER_ID: SonoffCluster.cluster_id,
                ENDPOINT_ID: 1,
                COMMAND: "Long_press",
            }
        }
    )
    .add_to_registry()
)