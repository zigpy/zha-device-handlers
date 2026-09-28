"""Quirk for Aqara aqara.feeder.acn001."""

from __future__ import annotations

import json
import logging
from typing import Any, Final

from zigpy import types
from zigpy.profiles import zgp, zha
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    foundation,
)
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.helpers import UnsupportedAttribute

from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster, XiaomiCustomDevice

# 32 bit signed integer values that are encoded in FEEDER_ATTR = 0xFFF1
FEEDING = 0x04150055
FEEDING_REPORT = 0x041502BC
PORTIONS_DISPENSED = 0x0D680055
WEIGHT_DISPENSED = 0x0D690055
ERROR_DETECTED = 0x0D0B0055
SCHEDULING_STRING = 0x080008C8
DISABLE_LED_INDICATOR = 0x04170055
CHILD_LOCK = 0x04160055
FEEDING_MODE = 0x04180055
SERVING_SIZE = 0x0E5C0055
PORTION_WEIGHT = 0x0E5F0055

FEEDER_ATTR = 0xFFF1
FEEDER_ATTR_NAME = "feeder_attr"
# 3 byte header, 4 byte attribute id, 1 byte length prefix. ``FEEDER_ATTR`` is a
# single-TLV register that doubles as a "last value written" register, so it can
# also hold a short non-TLV payload; guard against that rather than assuming one.
FEEDER_ATTR_HEADER_LENGTH = 8

# Fake ZCL attribute ids we can use for entities for the opple cluster
ZCL_FEEDING = 0x1388
ZCL_LAST_FEEDING_SOURCE = 0x1389
ZCL_LAST_FEEDING_SIZE = 0x138A
ZCL_PORTIONS_DISPENSED = 0x138B
ZCL_WEIGHT_DISPENSED = 0x138C
ZCL_ERROR_DETECTED = 0x138D
ZCL_DISABLE_LED_INDICATOR = 0x138E
ZCL_CHILD_LOCK = 0x138F
ZCL_FEEDING_MODE = 0x1390
ZCL_SERVING_SIZE = 0x1391
ZCL_PORTION_WEIGHT = 0x1392
ZCL_SCHEDULE = 0x1393
ZCL_SCHEDULE_TEXT = 0x1394

AQARA_TO_ZCL: dict[int, int] = {
    FEEDING: ZCL_FEEDING,
    ERROR_DETECTED: ZCL_ERROR_DETECTED,
    DISABLE_LED_INDICATOR: ZCL_DISABLE_LED_INDICATOR,
    CHILD_LOCK: ZCL_CHILD_LOCK,
    FEEDING_MODE: ZCL_FEEDING_MODE,
    SERVING_SIZE: ZCL_SERVING_SIZE,
    PORTION_WEIGHT: ZCL_PORTION_WEIGHT,
}

ZCL_TO_AQARA: dict[int, int] = {
    ZCL_FEEDING: FEEDING,
    ZCL_DISABLE_LED_INDICATOR: DISABLE_LED_INDICATOR,
    ZCL_CHILD_LOCK: CHILD_LOCK,
    ZCL_FEEDING_MODE: FEEDING_MODE,
    ZCL_SERVING_SIZE: SERVING_SIZE,
    ZCL_PORTION_WEIGHT: PORTION_WEIGHT,
    ZCL_ERROR_DETECTED: ERROR_DETECTED,
}

LOGGER = logging.getLogger(__name__)

