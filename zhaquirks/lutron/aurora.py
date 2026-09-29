"""Lutron Aurora Z3-1BRL button and rotary notifications (firmware 0x00000c12).

Every Philips-style 0xFC00 notification is preserved as ``aurora_notification``.
Known reports additionally produce immediate normalized input events. Native
press/hold/release reports are not delayed or grouped into multi-clicks.

Rotary payload fields are [phase, A, B, C, D, E, F]. Captures identify C as a
signed cumulative movement counter. Fresh windows have phase 1 and 4*A == 7*C;
other reports continue the counter, including phase-1 direction changes and
D timer rollovers. This reset signature is empirical, not a published firmware
contract. A/E are adjusted amounts and are never exposed as physical deltas.

``rotation`` carries a signed delta in degrees (clockwise positive), using the
Hue API's nominal resolution of 1000 counts per revolution. The device phase
is preserved separately. Counter differences use signed 16-bit arithmetic,
assuming less than half the counter range of movement between reports.

Unknown layouts remain raw. Startup mid-window and detectable sequence gaps
produce ``rotation_unavailable`` instead of a fabricated amount. The observed
7-bit sequence wrap is accepted alongside the standard 8-bit wrap. Other
sequence discontinuities establish a new baseline. A lost whole sequence
cycle is not detectable. State belongs to this cluster and resets on reload.

The prefix is a uint16 control ID and a uint8 control type. Numeric fields keep
their offsets/types, and undecoded tails and complete frame bytes are retained.
Shared Philips cluster identifiers do not imply shared gesture processing or
that this empirical Aurora counter decoder applies to other Philips remotes.
"""

from collections.abc import Iterator
from typing import Any, ClassVar

from zha.application.platforms import BaseEntity
from zha.application.platforms.event import BaseEvent
from zha.application.platforms.event.const import ButtonEventType, EventDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    LONG_PRESS,
    LONG_RELEASE,
    PRESSED,
    ROTARY_KNOB,
    ROTATED,
    SHORT_RELEASE,
    ZHA_SEND_EVENT,
)
from zhaquirks.philips import PhilipsRemoteCluster

PHILIPS_MANUFACTURER_CODE = 0x100B
DIAL_CONTROL_ID = 0x14
NUMERIC_TYPES = {
    foundation.DataTypeId.enum8: t.enum8,
    foundation.DataTypeId.uint16: t.uint16_t,
    foundation.DataTypeId.int16: t.int16s,
}


class AuroraCluster(CustomCluster):
    """Preserve native notifications and normalize supported input reports."""

    cluster_id = PhilipsRemoteCluster.cluster_id
    ep_attribute = "aurora"
    name = "Aurora notifications"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Track the button phase and rotary baseline per device."""
        super().__init__(*args, **kwargs)
        self._holding = False
        self._rotation_count: int | None = None
        self._last_notification: tuple[int, bytes] | None = None

    class ClientCommandDefs(BaseCommandDefs):
        """Keep the whole notification, including extensions and unknown fields."""

        notification = ZCLCommandDef(
            id=PhilipsRemoteCluster.ClientCommandDefs.notification.id,
            schema={"payload": t.List[t.uint8_t]},
            manufacturer_code=PHILIPS_MANUFACTURER_CODE,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Emit one immediate event with raw bytes and typed numeric fields."""
        if (
            hdr.manufacturer != PHILIPS_MANUFACTURER_CODE
            or hdr.command_id != self.ClientCommandDefs.notification.id
            or hdr.direction != foundation.Direction.Server_to_Client
        ):
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        payload = bytes(args.payload)
        event: dict[str, Any] = {
            "frame_hex": (hdr.serialize() + payload).hex(),
            "payload_hex": payload.hex(),
            "manufacturer_code": hdr.manufacturer,
            "command_id": hdr.command_id,
            "sequence": hdr.tsn,
        }
        if len(payload) >= 2:
            event["control_id"] = int.from_bytes(payload[:2], "little")
        if len(payload) >= 3:
            event["control_type"] = payload[2]
            event["prefix_hex"] = payload[:3].hex()
            fields = []
            offset = 3
            while offset < len(payload):
                type_id = payload[offset]
                value_type = NUMERIC_TYPES.get(type_id)
                if value_type is None:
                    break
                try:
                    value, remainder = value_type.deserialize(payload[offset + 1 :])
                except ValueError:
                    break
                fields.append({"offset": offset, "type": type_id, "value": int(value)})
                offset = len(payload) - len(remainder)
            event["fields"] = fields
            if offset < len(payload):
                event["undecoded_hex"] = payload[offset:].hex()
            if fields and fields[0]["type"] == foundation.DataTypeId.enum8:
                event["event_code"] = fields[0]["value"]

        self.listener_event(ZHA_SEND_EVENT, "aurora_notification", event)
        notification = (int(hdr.tsn), payload)
        if notification == self._last_notification:
            return
        discontinuity = False
        if self._last_notification is not None:
            previous_sequence = self._last_notification[0]
            expected = (previous_sequence + 1) % 256
            discontinuity = hdr.tsn != expected and not (
                previous_sequence == 127 and hdr.tsn == 0
            )
            if discontinuity:
                self._holding = False
                self._rotation_count = None
        self._last_notification = notification
        if len(payload) < 3:
            self._holding = False
            self._rotation_count = None
        self._normalize_button(payload, hdr.tsn)
        self._normalize_rotation(payload, event, discontinuity=discontinuity)

    def _normalize_rotation(
        self, payload: bytes, event: dict[str, Any], *, discontinuity: bool = False
    ) -> None:
        """Translate cumulative rotary counts to signed relative angles."""
        if event.get("control_id") != DIAL_CONTROL_ID:
            return
        fields = event.get("fields", [])
        if (
            len(payload) != 23
            or payload[:3] != bytes.fromhex("140001")
            or [f["type"] for f in fields] != [0x30, 0x29, 0x21, 0x29, 0x21, 0x29, 0x21]
        ):
            self._rotation_count = None
            self._rotation_unavailable(event["sequence"], "unsupported_payload")
            return
        code, adjusted, _, count, _, duplicate, period = (f["value"] for f in fields)
        if code not in (1, 2) or adjusted != duplicate or period != 400:
            self._rotation_count = None
            self._rotation_unavailable(event["sequence"], "unsupported_payload")
            return
        previous = self._rotation_count
        self._rotation_count = count
        if discontinuity:
            self._rotation_unavailable(event["sequence"], "sequence_gap")
            return
        reset = code == 1 and 4 * adjusted == 7 * count
        if reset:
            delta = count
        elif previous is not None:
            delta = (count - previous + 32768) % 65536 - 32768
        else:
            self._rotation_unavailable(event["sequence"], "missing_baseline")
            return
        if delta == -32768:
            self._rotation_unavailable(event["sequence"], "ambiguous_counter_wrap")
            return
        self.listener_event(
            ZHA_SEND_EVENT,
            "rotation",
            {
                "control_id": DIAL_CONTROL_ID,
                "sequence": event["sequence"],
                "phase": "start" if code == 1 else "repeat",
                "delta_counts": delta,
                "delta_degrees": delta * 360 / 1000,
                "direction": ("clockwise" if delta > 0 else "counterclockwise")
                if delta
                else None,
            },
        )

    def _rotation_unavailable(self, sequence: int, reason: str) -> None:
        """Report an undecodable interval without substituting zero movement."""
        self.listener_event(
            ZHA_SEND_EVENT,
            "rotation_unavailable",
            {"control_id": DIAL_CONTROL_ID, "sequence": sequence, "reason": reason},
        )

    def _normalize_button(self, payload: bytes, sequence: int) -> None:
        """Translate native button phases and decisecond durations."""
        if (
            len(payload) != 8
            or payload[:4] != bytes.fromhex("01000030")
            or payload[5] != foundation.DataTypeId.uint16
        ):
            return
        code = payload[4]
        if code == 1:
            command = "hold" if self._holding else "long_press_start"
            self._holding = True
        else:
            self._holding = False
            command = {0: "press_start", 2: "press_end", 3: "long_press_end"}.get(code)
        if command is not None:
            self.listener_event(
                ZHA_SEND_EVENT,
                command,
                {
                    "control_id": 1,
                    "sequence": sequence,
                    "duration_seconds": int.from_bytes(payload[6:8], "little") / 10,
                },
            )


