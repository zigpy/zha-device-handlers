"""Tests for the Tuya IR key_code codec."""

import base64

import pytest

from zhaquirks.tuya.ir_codec import decode_key_code, encode_timings

# Learned by a physical ZS06 from a Panasonic-family washlet remote. Every one of
# them uses back-references, which our own encoder emits differently, so these
# are what cover the decoder on real device output.
REAL_CAPTURES = {
    "stop": "CV8N3gbOAc4BiAHgCwMHHQXOAc4BiAHgAQNAAeADD+AFCwMdBYgBQBPAB0AL4AsDwB9AB0ADwCPgAwvAE0AHwBfgBwfgAxtAC+ADA8ArQBMBY9NA5wGIAUAL4AsDBx0FzgHOAYgB4B0DAc4BwC8JHQWIAf0BiAHOAUADQAFAB+ABA0AfQA8CHQXOYAMDzgGIAUADAx0FiAFAB+AHA8AX4AUHQAHgARNAC+ADAwsdBYgB/QGIAc4BiAE=",  # codespell:ignore
    "wash and dry": "DVQNzQaCAb4BggHyAYIBwAdAC0ADByMFvgG+AYIBQAtABwC+YAFAB+ALAwG+AcAvBSMFggG+AcADQAHAC4AHwB9ABwUjBb4BvgFAB4AD4AULQAFAEwe+ASMFvgG+AUALCIIBIwWCAYIBviABQAWAA0ATAL4gAUAHQAMAvmABgAcBhdDgAecAvuAAAUALgAPgBy8DvgGCAYADQAFAC4ABgAkBggHAL0AHwRvABwG+AeABA0AfQA9AB0AD4AULA74BIwWAAwG+AYAbAL4gAUATAb4BQAsBggHgAQtAAQGCAUADBCMFggG+IAEBIwWAAwu+AYIBvgGCAb4BvgE=",  # codespell:ignore
    "nozzle down": "BlEN0AZ+AbpgAUAHBX4B7gF+AUAHALogAQceBboBugF+AUATgAMAuiABgAtAB4ADQAFACw26AR4FfgHuAX4BugF+AeAFB8ABgBcFHgW6AboBgAfAC8AvBB4FfgG6YAEBfgFAE0ADgBPABwq6AR4FugG6AX4BumABA1Ycz9PAx0ATwANAAUALAboBwC9ASwG6AUADQAFAB+ADA0ABQA8FugEeBX4BwCvgBQfAAYAXBR4FugG6AUAHgANAC8ADQBMAumABQAeAA4ATwAcRugEeBboBugF+AboBugG6AVYc",  # codespell:ignore
    "nozzle up": "DEQN9gamAaYBcgHnAaYgAYAHAecBgAcBJgVAB+ADAwCm4AABBOcBcgGm4AABQAsFcgEmBaYBgBcCcgGmIAFAC4ADAKZgAQHnAYAPgCcBpgFAB0ADA6YBcgFAD0ABQA8BJgVADwNyAaYBQANAAQFyAUATAyYFpgFAAYAHBHIB5wGmIAEDUxy90MDH4AcBAnIBpiABQC8D5wFyAcADAKbgAAEEcgHnAaYgAQJyAaZgAQlyAecBcgEmBXIBQAcC5wGmYAEF5wFyAaYBQAPgAQFAEwMmBaYBQAFABwMmBXIBQBMApiABBecBpgEmBYADBecBcgHnAUAHAKZgAcAXQAEBJgVAGwlyAecBpgHnAVMc",  # codespell:ignore
    "water/dry up": "C1UN6wZ8AegBfAG3AeAJAwMkBbcBgAECfAG3IAHAJ+AFBwG3AcAPwC+ABwF8AUAX4AMDwBPAHwEkBcADCLcBtwF8AegBtyABBXwBJAV8AcALALdgAQF8AUATALdgAUAHAXwB4AEPwAHAE4AHgD+AAQH80YDnAbcBQANAAUAH4AEDgEsBfAGAAwG3AUA7QA0B6AFABQF8AYAHQAEBfAFAAwMkBbcBQBNABwS3AXwBt+AEAQF8AUAbQAdAH0ALQAcBJAVABwJ8AbdgAUAHAXwBQA9AHwC3IAGABwF8AUATALdgAUAHAXwBQA/AG0APQAMDJAW3AUABDyQFfAHoAXwBtwG3AbcBtwE=",  # codespell:ignore
    "water/dry down": "B0UN6QaCAc4B4AUDA/gBggFAEwchBc4BzgGCAeAfAwMhBYIBQCvAB0AL4AsDwB9AB8AD4AsnwBNAI8ALwAfgBxPgAw/gAwtALwFRzeAB58DbwAdAHwchBc4BzgGCAeABA0AB4AMP4AULAyEFggFAE8AHQAvgAwPAW4AfAc4BQAfAAwHOAUADAs4BgiABQAXgAQMBzgFAIwHOAeAFA+ABE0AB4AMP4AULA84BzgE=",  # codespell:ignore
}