# Day bitmask used by the feeding schedule: bit 0 is Monday ... bit 6 is Sunday.
# Only the combinations the feeder offers as presets have a name here; any other
# bitmask is rendered as a comma separated day list. The preset names come from
# zigbee-herdsman-converters (``feederDaysLookup``, MIT).
SCHEDULE_DAY_ORDER: Final = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SCHEDULE_DAYS_BY_MASK: Final = {
    0x7F: "everyday",
    0x1F: "workdays",
    0x60: "weekend",
    0x01: "mon",
    0x02: "tue",
    0x04: "wed",
    0x08: "thu",
    0x10: "fri",
    0x20: "sat",
    0x40: "sun",
    0x55: "mon-wed-fri-sun",
    0x2A: "tue-thu-sat",
}
SCHEDULE_MASK_BY_DAYS: Final = {
    days: mask for mask, days in SCHEDULE_DAYS_BY_MASK.items()
}
SCHEDULE_DAY_BITS: Final = {day: 1 << bit for bit, day in enumerate(SCHEDULE_DAY_ORDER)}
# Unused schedule slots are the two character token ``//``.
SCHEDULE_EMPTY_SLOT: Final = b"//"
SCHEDULE_WHITESPACE: Final = b" \t\r\n\x00"
# Day token for a slot with no days set, i.e. a day bitmask of 0.
SCHEDULE_NO_DAYS: Final = "none"
# days, hour, minute, size, reserved
SCHEDULE_ENTRY_LENGTH: Final = 5
SCHEDULE_NO_TEXT: Final = "no schedule"
# The whole 0xFFF1 feeder attribute is a ``types.LVBytes`` capped at 255 bytes, and
# an 8 byte header carries the attribute id and the payload length, so 247 bytes are
# left for the scheduling string. Each slot costs two hex characters per byte plus a
# separating comma, which puts the *encoding* ceiling at 22 slots.
SCHEDULE_MAX_PAYLOAD_LENGTH: Final = 0xFF - FEEDER_ATTR_HEADER_LENGTH
SCHEDULE_ENCODABLE_SLOTS: Final = (SCHEDULE_MAX_PAYLOAD_LENGTH - 1) // (
    SCHEDULE_ENTRY_LENGTH * 2 + 1
)
# Only 4 slots have been verified end to end on real hardware. The device *accepts* 5
# and answers ``SUCCESS``, but it then reports the applied schedule back as two
# fragments in an undocumented layout that cannot be reassembled into the TLV it was
# sent, so the write cannot be confirmed: the cache keeps the previous schedule while
# the device holds a different one, and the UI reports the stale value as current.
# Reproduced twice, byte for byte. This is a limit on what can be *verified*, not a
# claim about the feeder's storage capacity -- 5 slots may well be stored correctly,
# there is just no way to tell from ZHA. Refusing them is what keeps a write from
# silently going unconfirmed.
SCHEDULE_MAX_SLOTS: Final = 4
# Returned by ``read_attributes`` while no schedule has been received yet.
SCHEDULE_DEFAULTS: Final = {
    ZCL_SCHEDULE: "[]",
    ZCL_SCHEDULE_TEXT: SCHEDULE_NO_TEXT,
}


class ScheduleString(types.CharacterString):
    """Decoded feeding schedule, carried as text rather than raw bytes.

    ``zha.set_zigbee_cluster_attribute`` runs the caller's value through
    ``convert_zcl_value`` against this declared type *before*
    :meth:`OppleCluster.write_attributes` sees it. A bytes type such as
    ``LongOctetString`` makes that helper call ``bytes(value)`` on the caller's
    string, raising ``TypeError: string argument without an encoding`` for every
    text input. The wire format is unaffected: ``write_attributes`` encodes the
    text to the device's ASCII payload and hands the bytes to the base class.
    """


def _schedule_day_name(mask: int) -> str:
    """Map a day bitmask to its name, falling back to a day list."""
    if mask in SCHEDULE_DAYS_BY_MASK:
        return SCHEDULE_DAYS_BY_MASK[mask]
    if mask == 0:
        return SCHEDULE_NO_DAYS
    days = [day for bit, day in enumerate(SCHEDULE_DAY_ORDER) if mask & (1 << bit)]
    return ",".join(days)


def _days_to_mask(days: str) -> int:
    """Resolve the day token of a schedule entry to its day bitmask.

    Accepts the named masks from ``SCHEDULE_DAYS_BY_MASK``, ``"none"`` for the
    empty set, and comma separated lists of individual day names -- the form
    ``_schedule_day_name`` falls back to for any other combination of days. That
    makes the encoder accept everything the decoder can emit, so a schedule read
    from the device can be written back after a tweak.
    """
    if days in SCHEDULE_MASK_BY_DAYS:
        return SCHEDULE_MASK_BY_DAYS[days]
    if days == SCHEDULE_NO_DAYS:
        return 0
    mask = 0
    for token in days.split(","):
        day = token.strip()
        if day not in SCHEDULE_DAY_BITS:
            raise ValueError(f"Unknown feeding schedule day: {day!r}")
        mask |= SCHEDULE_DAY_BITS[day]
    return mask


