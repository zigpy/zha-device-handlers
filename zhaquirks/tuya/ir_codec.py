"""Codec for the Tuya/Zosung IR ``key_code`` format.

A ``key_code`` is base64 over a stream of literal and back-reference blocks that
expands to little-endian uint16 pulse and space durations in microseconds. Ported
from zigbee-herdsman-converters' ``lib/zosung.ts``, whose decoder output this
matches, and free of zigpy so it can be tested on its own. The decoder ships with the
encoder so a learned code can be turned back into raw timings, and so the encoder can
be checked against the reference implementation's decoder.
"""

import base64
from collections.abc import Sequence

MAX_LITERAL_BLOCK = 32
MIN_MATCH = 4
MAX_DISTANCE = 0x2000


def _emit_literals(out: bytearray, pending: bytearray) -> None:
    """Flush buffered literal bytes as length-prefixed blocks."""
    for start in range(0, len(pending), MAX_LITERAL_BLOCK):
        block = pending[start : start + MAX_LITERAL_BLOCK]
        out.append((len(block) - 1) & 0x1F)
        out += block
    pending.clear()


def _longest_match(raw: bytes, pos: int) -> tuple[int, int]:
    """Find the longest earlier run repeating at `pos`, as (length, offset)."""
    best_length = 0
    best_offset = 0
    earliest = max(0, pos - MAX_DISTANCE)

    for start in range(pos - 1, earliest - 1, -1):
        length = 0
        # Matches may overrun into what they produce, LZ77 style.
        while pos + length < len(raw) and raw[start + length] == raw[pos + length]:
            length += 1
        if length > best_length:
            best_length = length
            best_offset = pos - start

    return best_length, best_offset


def _emit_match(out: bytearray, length: int, offset: int) -> None:
    """Write one back-reference block."""
    distance = offset - 1
    block_type = 7 if length >= 9 else length - 2
    out.append((block_type << 5) | ((distance >> 8) & 0x1F))

    if block_type == 7:
        extra = length - 9
        while extra >= 0xFF:
            out.append(0xFF)
            extra -= 0xFF
        # Always < 0xFF, so it terminates the chain rather than extending it.
        out.append(extra)

    out.append(distance & 0xFF)


def _compress(raw: bytes) -> bytearray:
    """Greedily replace repeated runs with back-references."""
    out = bytearray()
    pending = bytearray()
    pos = 0

    while pos < len(raw):
        length, offset = _longest_match(raw, pos)
        if length >= MIN_MATCH:
            _emit_literals(out, pending)
            _emit_match(out, length, offset)
            pos += length
        else:
            pending.append(raw[pos])
            pos += 1

    _emit_literals(out, pending)
    return out


def encode_timings(timings: Sequence[int], *, compress: bool = True) -> str:
    """Encode raw IR timings as a base64 Tuya ``key_code``.

    Compression matters: the message is pushed to the blaster in 56-byte chunks
    over Zigbee before any IR is emitted, so halving it halves the round trips.
    Pass ``compress=False`` for the literal-only form the reference encoder emits.
    """
    if not timings:
        raise ValueError("timings must be a non-empty sequence")

    raw = bytearray()
    for index, value in enumerate(timings):
        magnitude = abs(value)
        if magnitude > 0xFFFF:
            raise ValueError(f"timing out of range at index {index}: {value}")
        raw += magnitude.to_bytes(2, "little")

    literal = bytearray()
    _emit_literals(literal, bytearray(raw))
    if not compress:
        return base64.b64encode(bytes(literal)).decode()

    packed = _compress(bytes(raw))
    # Never pay for compression that did not help.
    return base64.b64encode(bytes(min(packed, literal, key=len))).decode()


def _decompress(data: bytes) -> bytearray:
    """Expand the device's literal/back-reference stream.

    A malformed or truncated stream stops decoding and keeps what was recovered,
    matching the reference implementation: a partial capture is still useful.
    """
    out = bytearray()
    pos = 0
    while pos < len(data):
        header = data[pos]
        pos += 1
        block_type = header >> 5

        if block_type == 0:
            length = (header & 0x1F) + 1
            chunk = data[pos : pos + length]
            out += chunk
            pos += length
            if len(chunk) < length:
                break
            continue

        length = block_type + 2
        if length == 9:
            while pos < len(data) and data[pos] == 0xFF:
                length += 255
                pos += 1
            if pos >= len(data):
                break
            length += data[pos]
            pos += 1

        if pos >= len(data):
            break
        offset = (((header & 0x1F) << 8) | data[pos]) + 1
        pos += 1
        if offset > len(out):
            break
        for _ in range(length):
            out.append(out[-offset])

    return out


def decode_key_code(key_code: str) -> list[int]:
    """Decode a base64 Tuya ``key_code`` into signed pulse/space timings."""
    raw = _decompress(base64.b64decode(key_code))

    return [
        value if index % 2 == 0 else -value
        for index, value in enumerate(
            int.from_bytes(raw[offset : offset + 2], "little")
            for offset in range(0, len(raw) - 1, 2)
        )
    ]