# The remote's Kaseikyo leader: a ~3456us mark and ~1728us space, with slack for
# receiver jitter.
LEADER_MARK = (3300, 3550)
LEADER_SPACE = (1650, 1850)

# A subset of cases produced by running zigbee-herdsman-converters' TypeScript
# encodeTuyaTimings and decodeTuyaTimings over a pseudo-random corpus. The full
# corpus is 1500 cases (1 MB); these keep up to two of the shortest of every way a decode
# can go (literal, short and extended back-references, 0xFF length chains, and
# each truncated or malformed ending) plus the encoder's edges.
# Encoding: (timings, expected key_code, or None where the reference rejects it).
# fmt: off
REFERENCE_ENCODE_CASES = [
    ([66271], None),
    ([50860, -65699], None),
    ([36076], "AeyM"),
    ([38739, -46826, 39775, -28400, 20212, -60392, 26277, -62905, 55663, -55714, 49872, -23727, 307, -1211, 12467, -19804], "H1OX6rZfm/Bu9E7o66VmufVv2aLZ0MKvXDMBuwSzMFxN"),
    ([28570, -57124, 19448, -310, 42051, -13855, 57975, -14193, 2931, -52688, 49609, -39754, 60895, -32864, 63550, -4015, 26267], "H5pvJN/4SzYBQ6QfNnficTdzC9DNycFKm9/tYIA++K8PAZtm"),
    ([17302, -14580, 17302, -49102, 36032, -61850, 31189, -47443, 1563, -15152, 10192, -47355, 53174, -50, 10138, -24890, 62270, -576, 34154, -15626, 36170, -27206, 15732, -46273, 56547, -25928, 12977, -5404, 52889, -10326, 28315, -33989, 38622, -52970, 51761, -54784, 7377, -31104, 15874, -63022, 37670, -34159, 7310, -52234, 31681, -6423, 12702, -695, 28285, -49836], "H5ZD9DiWQ86/wIya8dV5U7kbBjA70Cf7uLbPMgCaJzphHz7zQAJqhQo9So1GanQ9wbTj3EhlsTIcFZnOViibbsWEH96W6s4xygDW0RyAeQI+LvYmk2+FjhwKzMF7FxmeMbcCA31urMI="),
]
# Decoding: (key_code, expected timings).
REFERENCE_DECODE_CASES = [
    ("6hEoIaiV", []),
    ("9RyxPPO6", []),
    ("E9RE/c91YGAmr/a5+fuXtjooenhx7v+wX5oEIlu0NLn8EPr/epzoQqWJ4Q==", [17620, -53245, 24693, -9824, 63151, -63929, 38907, -15030, 31272, -29048]),
    ("AuXdmP9TneG2", [56805]),
    ("A0QplprtDtek0JL/TV3kUr8Er+kV37RcLIh3W4q4zZrwNcdMtIAbzf18g63bE7rIqw==", [10564, -39574]),
    ("AkWcG62IBl+9qhM0St/iygfMdQ==", [40005]),
    ("ecrM", []),
    ("tnc9", []),
    ("EkTIzpY5c+UjnNZTEY8v6hdlPcMdSClBcHJlVfxac6qakB2vbJVf8SOqO2h5DYmMOfO44P8ZIQ8a+ZMyZXCy3KLP3nes1qlsHDZvWVpCe9I4tKctICVZcQRoRFCGaxO8V8byvMo4", [51268, -38606, 29497, -9189, 54940, -4435, 12175, -6122, 15717, -18627, 16681, -29296, 21861, -23292, 43635, -37018, 44829, -38252, 61791, -43555, 26683, -3449, 35977, -62265, 6072, -15717, 18627, -16681, 29296, -21861, 23292, -43635, 37018, -44829, 38252, -61791, 43555, -26683, 3449, -35977, 62265, -6072, 15717, -18627, 16681, -29296, 21861, -23292, 43635, -37018, 44829, -38252, 61791, -43555, 26683, -3449, 35977, -62265, 6072, -15717, 18627, -16681, 29296, -21861, 23292, -43635, 37018, -44829, 38252, -61791, 43555, -26683, 3449, -35977, 62265, -6072, 15717, -18627, 16681, -29296, 21861, -23292, 43635, -37018, 44829, -38252, 61791, -43555, 26683, -3449, 35977, -62265, 6072, -15717, 18627, -16681, 29296, -21861, 23292, -43635, 37018, -44829, 38252, -61791, 43555, -26683, 3449, -35977, 62265, -6072, 15717, -18627, 16681, -29296, 21861, -23292, 43635, -37018, 44829, -38252, 61791, -43555, 26683, -3449, 35977, -62265, 6072, -15717, 18627, -16681, 29296, -21861, 23292, -43635, 37018, -44829, 38252, -61791, 43555, -26683, 3449, -35977, 62265, -6072, 15717, -18627, 16681, -29296, 21861, -23292, 43635, -37018, 44829, -38252, 61791, -43555, 26683, -3449, 35977, -62265, 6072, -15717, 18627, -16681, 29296, -21861, 23292, -43635, 37018, -63770, 12947, -28773, 56498, -53154, 30686, -54956, 27817, -28470, 23129, -31554, 14546, -42932, 8237, -22821, 1137, -17512, 34384, -4971, 22460, -62150, 51900]),
    ("BaLgrrRangyuxSUJIeLDCHE7xwXDoAdAD+D/DgDBBwHg3wzWzoIgjtgT1ET9z3Vg", [57506, -46254, 40538, -50606, 2341, -57889, 2243, -15217, 1479, -58051, 2243, -15217, 1479, -57889, 2243, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 2056, -2056, 57312, -52950, 8322, -55438, 54291, -64836, 30159]),
    ("Afh0", [29944]),
    ("AejJ", [51688]),
    ("Amk9S6AB", [15721, -15691, 15691, -15691, 15691]),
    ("BpG15DTm9zRgAw==", [46481, -13540, 63462, -13364, 63462, -13364]),
    ("+0Y=", []),
    ("93g=", []),
    ("Dj5RUDA2xLlR3uC0PBpz2bI=", [20798, -12368, 50230, -20921, 57566, -15540, 29466]),
    ("ow==", []),
    ("QA==", []),
    ("Gz8=", []),
    ("CwA=", []),
]
# fmt: on