def _parse_feeder_schedule(payload: bytes) -> list[dict[str, Any]]:
    """Decode the ASCII schedule payload into a list of meal entries.

    Comma separated groups of ten hex characters, each decoding to five bytes
    (day bitmask, hour, minute, portion size, reserved), usually NUL
    terminated. An empty schedule is a single NUL.
    """
    entries: list[dict[str, Any]] = []
    for chunk in bytes(payload).split(b","):
        chunk = chunk.strip(SCHEDULE_WHITESPACE)
        if not chunk or chunk == SCHEDULE_EMPTY_SLOT:
            continue
        try:
            entry = bytes.fromhex(chunk.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            LOGGER.debug("Skipping unparsable schedule slot: %r", chunk)
            continue
        if len(entry) < SCHEDULE_ENTRY_LENGTH - 1:
            LOGGER.debug("Skipping short schedule slot: %r", chunk)
            continue
        entries.append(
            {
                "days": _schedule_day_name(entry[0]),
                "hour": entry[1],
                "minute": entry[2],
                "size": entry[3],
            }
        )
    return entries


def _schedule_to_text(entries: list[dict[str, Any]]) -> str:
    """Render schedule entries as "everyday 09:00 x1; mon 12:00 x2; ..."."""
    parts = [
        f"{entry['days']} {int(entry['hour']):02d}:{int(entry['minute']):02d}"
        f" x{int(entry['size'])}"
        for entry in entries
    ]
    return "; ".join(parts) if parts else SCHEDULE_NO_TEXT


def _schedule_to_json(entries: list[dict[str, Any]]) -> str:
    """Serialize schedule entries as compact JSON.

    The short keys (d/h/m/s) together with the four-slot write cap keep a
    full schedule comfortably inside Home Assistant's 255 character state
    limit.
    """
    payload = [
        {
            "d": entry["days"],
            "h": int(entry["hour"]),
            "m": int(entry["minute"]),
            "s": int(entry["size"]),
        }
        for entry in entries
    ]
    return json.dumps(payload, separators=(",", ":"))


def _schedule_entry_int(
    entry: dict[str, Any],
    long_key: str,
    short_key: str,
    minimum: int,
    maximum: int,
    default: int | None = None,
) -> int:
    """Read an integer schedule entry field, rejecting anything else by name.

    Accepts either the long key (``hour``) or the compact one (``h``). A
    missing key without a default and an out-of-range value raise
    ``ValueError``, a non-integer value -- ``bool`` and ``float`` included --
    raises ``TypeError``, each naming the field and the entry before any
    frame is built.
    """
    if long_key in entry:
        value = entry[long_key]
    elif short_key in entry:
        value = entry[short_key]
    elif default is not None:
        return default
    else:
        raise ValueError(
            f"Feeding schedule entry is missing its {long_key}/{short_key} "
            f"key: {entry!r}"
        )
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"Feeding schedule {long_key} must be an integer, "
            f"got {value!r} in {entry!r}"
        )
    if not minimum <= value <= maximum:
        raise ValueError(f"Feeding schedule {long_key} out of range: {value}")
    return value


def _encode_feeder_schedule(value: Any) -> bytes:
    """Encode a schedule into the ASCII payload the device expects.

    The inverse of :func:`_parse_feeder_schedule`: comma separated lowercase hex
    groups of five bytes each, NUL terminated, empty schedule a single NUL byte.
    Accepts the compact JSON string, the long keyed form, or a list of entries.
    Days are resolved by :func:`_days_to_mask`.

    Only ``"[]"`` and ``"no schedule"`` clear the schedule. An empty or blank
    string is rejected instead of silently wiping every meal, so a mistyped
    service call cannot empty the feeder; clearing it takes an explicit empty
    list.
    """
    if isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        text = str(value).strip()
        if text in ("[]", SCHEDULE_NO_TEXT):
            # Explicit clears only: the empty schedule in JSON form, and the
            # placeholder the text view shows when nothing is scheduled.
            raw = []
        else:
            if not text:
                raise ValueError('Feeding schedule cannot be empty: use "[]" to clear')
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid feeding schedule: {text!r}") from exc

    if not isinstance(raw, list):
        raise TypeError("Feeding schedule must be a JSON list")

    groups = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise TypeError(f"Feeding schedule entry must be an object: {entry!r}")
        days = entry.get("days", entry.get("d"))
        if days is None:
            raise ValueError(
                f"Feeding schedule entry is missing its days/d key: {entry!r}"
            )
        if not isinstance(days, str):
            raise TypeError(f"Feeding schedule days/d must be a string, got {days!r}")
        mask = _days_to_mask(days)
        hour = _schedule_entry_int(entry, "hour", "h", 0, 23)
        minute = _schedule_entry_int(entry, "minute", "m", 0, 59)
        # Portion sizes 1-10 match the feeder's serving size range as exposed
        # by zigbee-herdsman-converters (``ZNCWWSQ01LM``: valueMin 1, valueMax
        # 10), the range the Aqara app offers per feeding.
        size = _schedule_entry_int(entry, "size", "s", 1, 10, default=1)
        groups.append(bytes([mask, hour, minute, size, 0x00]).hex())

    if len(groups) > SCHEDULE_MAX_SLOTS:
        raise ValueError(
            f"Feeding schedule too long: {len(groups)} slots given, at most "
            f"{SCHEDULE_MAX_SLOTS} can be confirmed on this device. It accepts "
            f"longer schedules -- up to {SCHEDULE_ENCODABLE_SLOTS} that the "
            f"0xFFF1 attribute can encode -- but does not report them back "
            f"intact, so they cannot be verified and the reported schedule "
            f"would be left stale."
        )
    return (",".join(groups) + "\x00").encode("ascii")