class AuroraEvent(BaseEvent):
    """Expose a single Aurora control through ZHA's native event platform."""

    _control_id: int

    def on_add(self) -> None:
        """Listen directly to the quirk cluster, before HA event-bus forwarding."""
        super().on_add()
        self._cluster.add_listener(self)
        self._on_remove_callbacks.append(lambda: self._cluster.remove_listener(self))

    def zha_send_event(self, command: str, args: Any) -> None:
        """Forward normalized input without decoding or gesture inference."""
        if (
            command in self.event_types
            and isinstance(args, dict)
            and args.get("control_id") == self._control_id
        ):
            self._trigger_event(command, dict(args))


class AuroraButton(AuroraEvent):
    """Aurora's push button."""

    _control_id = 1
    _unique_id_suffix = "button"
    _attr_translation_key = "aurora_button"
    _attr_fallback_name = "Button"
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types: ClassVar[list[str]] = [
        ButtonEventType.PRESS_START,
        ButtonEventType.LONG_PRESS_START,
        "hold",
        ButtonEventType.PRESS_END,
        ButtonEventType.LONG_PRESS_END,
    ]


class AuroraDial(AuroraEvent):
    """Aurora's infinite rotary dial."""

    _control_id = 0x14
    _unique_id_suffix = "dial"
    _attr_translation_key = "aurora_dial"
    _attr_fallback_name = "Dial"
    _attr_event_types: ClassVar[list[str]] = ["rotation", "rotation_unavailable"]


class AuroraDevice(QuirkV2Device):
    """Discover the Aurora's input controls alongside its standard entities."""

    def discover_entities(self) -> Iterator[BaseEntity]:
        """Expose the normalized button and dial through ZHA's event platform."""
        yield from super().discover_entities()
        endpoint = self.endpoints.get(1)
        if endpoint is None:
            return
        cluster = endpoint.zigpy_endpoint.in_clusters.get(AuroraCluster.cluster_id)
        if not isinstance(cluster, AuroraCluster):
            return
        for entity_class in (AuroraButton, AuroraDial):
            yield entity_class(endpoint=endpoint, device=self, cluster=cluster)


(
    QuirkBuilder("Lutron", "Z3-1BRL")
    .replaces(AuroraCluster)
    .zha_device_class(AuroraDevice)
    .device_automation_triggers(
        {
            (PRESSED, BUTTON): {COMMAND: "press_start"},
            (LONG_PRESS, BUTTON): {COMMAND: "long_press_start"},
            (SHORT_RELEASE, BUTTON): {COMMAND: "press_end"},
            (LONG_RELEASE, BUTTON): {COMMAND: "long_press_end"},
            (ROTATED, ROTARY_KNOB): {COMMAND: "rotation"},
        }
    )
    .add_to_registry()
)