def test_encode_timings_emits_one_literal_block():
    """Timings become little-endian uint16 in a length-prefixed literal block."""
    # 100 -> 64 00, 200 -> C8 00; header is (4 bytes - 1) & 0x1F == 3.
    assert (
        encode_timings([100, 200])
        == base64.b64encode(bytes([0x03, 0x64, 0x00, 0xC8, 0x00])).decode()
    )


def test_encode_timings_strips_pulse_space_sign():
    """Signed pulse/space timings encode identically to their magnitudes."""
    assert encode_timings([100, -200]) == encode_timings([100, 200])


def test_encode_timings_splits_runs_longer_than_32_bytes():
    """Literal bytes are emitted in blocks of at most 32.

    Checked on the uncompressed path: a repetitive run like this is exactly what
    the compressor collapses into a back-reference.
    """
    # 17 timings -> 34 raw bytes -> a full 32-byte block plus a 2-byte block.
    raw_pair = bytes([0x01, 0x00])
    expected = bytes([0x1F]) + raw_pair * 16 + bytes([0x01]) + raw_pair
    assert base64.b64decode(encode_timings([1] * 17, compress=False)) == expected


def test_encode_timings_rejects_empty_input():
    """An empty timing list is not a sendable IR command."""
    with pytest.raises(ValueError, match="non-empty"):
        encode_timings([])


def test_encode_timings_rejects_values_above_uint16():
    """Timings must fit the protocol's little-endian uint16 fields."""
    with pytest.raises(ValueError, match="index 1"):
        encode_timings([100, 0x10000])


def test_decode_key_code_applies_alternating_pulse_space_signs():
    """Decoded byte pairs alternate pulse (positive) and space (negative)."""
    key_code = base64.b64encode(bytes([0x03, 0x64, 0x00, 0xC8, 0x00])).decode()
    assert decode_key_code(key_code) == [100, -200]


def test_decode_key_code_returns_empty_for_empty_payload():
    """An empty payload decodes to no timings rather than raising."""
    assert decode_key_code("") == []


def test_decode_key_code_ignores_trailing_unpaired_byte():
    """A dangling byte cannot form a uint16 and is discarded."""
    key_code = base64.b64encode(bytes([0x02, 0x64, 0x00, 0xFF])).decode()
    assert decode_key_code(key_code) == [100]


def test_decode_key_code_expands_back_reference():
    """A back-reference block copies earlier bytes forward."""
    # literal 64 00 C8 00, then blockType 1 (length 3) at distance 3 (offset 4).
    key_code = base64.b64encode(
        bytes([0x03, 0x64, 0x00, 0xC8, 0x00, 0x20, 0x03])
    ).decode()
    assert decode_key_code(key_code) == [100, -200, 100]


def test_decode_key_code_back_reference_may_overlap_its_own_output():
    """Copying more bytes than the offset repeats the window, LZ77 style."""
    # blockType 7 means length 9 plus an extension byte (here 0), offset 4.
    key_code = base64.b64encode(
        bytes([0x03, 0x64, 0x00, 0xC8, 0x00, 0xE0, 0x00, 0x03])
    ).decode()
    assert decode_key_code(key_code) == [100, -200, 100, -200, 100, -200]