class FeedingSource(types.enum8):
    """Feeding source."""

    Schedule = 0x00
    Feeder = 0x01
    Remote = 0x02


class FeedingMode(types.enum8):
    """Feeding mode."""

    Manual = 0x00
    Schedule = 0x01


# Served for ZCL_FEEDING_MODE whenever zigpy holds no usable value. The feeder
# answers a read of it with UNSUPPORTED_ATTRIBUTE, so the value can only enter
# the cache through a write made via this quirk: a confirmed write caches the
# written mode, and the device echoes the mode back as a 0xFFF1 report TLV too.
# The default matches what OppleCluster.__init__ seeds.
#
# The default has to be re-derivable rather than seeded once, because zigpy
# clears the whole attribute cache on every start and repopulates it from the
# database alone. A value stored in __init__ therefore never survives a
# restart, and ZHA drops the Mode entity as soon as its attribute has no value,
# leaving an orphaned registry entry reported as "no longer being provided by
# the zha integration". See OppleCluster.get and
# OppleCluster.is_attribute_unsupported.
FEEDING_MODE_DEFAULT: Final = FeedingMode.Manual


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        feeding: Final = ZCLAttributeDef(
            id=ZCL_FEEDING, type=types.Bool, manufacturer_code=0x115F
        )
        last_feeding_source: Final = ZCLAttributeDef(
            id=ZCL_LAST_FEEDING_SOURCE, type=FeedingSource, manufacturer_code=0x115F
        )
        last_feeding_size: Final = ZCLAttributeDef(
            id=ZCL_LAST_FEEDING_SIZE, type=types.uint8_t, manufacturer_code=0x115F
        )
        portions_dispensed: Final = ZCLAttributeDef(
            id=ZCL_PORTIONS_DISPENSED, type=types.uint16_t, manufacturer_code=0x115F
        )
        weight_dispensed: Final = ZCLAttributeDef(
            id=ZCL_WEIGHT_DISPENSED, type=types.uint32_t, manufacturer_code=0x115F
        )
        error_detected: Final = ZCLAttributeDef(
            id=ZCL_ERROR_DETECTED, type=types.Bool, manufacturer_code=0x115F
        )
        disable_led_indicator: Final = ZCLAttributeDef(
            id=ZCL_DISABLE_LED_INDICATOR, type=types.Bool, manufacturer_code=0x115F
        )
        child_lock: Final = ZCLAttributeDef(
            id=ZCL_CHILD_LOCK, type=types.Bool, manufacturer_code=0x115F
        )
        feeding_mode: Final = ZCLAttributeDef(
            id=ZCL_FEEDING_MODE,
            type=FeedingMode,
            manufacturer_code=0x115F,
        )
        serving_size: Final = ZCLAttributeDef(
            id=ZCL_SERVING_SIZE, type=types.uint8_t, manufacturer_code=0x115F
        )
        portion_weight: Final = ZCLAttributeDef(
            id=ZCL_PORTION_WEIGHT, type=types.uint8_t, manufacturer_code=0x115F
        )
        schedule: Final = ZCLAttributeDef(
            id=ZCL_SCHEDULE,
            type=ScheduleString,
            access="rw",
            manufacturer_code=0x115F,
        )
        # Derived from ``schedule``; never sent to the device.
        schedule_text: Final = ZCLAttributeDef(
            id=ZCL_SCHEDULE_TEXT,
            type=ScheduleString,
            access="r",
            manufacturer_code=0x115F,
        )
        feeder_attr: Final = ZCLAttributeDef(
            id=FEEDER_ATTR, type=types.LVBytes, manufacturer_code=0x115F
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._send_sequence: int = None
        # Payload of the most recent schedule write, awaiting the device's echo.
        self._pending_schedule: bytes | None = None
        # Set default values for attributes
        if ZCL_DISABLE_LED_INDICATOR not in self._attr_cache:
            self._update_attribute(ZCL_DISABLE_LED_INDICATOR, False)
        if ZCL_CHILD_LOCK not in self._attr_cache:
            self._update_attribute(ZCL_CHILD_LOCK, False)
        if ZCL_FEEDING_MODE not in self._attr_cache:
            self._update_attribute(ZCL_FEEDING_MODE, FeedingMode.Manual)
        if ZCL_SERVING_SIZE not in self._attr_cache:
            self._update_attribute(ZCL_SERVING_SIZE, 1)
        if ZCL_PORTION_WEIGHT not in self._attr_cache:
            self._update_attribute(ZCL_PORTION_WEIGHT, 8)
        if ZCL_ERROR_DETECTED not in self._attr_cache:
            self._update_attribute(ZCL_ERROR_DETECTED, False)
        if ZCL_PORTIONS_DISPENSED not in self._attr_cache:
            self._update_attribute(ZCL_PORTIONS_DISPENSED, 0)
        if ZCL_WEIGHT_DISPENSED not in self._attr_cache:
            self._update_attribute(ZCL_WEIGHT_DISPENSED, 0)
        # ``schedule``/``schedule_text`` are deliberately NOT seeded here: zigpy restores
        # persisted attributes after construction, so seeding would overwrite the
        # stored schedule on every restart. The placeholder is applied at read
        # time instead, see ``read_attributes``.

        # Subscribe to attribute events to parse feeder_attr
        self.on_event(AttributeReportedEvent.event_type, self._handle_attribute_event)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_attribute_event)
        # A plain read of FEEDER_ATTR is answered with the full scheduling TLV,
        # so it is parsed too: that is what lets the schedule be populated on
        # demand instead of only waiting for a report, a power cycle or zigpy's
        # restored database values. Verified on hardware -- reading 0xFFF1
        # returns "7f09000100,7f0d000100,7f13000100".
        self.on_event(AttributeReadEvent.event_type, self._handle_attribute_event)

    def _handle_attribute_event(
        self,
        event: AttributeReadEvent | AttributeReportedEvent | AttributeUpdatedEvent,
    ) -> None:
        """Handle attribute report/update event to parse feeder attribute."""
        if event.attribute_id == FEEDER_ATTR:
            self._parse_feeder_attribute(event.value)

    def _update_feeder_attribute(self, attrid: int, value: Any) -> None:
        zcl_attr_def = self.attributes.get(AQARA_TO_ZCL[attrid])
        self._update_attribute(zcl_attr_def.id, zcl_attr_def.type.deserialize(value)[0])

    def _resolve_attribute_id(self, attr: int | str | ZCLAttributeDef) -> int | None:
        """Resolve an attribute id from an id, name or attribute definition."""
        if isinstance(attr, ZCLAttributeDef):
            return attr.id
        if isinstance(attr, int):
            return attr
        attr_def = self.attributes_by_name.get(attr)
        return attr_def.id if attr_def is not None else None

    def _feeding_mode_value(self) -> FeedingMode:
        """Return the cached feeding mode, or the default when it is unusable.

        ``ZCL_FEEDING_MODE`` cannot be read from the feeder, so a cached value
        only ever comes from a local seed, a write made through this quirk, or
        the 0xFFF1 report TLV the device echoes after such a write. Clearing
        the attribute cache, replaying a poisoned database row, or simply never
        having read the attribute each leave the entity with no value at all.
        """
        try:
            return self._attr_cache.get_value(self.find_attribute(ZCL_FEEDING_MODE))
        except (UnsupportedAttribute, KeyError):
            return FEEDING_MODE_DEFAULT

    def get(self, key: int | str | ZCLAttributeDef, default: Any = None) -> Any:
        """Return a cached value, keeping the feeding mode always readable.

        ``zigpy.appdb`` empties the attribute cache on every start and refills
        it from the database only, which discards the value seeded in
        ``__init__``. ZHA builds its Mode entity from ``cluster.get(...)`` and
        skips it when that returns ``None``, so the control disappears from the
        device page until the attribute is read successfully again.
        """
        if self._resolve_attribute_id(key) == ZCL_FEEDING_MODE:
            return self._feeding_mode_value()
        return super().get(key, default)

    def is_attribute_unsupported(self, attribute: int | str | ZCLAttributeDef) -> bool:
        """Report the feeding mode as supported regardless of a stale marker.

        ``zigpy.appdb`` replays a cached ``UNSUPPORTED_ATTRIBUTE`` row as a
        permanent unsupported marker on every start, and ZHA refuses to build
        any entity whose attribute is marked unsupported. The marker is wrong
        here: ``get()`` and ``read_attributes`` serve the value locally, so a
        poisoned row must not hide the Mode control. The check stays pure --
        the in-memory marker is left alone instead of dropped as a side
        effect, since ``get()`` already copes with it. The marker is only
        hidden, not healed: a poisoned ``status=134`` database row survives
        restarts until a confirmed mode write rewrites it, because the local
        read never stores a value itself.
        """
        if self._resolve_attribute_id(attribute) == ZCL_FEEDING_MODE:
            return False
        return super().is_attribute_unsupported(attribute)

    def _parse_feeder_attribute(self, value: bytes) -> None:
        """Parse the feeder attribute."""
        value = bytes(value)

        # The register also stores arbitrary user written data, so ignore
        # anything too short to be a TLV rather than failing the caller's read.
        if len(value) < FEEDER_ATTR_HEADER_LENGTH:
            LOGGER.debug(
                "OppleCluster._parse_feeder_attribute: ignoring %d byte value, "
                "too short to be a feeder TLV: %s",
                len(value),
                value,
            )
            return

        attribute, _ = types.int32s_be.deserialize(value[3:7])
        LOGGER.debug("OppleCluster._parse_feeder_attribute: attribute: %s", attribute)
        length, _ = types.uint8_t.deserialize(value[7:8])
        LOGGER.debug("OppleCluster._parse_feeder_attribute: length: %s", length)
        attribute_value = value[
            FEEDER_ATTR_HEADER_LENGTH : FEEDER_ATTR_HEADER_LENGTH + length
        ]
        LOGGER.debug("OppleCluster._parse_feeder_attribute: value: %s", attribute_value)

        if attribute in AQARA_TO_ZCL:
            self._update_feeder_attribute(attribute, attribute_value)
        elif attribute == FEEDING_REPORT:
            attr_str = attribute_value.decode("utf-8", errors="replace")
            try:
                feeding_source = FeedingSource(int(attr_str[0:2]))
                feeding_size = int(attr_str[3:4], base=16)
            except (KeyError, ValueError):
                # The register also stores arbitrary user written data, so a
                # report that does not parse must not raise out of the report
                # handler, and silently recording a default source would be
                # worse than skipping it.
                LOGGER.warning(
                    "OppleCluster._parse_feeder_attribute: skipping malformed "
                    "feeding report: %s",
                    attribute_value,
                )
            else:
                self._update_attribute(ZCL_LAST_FEEDING_SOURCE, feeding_source)
                self._update_attribute(ZCL_LAST_FEEDING_SIZE, feeding_size)
        elif attribute == PORTIONS_DISPENSED:
            portions_per_day, _ = types.uint16_t_be.deserialize(attribute_value)
            self._update_attribute(ZCL_PORTIONS_DISPENSED, portions_per_day)
        elif attribute == WEIGHT_DISPENSED:
            weight_per_day, _ = types.uint32_t_be.deserialize(attribute_value)
            self._update_attribute(ZCL_WEIGHT_DISPENSED, weight_per_day)
        elif attribute == SCHEDULING_STRING:
            self._update_schedule(attribute_value)
        else:
            LOGGER.debug(
                "OppleCluster._parse_feeder_attribute: unhandled attribute: %s value: %s",
                attribute,
                attribute_value,
            )

    def _update_schedule(self, payload: bytes) -> None:
        """Decode the scheduling string and store both schedule attributes."""
        entries = _parse_feeder_schedule(payload)
        LOGGER.debug(
            "OppleCluster._update_schedule: decoded schedule: %s",
            _schedule_to_text(entries),
        )
        self._check_schedule_applied(entries)
        self._update_attribute(ZCL_SCHEDULE, _schedule_to_json(entries))
        self._update_attribute(ZCL_SCHEDULE_TEXT, _schedule_to_text(entries))

    def _check_schedule_applied(self, entries: list[dict[str, Any]]) -> None:
        """Warn when the device echoes a schedule other than the one written.

        The device acknowledges the 0xFFF1 write before it commits the schedule
        and reports what it actually applied a moment later, so the service call
        reports success either way and the echo is the only evidence that a write
        took effect. Compare the two and warn if the device stored something else,
        which is how a schedule longer than the device can hold shows up.

        The comparison is over re-encoded bytes rather than decoded text because
        the decoder resolves a day mask back to a named preset where one exists:
        a caller that wrote ``mon,tue,wed,thu,fri`` is echoed ``workdays``.
        Re-encoding reduces both spellings to the same mask. Comparing raw echo
        bytes against the sent payload would instead mismatch every time, since
        the device reports uppercase hex.

        Only one write is tracked at a time, so overlapping writes or a read
        report arriving between a write and its echo can pair the wrong payloads
        and produce a spurious warning. That is acceptable: a false warning is
        noise, whereas dropping the comparison would lose the signal entirely.
        """
        requested, self._pending_schedule = self._pending_schedule, None
        if requested is None:
            return
        try:
            applied = _encode_feeder_schedule(_schedule_to_json(entries))
        except (TypeError, ValueError):
            # A comparison failure must never break decoding of the schedule
            # itself; the attributes set by the caller are still correct.
            LOGGER.debug(
                "OppleCluster._check_schedule_applied: could not re-encode echoed "
                "schedule to compare against the written schedule",
                exc_info=True,
            )
            return
        if applied == requested:
            return
        sent_entries = _parse_feeder_schedule(requested)
        LOGGER.warning(
            "OppleCluster: feeder applied a different feeding schedule than was "
            "written, the device may have truncated it: wrote %d slot(s) [%s], "
            "device stored %d slot(s) [%s]",
            len(sent_entries),
            _schedule_to_text(sent_entries),
            len(entries),
            _schedule_to_text(entries),
        )

    async def read_attributes(
        self,
        attributes: list[int | str | ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """Serve the schedule attributes locally instead of reading the device.

        The feeding schedule is not a real ZCL attribute: it is decoded from the
        scheduling string carried inside ``FEEDER_ATTR`` (``0xFFF1``) reports.

        ``FEEDER_ATTR`` is a single-TLV register, so a read returns whichever inner
        attribute the feeder currently holds -- never necessarily the schedule --
        and decoding such a response would mutate unrelated cached attributes as a
        side effect. The cache is therefore filled by genuine device reports, a
        power cycle (which reports every TLV), a read of ``FEEDER_ATTR`` that
        happens to return the schedule, and zigpy's restored database values. Reads
        cost no Zigbee traffic, and when nothing has been cached yet a placeholder
        is returned so the attribute is always readable.

        ``ZCL_FEEDING_MODE`` (``0x1390``) is served locally for a different reason:
        the feeder accepts a write but answers a read with
        ``UNSUPPORTED_ATTRIBUTE``. ZHA reads the attribute on every start, and
        zigpy persists that failure as ``status=134`` in ``attributes_cache``,
        which it then replays as a permanent unsupported marker. ZHA drops any
        entity whose attribute is marked unsupported, so a writable attribute
        becomes impossible to configure and the registry entry is orphaned.
        Answering locally keeps the device from ever being asked, so the cached
        row cannot be poisoned, and the value stays available to ZHA.

        The attribute keeps its declared access bits: it is genuinely writable.
        ``access="w"`` was tried and reverted -- ZHA's UI does consult the bits,
        so it drops the read button from the Manage Zigbee device panel, but
        the Zigbee read path itself ignores them, so ZHA's own startup read
        still went out and re-poisoned the row. The interception above is what
        actually prevents the poisoning.
        """
        remaining: list[int | str | ZCLAttributeDef] = []
        requested: list[tuple[int, int | str | ZCLAttributeDef]] = []

        for attribute in attributes:
            attribute_id = self._resolve_attribute_id(attribute)
            if attribute_id in (ZCL_SCHEDULE, ZCL_SCHEDULE_TEXT, ZCL_FEEDING_MODE):
                requested.append((attribute_id, attribute))
            else:
                remaining.append(attribute)

        if not requested:
            return await super().read_attributes(attributes, **kwargs)

        success, failure = {}, {}
        if remaining:
            success, failure = await super().read_attributes(remaining, **kwargs)

        for attribute_id, attribute in requested:
            if attribute_id == ZCL_FEEDING_MODE:
                success[attribute] = self._feeding_mode_value()
                continue
            try:
                success[attribute] = self._attr_cache.get_value(
                    self.find_attribute(attribute_id)
                )
            except UnsupportedAttribute:
                # The schedule attributes have no device-independent meaning, so
                # they keep reporting the failure instead of inventing a value.
                failure[attribute] = foundation.Status.UNSUPPORTED_ATTRIBUTE
            except KeyError:
                success[attribute] = SCHEDULE_DEFAULTS[attribute_id]

        return success, failure

    def _build_feeder_attribute(
        self, attribute_id: int, value: Any = None, length: int | None = None
    ):
        """Build the Xiaomi feeder attribute."""
        LOGGER.debug(
            "OppleCluster.build_feeder_attribute: id: %s, value: %s length: %s",
            attribute_id,
            value,
            length,
        )
        self._send_sequence = ((self._send_sequence or 0) + 1) % 256
        val = bytes([0x00, 0x02, self._send_sequence])
        self._send_sequence += 1
        val += types.int32s_be(attribute_id).serialize()
        if length is not None and value is not None:
            val += types.uint8_t(length).serialize()
        if value is not None:
            if isinstance(value, (bytes, bytearray)):
                # Raw payloads (e.g. the scheduling string) are already encoded.
                val += bytes(value)
            elif length == 1:
                val += types.uint8_t(value).serialize()
            elif length == 2:
                val += types.uint16_t_be(value).serialize()
            elif length == 4:
                val += types.uint32_t_be(value).serialize()
            else:
                val += value
        LOGGER.debug(
            "OppleCluster.build_feeder_attribute: id: %s, cooked value: %s length: %s",
            attribute_id,
            val,
            length,
        )
        return FEEDER_ATTR_NAME, val

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes to device with internal 'attributes' validation."""
        attrs = {}
        schedule_written = False
        written_mode: Any = None
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == ZCL_SCHEDULE:
                raw = _encode_feeder_schedule(value)
                name, cooked = self._build_feeder_attribute(
                    SCHEDULING_STRING, raw, len(raw)
                )
                attrs[name] = cooked
                # Compared against the device's echo in _check_schedule_applied.
                self._pending_schedule = raw
                schedule_written = True
            elif attr_id == ZCL_SCHEDULE_TEXT:
                # Derived from ``schedule``; the device has no such attribute, and
                # ``access="r"`` is not enforced on the service-call write path.
                raise UnsupportedAttribute(
                    "schedule_text is read-only, write schedule (0x1393) instead"
                )
            elif attr_id in ZCL_TO_AQARA:
                attribute, cooked_value = self._build_feeder_attribute(
                    ZCL_TO_AQARA[attr_id],
                    value,
                    4 if attr_def.name in ["serving_size", "portion_weight"] else 1,
                )
                attrs[attribute] = cooked_value
                if attr_id == ZCL_FEEDING_MODE:
                    # Cached only after the write is confirmed, below: zigpy
                    # does not raise on a non-SUCCESS status, so caching here
                    # would leave the select showing -- and zigpy persisting
                    # -- a mode the feeder never took.
                    written_mode = value
            else:
                attrs[attr] = value
        LOGGER.debug("OppleCluster.write_attributes: %s", attrs)
        # Skip attr cache because of the encoding from Xiaomi and
        # the attributes are reported back by the device
        kwargs.pop("update_cache", None)  # To not break when this is passed already
        try:
            results = await super().write_attributes(
                attrs, update_cache=False, **kwargs
            )
        except Exception:
            # No echo is coming, so drop the payload rather than let it be
            # compared against whatever report arrives next.
            self._pending_schedule = None
            raise

        # zigpy reports a failed write as a status record instead of raising,
        # so the pending schedule and the written mode are settled by
        # inspecting the result. Every value this quirk translates is carried
        # inside a single 0xFFF1 write, so its records are the ones to check.
        records = [record for result in results for record in result]
        feeder_attr_ok = any(record.attrid == FEEDER_ATTR for record in records) and (
            all(
                record.status == foundation.Status.SUCCESS
                for record in records
                if record.attrid == FEEDER_ATTR
            )
        )
        if schedule_written and not feeder_attr_ok:
            # Same reason as the exception path above: this write has no echo
            # coming, and a stale payload would be compared against the next
            # unrelated report, e.g. the power-on TLVs after a power cycle,
            # and warn about a truncation that never happened.
            self._pending_schedule = None
        if written_mode is not None and feeder_attr_ok:
            # Cache the mode only now that the write is confirmed. The device
            # also echoes the mode back as a 0xFFF1 report TLV, which reaches
            # the cache on its own; this update additionally fires the
            # AttributeUpdatedEvent that makes zigpy persist the row, so a
            # poisoned status=134 database row is rewritten as a success.
            self._update_attribute(ZCL_FEEDING_MODE, written_mode)
        return results


class FeederTimeCluster(CustomCluster, Time):
    """Time cluster that answers the feeder's time polls with *local* time.

    ZCL R8 §3.2.2.1 defines attribute ``0x0000`` as "the time in UTC, expressed as
    the number of seconds since 1st January 2000 00:00:00 UTC", which is what
    zigpy's stock ``Time`` cluster serves. This feeder violates that: it polls the
    coordinator for ``0x0000`` and stores the result as its own local wall clock,
    then schedules feedings from it. The schedule carries no timezone (each slot is
    just day mask / hour / minute / size), so answering with UTC shifts every meal
    by the UTC offset.

    Zigbee2MQTT works around this in zigbee-herdsman-converters commit 5e0cd127
    (PR #5364) with ``secondsUTC - getTimezoneOffset() * 60``, noting "Aqara
    feeder C1 polls the time during the interview, need to send back the local
    time instead of the UTC". We match that proven behaviour.

    This knowingly deviates from the spec, but only for this device.
    ``_skip_registry`` keeps the override out of zigpy's global cluster registry
    so every other device keeps the spec-correct responder. The offset is
    evaluated per request, so DST is correct as of the most recent poll. The
    value is delegated to zigpy's own ``local_time`` handler rather than
    reimplemented here, so the arithmetic has a single upstream definition.
    Attribute ``0x0006`` (``standard_time``) is deliberately *not* used: it
    subtracts a DST delta that is always zero in practice since
    ``datetime.now().astimezone()`` yields a fixed-offset ``tzinfo``. Finally,
    the offset comes from the process timezone, not Home Assistant's
    ``hass.config.time_zone``, since zigpy offers no way to override it.
    """

    _skip_registry = True

    def handle_read_attribute_time(self) -> types.UTCTime:
        """Return the current local time as seconds since 2000-01-01."""
        return types.UTCTime(int(self.handle_read_attribute_local_time()))


class AqaraFeederAcn001(XiaomiCustomDevice):
    """Aqara aqara.feeder.acn001 custom device implementation."""

    signature = {
        MODEL: "aqara.feeder.acn001",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    replacement = {
        MANUFACTURER: "Aqara",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OppleCluster,
                    # This device misreads a spec-compliant UTC response as local time.
                    # See FeederTimeCluster.
                    FeederTimeCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