def test_decode_key_code_accumulates_ff_extended_lengths():
    """Each 0xFF in the extension chain adds 255 to the copy length."""
    # length = 9 + 255 + 2 = 266, offset 1, so the last byte repeats.
    key_code = base64.b64encode(
        bytes([0x01, 0x64, 0x00, 0xE0, 0xFF, 0x02, 0x00])
    ).decode()
    timings = decode_key_code(key_code)
    assert len(timings) == 134
    assert timings[0] == 100


def test_decode_key_code_stops_at_truncated_length_chain():
    """A 0xFF length chain running off the end yields what was decoded."""
    key_code = base64.b64encode(bytes([0x01, 0x64, 0x00, 0xE0, 0xFF])).decode()
    assert decode_key_code(key_code) == [100]


def test_compression_chains_long_back_references():
    """A run longer than 9 + 255 bytes is encoded with a 0xFF length chain."""
    timings = [9000, -4500] + [560, -560] * 100

    packed = base64.b64decode(encode_timings(timings))

    assert 0xFF in packed
    assert decode_key_code(encode_timings(timings)) == timings


def test_decode_key_code_returns_partial_result_for_truncated_stream():
    """A back-reference missing its distance byte yields what was decoded."""
    key_code = base64.b64encode(bytes([0x03, 0x64, 0x00, 0xC8, 0x00, 0x20])).decode()
    assert decode_key_code(key_code) == [100, -200]


def test_round_trip_preserves_alternating_timings():
    """Timings already in pulse/space form survive encode then decode."""
    nec_leader = [9000, -4500, 560, -560, 560, -1690]
    assert decode_key_code(encode_timings(nec_leader)) == nec_leader


def test_compressed_encoding_round_trips():
    """Compression must not change what the timings mean."""
    timings = [9000, -4500] + [560, -560, 560, -1690] * 20

    assert decode_key_code(encode_timings(timings)) == timings


def test_compression_beats_literal_only_on_repetitive_signals():
    """Real IR is highly repetitive, which is what back-references exploit."""
    timings = [9000, -4500] + [560, -560, 560, -1690] * 20

    compressed = encode_timings(timings)
    literal = encode_timings(timings, compress=False)

    assert len(compressed) < len(literal) / 2


def test_literal_only_encoding_is_still_available():
    """The uncompressed path stays byte-identical to the reference encoder."""
    literal = base64.b64decode(encode_timings([1] * 17, compress=False))

    assert literal == bytes([0x1F]) + bytes([1, 0]) * 16 + bytes([0x01, 1, 0])


def test_compression_never_exceeds_the_literal_encoding():
    """Incompressible input must not be inflated by trying."""
    timings = [i * 7 + 1 for i in range(1, 60)]

    assert len(encode_timings(timings)) <= len(encode_timings(timings, compress=False))


@pytest.mark.parametrize("key_code", REAL_CAPTURES.values(), ids=REAL_CAPTURES)
def test_real_capture_decodes(key_code):
    """Test a learned code decodes to a plausible signal that fits the format."""
    timings = decode_key_code(key_code)

    mark, space = timings[:2]
    assert LEADER_MARK[0] <= mark <= LEADER_MARK[1]
    assert -LEADER_SPACE[1] <= space <= -LEADER_SPACE[0]
    assert all(abs(timing) <= 0xFFFF for timing in timings)
    # Back-references make the decoded signal larger than the payload.
    assert len(timings) * 2 > len(base64.b64decode(key_code))


@pytest.mark.parametrize("key_code", REAL_CAPTURES.values(), ids=REAL_CAPTURES)
def test_real_capture_round_trips(key_code):
    """Test a learned code survives decoding and re-encoding, as a resend does."""
    timings = decode_key_code(key_code)

    assert decode_key_code(encode_timings(timings)) == timings


@pytest.mark.parametrize(("timings", "expected"), REFERENCE_ENCODE_CASES)
def test_encode_matches_reference(timings, expected):
    """Test uncompressed encoding is byte-identical to the reference encoder."""
    if expected is None:
        with pytest.raises(ValueError):
            encode_timings(timings, compress=False)
        return

    assert encode_timings(timings, compress=False) == expected
    # The compressed form differs in bytes but must mean the same thing.
    assert decode_key_code(encode_timings(timings)) == decode_key_code(expected)


@pytest.mark.parametrize(("key_code", "expected"), REFERENCE_DECODE_CASES)
def test_decode_matches_reference(key_code, expected):
    """Test decoding agrees with the reference on valid and malformed streams."""
    assert decode_key_code(key_code) == expected
