"""Tests for direct Lutron Aurora manufacturer notifications."""

import asyncio
import json
from pathlib import Path

import pytest
from zha.application import Platform
from zha.application.gateway import Gateway
from zha.application.helpers import CoordinatorConfiguration, ZHAConfiguration, ZHAData
from zha.zigbee.endpoint import Endpoint
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import ROTARY_KNOB, ROTATED
from zhaquirks.lutron.aurora import AuroraCluster

PRESS = bytes.fromhex("1d0b1012000100003000210000")
RELEASE = bytes.fromhex("1d0b1013000100003002210300")
CW = bytes.fromhex("1d0b1006001400013001293800216e00292000216e00293800219001")
CCW = bytes.fromhex("1d0b101400140001300129e4ff216e0029f0ff216e0029e4ff219001")
ROTATION_CAPTURES = json.loads(
    (Path(__file__).parent / "fixtures/lutron_aurora_rotation.json").read_text()
)["captures"]


class EventListener:
    """Collect the public event interface consumed by ZHA."""

    def __init__(self):
        """Initialize captured events."""
        self.events = []
        self.normalized_events = []
        self.unique_id = "08-07-06-05-04-03-02-01"
        self.zha_events = []

    def emit_zha_event(self, event):
        """Receive the event forwarded by a real ZHA endpoint."""
        self.zha_events.append(event)

    def zha_send_event(self, command, args):
        """Receive a quirk event."""
        if command == "aurora_notification":
            self.events.append((command, args))
        else:
            self.normalized_events.append((command, args))


@pytest.fixture
def aurora(zigpy_device_from_v2_quirk):
    """Apply the quirk to the observed Aurora cluster set."""
    device = zigpy_device_from_v2_quirk(
        "Lutron",
        "Z3-1BRL",
        firmware_version=0xC12,
        cluster_ids={
            1: {
                Basic.cluster_id: ClusterType.Server,
                PowerConfiguration.cluster_id: ClusterType.Server,
                Identify.cluster_id: ClusterType.Server,
                LightLink.cluster_id: ClusterType.Server,
                AuroraCluster.cluster_id: ClusterType.Server,
                Groups.cluster_id: ClusterType.Client,
                OnOff.cluster_id: ClusterType.Client,
                LevelControl.cluster_id: ClusterType.Client,
                Ota.cluster_id: ClusterType.Client,
            }
        },
    )
    # Both directions exist for Identify and LightLink on the real device.
    device.endpoints[1].add_output_cluster(Identify.cluster_id)
    device.endpoints[1].add_output_cluster(LightLink.cluster_id)
    device.endpoints[1].profile_id = 0x0104
    device.endpoints[1].device_type = 0x0820
    cluster = device.endpoints[1].in_clusters[AuroraCluster.cluster_id]
    assert isinstance(cluster, AuroraCluster)
    listener = EventListener()
    cluster.add_listener(listener)
    return cluster, listener


def feed(cluster, frame):
    """Pass a wire frame through the normal cluster deserialization path."""
    header, payload = cluster.deserialize(frame)
    cluster.handle_message(header, payload)


def dial_frame(sequence, fields):
    """Encode numeric rotary fields into a manufacturer notification."""
    payload = bytes.fromhex("14000130") + bytes([fields[0]])
    for type_id, value in zip([0x29, 0x21, 0x29, 0x21, 0x29, 0x21], fields[1:]):
        payload += bytes([type_id]) + value.to_bytes(
            2, "little", signed=type_id == 0x29
        )
    return bytes.fromhex("1d0b10") + bytes([sequence, 0]) + payload


def test_press_start_is_normalized_immediately(aurora):
    """A native down report starts a press without waiting for release."""
    cluster, listener = aurora
    feed(cluster, PRESS)
    assert listener.normalized_events == [
        ("press_start", {"control_id": 1, "sequence": 18, "duration_seconds": 0.0})
    ]


def test_hold_start_repeats_and_release_use_native_duration(aurora):
    """The first native hold starts a long press; later holds remain distinct."""
    cluster, listener = aurora
    frames = [
        "1d0b1039000100003000210000",
        "1d0b103a000100003001210c00",
        "1d0b103b000100003001211400",
        "1d0b103c000100003001211c00",
        "1d0b103d000100003003211d00",
    ]
    for frame in frames:
        feed(cluster, bytes.fromhex(frame))
    assert [
        (name, data["duration_seconds"]) for name, data in listener.normalized_events
    ] == [
        ("press_start", 0),
        ("long_press_start", 1.2),
        ("hold", 2),
        ("hold", 2.8),
        ("long_press_end", 2.9),
    ]
    feed(cluster, PRESS[:3] + bytes([62]) + PRESS[4:])
    feed(cluster, RELEASE[:3] + bytes([63]) + RELEASE[4:])
    assert [name for name, _ in listener.normalized_events[-2:]] == [
        "press_start",
        "press_end",
    ]


@pytest.mark.parametrize(
    ("frame", "counts", "degrees", "direction"),
    [(CW, 32, 11.52, "clockwise"), (CCW, -16, -5.76, "counterclockwise")],
)
def test_fresh_rotation_uses_cumulative_count_not_adjusted_amount(
    aurora, frame, counts, degrees, direction
):
    """A fresh window reports physical counts scaled at 1000 per revolution."""
    cluster, listener = aurora
    feed(cluster, frame)
    assert listener.normalized_events == [
        (
            "rotation",
            {
                "control_id": 20,
                "sequence": frame[3],
                "phase": "start",
                "delta_counts": counts,
                "delta_degrees": degrees,
                "direction": direction,
            },
        )
    ]


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        ([1, 56, 110, 32, 110, 56, 400], [2, 40, 400, 96, 510, 40, 400], 64),
        ([1, 168, 117, 96, 117, 168, 400], [1, -196, 377, -16, 377, -196, 400], -112),
        ([2, 176, 400, 320, 65487, 176, 400], [1, -168, 131, 224, 131, -168, 400], -96),
        ([1, -308, 1450, 16, 1450, -308, 400], [1, 28, 2010, -80, 2010, 28, 400], -96),
    ],
    ids=["compensation", "reversal", "timer_rollover", "adjusted_sign_disagrees"],
)
def test_recorded_continuations_use_counter_difference(
    aurora, previous, current, expected
):
    """Native start phases and adjusted amounts do not replace counter deltas."""
    cluster, listener = aurora
    feed(cluster, dial_frame(10, previous))
    feed(cluster, dial_frame(11, current))
    name, event = listener.normalized_events[-1]
    assert name == "rotation"
    assert event["sequence"] == 11
    assert event["delta_counts"] == expected


def test_button_down_is_immediate_and_lossless(aurora):
    """A button-down frame is forwarded without waiting for release."""
    cluster, listener = aurora
    feed(cluster, PRESS)
    assert listener.events == [
        (
            "aurora_notification",
            {
                "frame_hex": "1d0b1012000100003000210000",
                "payload_hex": "0100003000210000",
                "manufacturer_code": 4107,
                "command_id": 0,
                "sequence": 18,
                "control_id": 1,
                "control_type": 0,
                "prefix_hex": "010000",
                "event_code": 0,
                "fields": [
                    {"offset": 3, "type": 48, "value": 0},
                    {"offset": 5, "type": 33, "value": 0},
                ],
            },
        )
    ]


@pytest.mark.parametrize(
    ("previous", "current", "counts", "direction"),
    [
        (32752, -32768, 16, "clockwise"),
        (-32768, 32752, -16, "counterclockwise"),
        (16, 16, 0, None),
    ],
)
def test_counter_rollover_and_zero_net_movement(
    aurora, previous, current, counts, direction
):
    """Signed 16-bit counter wrap is movement; a zero delta has no direction."""
    cluster, listener = aurora
    feed(cluster, dial_frame(1, [2, 16, 400, previous, 500, 16, 400]))
    feed(cluster, dial_frame(2, [2, 16, 400, current, 900, 16, 400]))
    name, event = listener.normalized_events[-1]
    assert name == "rotation"
    assert event["delta_counts"] == counts
    assert event["direction"] == direction


@pytest.mark.parametrize(
    ("frame", "values"),
    [
        (CW, [1, 56, 110, 32, 110, 56, 400]),
        (CCW, [1, -28, 110, -16, 110, -28, 400]),
    ],
)
def test_rotation_preserves_every_numeric_field(aurora, frame, values):
    """Signed movement and trailing numeric data are preserved without scaling."""
    cluster, listener = aurora
    feed(cluster, frame)
    assert len(listener.events) == 1
    command, event = listener.events[0]
    assert command == "aurora_notification"
    assert event["control_id"] == 0x14
    assert event["event_code"] == 1
    assert "rotation" not in event
    assert [f["value"] for f in event["fields"]] == values
    assert [f["offset"] for f in event["fields"]] == [3, 5, 8, 11, 14, 17, 20]
    assert [f["type"] for f in event["fields"]] == [
        0x30,
        0x29,
        0x21,
        0x29,
        0x21,
        0x29,
        0x21,
    ]
    assert event["frame_hex"] == frame.hex()
    assert "speed" not in event


def test_control_id_uses_both_bytes(aurora):
    """An unknown control 257 must not be mistaken for button 1."""
    cluster, listener = aurora
    feed(cluster, PRESS[:5] + bytes.fromhex("0101003000210000"))
    assert listener.events[0][1]["control_id"] == 257
    assert listener.normalized_events == []


@pytest.mark.parametrize("frame", [CW, CCW])
def test_single_rotation_trigger_matches_both_directions(aurora, frame):
    """One rotation trigger receives signed movement in either direction."""
    cluster, listener = aurora
    endpoint = Endpoint.new(cluster.endpoint, listener)
    feed(cluster, frame)
    triggers = cluster.endpoint.device.device_automation_triggers
    assert {key for key in triggers if key[0] == ROTATED} == {(ROTATED, ROTARY_KNOB)}
    trigger = triggers[(ROTATED, ROTARY_KNOB)]
    event = listener.zha_events[-1]
    for key, value in trigger.items():
        if isinstance(value, dict):
            assert value.items() <= event[key].items()
        else:
            assert value == event[key]
    endpoint.on_remove()


def test_continuation_without_baseline_is_explicit_and_recovers(aurora):
    """Startup in mid-turn does not report the accumulated position as a delta."""
    cluster, listener = aurora
    feed(cluster, dial_frame(1, [2, 16, 400, 160, 510, 16, 400]))
    assert listener.normalized_events == [
        (
            "rotation_unavailable",
            {"control_id": 20, "sequence": 1, "reason": "missing_baseline"},
        )
    ]
    feed(cluster, dial_frame(2, [2, 16, 400, 176, 910, 16, 400]))
    assert listener.normalized_events[-1][1]["delta_counts"] == 16


def test_duplicate_is_preserved_but_does_not_double_movement(aurora):
    """An exact retransmission stays raw without another normalized action."""
    cluster, listener = aurora
    feed(cluster, CW)
    feed(cluster, CW)
    assert len(listener.events) == 2
    assert len(listener.normalized_events) == 1
    # A new notification with identical values is a separate physical nudge.
    feed(cluster, CW[:3] + bytes([7]) + CW[4:])
    assert [data["delta_counts"] for _, data in listener.normalized_events] == [32, 32]


@pytest.mark.parametrize("sequence", [5, 8], ids=["out_of_order", "missing_report"])
def test_discontinuous_sequence_never_invents_movement(aurora, sequence):
    """A stream discontinuity requires a new baseline before movement resumes."""
    cluster, listener = aurora
    feed(cluster, CW)
    feed(cluster, dial_frame(sequence, [2, 16, 400, 96, 510, 16, 400]))
    assert listener.normalized_events[-1][0] == "rotation_unavailable"
    following = 7 if sequence == 5 else 9
    feed(cluster, dial_frame(following, [2, 16, 400, 112, 910, 16, 400]))
    if sequence == 5:
        assert listener.normalized_events[-1][0] == "rotation_unavailable"
        feed(cluster, dial_frame(8, [2, 16, 400, 128, 1310, 16, 400]))
    assert listener.normalized_events[-1][0] == "rotation"
    assert listener.normalized_events[-1][1]["delta_counts"] == 16


@pytest.mark.parametrize(
    "variant", ["truncated", "extended", "unknown_phase", "different_samples"]
)
def test_unrecognized_dial_report_invalidates_baseline(aurora, variant):
    """An unsupported notification is retained and cannot hide a counter restart."""
    cluster, listener = aurora
    feed(cluster, CW)
    fields = [2, 16, 400, 48, 510, 16, 400]
    if variant == "unknown_phase":
        fields[0] = 3
    if variant == "different_samples":
        fields[5] = 32
    frame = dial_frame(7, fields)
    if variant == "truncated":
        frame = frame[:-1]
    if variant == "extended":
        frame += b"\xff"
    feed(cluster, frame)
    assert listener.events[-1][1]["frame_hex"] == frame.hex()
    assert listener.normalized_events[-1][0] == "rotation_unavailable"
    feed(cluster, dial_frame(8, [2, 16, 400, 64, 910, 16, 400]))
    assert listener.normalized_events[-1][1]["reason"] == "missing_baseline"
    feed(cluster, dial_frame(9, [2, 16, 400, 80, 1310, 16, 400]))
    assert listener.normalized_events[-1][1]["delta_counts"] == 16


@pytest.mark.parametrize("payload", [b"", b"\x14", b"\x14\x00"])
def test_unidentifiable_notification_cannot_hide_counter_reset(aurora, payload):
    """A report too short to identify must also invalidate the rotary baseline."""
    cluster, listener = aurora
    feed(cluster, CW)
    feed(cluster, bytes.fromhex("1d0b100700") + payload)
    feed(cluster, dial_frame(8, [2, 16, 400, 96, 510, 16, 400]))
    assert listener.normalized_events[-1] == (
        "rotation_unavailable",
        {"control_id": 20, "sequence": 8, "reason": "missing_baseline"},
    )


def test_half_counter_range_has_no_unique_direction(aurora):
    """Exactly half a counter turn cannot choose between two signed differences."""
    cluster, listener = aurora
    feed(cluster, dial_frame(1, [2, 16, 400, 0, 510, 16, 400]))
    feed(cluster, dial_frame(2, [2, 16, 400, -32768, 910, 16, 400]))
    assert listener.normalized_events[-1][0] == "rotation_unavailable"
    assert listener.normalized_events[-1][1]["reason"] == "ambiguous_counter_wrap"


def test_whole_capture_is_one_event_per_notification(aurora):
    """All 32 captured frames survive, in order, including the release value."""
    cluster, listener = aurora
    capture = json.loads(
        (Path(__file__).parent / "fixtures/lutron_aurora_c12.json").read_text()
    )
    for index, frame in enumerate(capture["frames"], start=1):
        feed(cluster, bytes.fromhex(frame))
        assert len(listener.events) == index
    events = [event for command, event in listener.events]
    assert len(events) == 32
    assert [event["frame_hex"] for event in events] == capture["frames"]
    assert [event["control_id"] for event in events] == [20] * 12 + [1] * 2 + [20] * 18
    assert [event["event_code"] for event in events] == [1] + [2] * 11 + [0, 2] + [
        1
    ] + [2] * 17
    assert events[13]["fields"][-1] == {"offset": 5, "type": 0x21, "value": 3}
    assert [field["value"] for field in events[-1]["fields"]] == [
        2,
        -96,
        400,
        -1152,
        7290,
        -96,
        400,
    ]
    assert all("undecoded_hex" not in event for event in events)
    json.dumps(events)


@pytest.mark.parametrize(
    "capture", ROTATION_CAPTURES, ids=lambda capture: capture["name"]
)
def test_physical_trials_through_cluster_dispatch(aurora, capture):
    """Replay complete trials against frozen, timing-derived movement interpretations."""
    cluster, listener = aurora
    for frame in capture["frames"]:
        feed(cluster, bytes.fromhex(frame["frame"]))
    assert [data["frame_hex"] for _, data in listener.events] == [
        frame["frame"] for frame in capture["frames"]
    ]
    assert not any(
        name == "rotation_unavailable" for name, _ in listener.normalized_events
    )
    assert [
        data["delta_counts"]
        for name, data in listener.normalized_events
        if name == "rotation"
    ] == [
        frame["delta_counts"] for frame in capture["frames"] if "delta_counts" in frame
    ]
    json.dumps(listener.normalized_events)


@pytest.mark.asyncio
async def test_fast_clicks_stay_separate(aurora):
    """Three quick clicks yield six immediate events and no delayed synthesis."""
    cluster, listener = aurora
    for index, frame in enumerate([PRESS, RELEASE] * 3, start=1):
        feed(cluster, frame[:3] + bytes([index]) + frame[4:])
        assert len(listener.events) == index
        assert len(listener.normalized_events) == index
    assert [event["event_code"] for command, event in listener.events] == [0, 2] * 3
    assert [command for command, _ in listener.normalized_events] == [
        "press_start",
        "press_end",
    ] * 3
    await asyncio.sleep(0.35)
    assert len(listener.events) == 6
    assert len(listener.normalized_events) == 6


def test_new_press_recovers_after_missing_release(aurora):
    """A new native press starts another hold without synthesizing a lost release."""
    cluster, listener = aurora
    for frame in (
        "1d0b1001000100003000210000",
        "1d0b1002000100003001210c00",
        "1d0b1003000100003000210000",
        "1d0b1004000100003001210c00",
    ):
        feed(cluster, bytes.fromhex(frame))
    assert [command for command, _ in listener.normalized_events] == [
        "press_start",
        "long_press_start",
        "press_start",
        "long_press_start",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x01",
        bytes.fromhex("010000"),
        bytes.fromhex("0100003099"),
        bytes.fromhex("9900003000210000"),
    ],
)
def test_unknown_and_short_notifications_are_preserved(aurora, payload):
    """Unknown controls/codes and short payloads remain available to callers."""
    cluster, listener = aurora
    frame = PRESS[:5] + payload
    feed(cluster, frame)
    assert len(listener.events) == 1
    assert listener.events[0][1]["frame_hex"] == frame.hex()
    assert listener.events[0][1]["payload_hex"] == payload.hex()


@pytest.mark.parametrize("tail", ["ff1122", "29aa"])
def test_unknown_or_truncated_typed_tail_is_retained(aurora, tail):
    """An unrecognized or incomplete value stops decoding without losing bytes."""
    cluster, listener = aurora
    frame = PRESS + bytes.fromhex(tail)
    feed(cluster, frame)
    event = listener.events[0][1]
    assert event["frame_hex"] == frame.hex()
    assert event["undecoded_hex"] == tail
    assert event["fields"] == [
        {"offset": 3, "type": 0x30, "value": 0},
        {"offset": 5, "type": 0x21, "value": 0},
    ]


@pytest.mark.parametrize("header", ["1d44111200", "1d0b101299", "150b101200"])
def test_unrelated_cluster_commands_do_not_emit_notifications(aurora, header):
    """Other manufacturers, commands and directions are left to the base cluster."""
    cluster, listener = aurora
    feed(cluster, bytes.fromhex(header) + PRESS[5:])
    assert listener.events == []


async def test_quirk_discovers_button_and_dial_event_entities(aurora):
    """A resolved quirk discovers input entities without any HA-specific code."""
    cluster, _ = aurora
    gateway = Gateway(
        ZHAData(
            config=ZHAConfiguration(
                coordinator_configuration=CoordinatorConfiguration(path="/dev/fake")
            )
        )
    )
    gateway.application_controller = cluster.endpoint.device.application
    device = gateway.get_or_create_device(cluster.endpoint.device)
    entities = list(device.discover_entities())
    events = [e for e in entities if e.PLATFORM == Platform.EVENT]
    assert {e.fallback_name for e in events} == {"Button", "Dial"}
    button = next(e for e in events if e.fallback_name == "Button")
    dial = next(e for e in events if e.fallback_name == "Dial")
    assert button.device_class == "button"
    assert button.event_types == [
        "press_start",
        "long_press_start",
        "hold",
        "press_end",
        "long_press_end",
    ]
    assert dial.event_types == ["rotation", "rotation_unavailable"]
    assert len({e.unique_id for e in events}) == len(events)
    assert any(e.PLATFORM == Platform.SENSOR for e in entities)


@pytest.fixture
async def input_entities(aurora):
    """Discover and attach the quirk's input entities through the ZHA gateway."""
    cluster, _ = aurora
    gateway = Gateway(
        ZHAData(
            config=ZHAConfiguration(
                coordinator_configuration=CoordinatorConfiguration(path="/dev/fake")
            )
        )
    )
    gateway.application_controller = cluster.endpoint.device.application
    device = gateway.get_or_create_device(cluster.endpoint.device)
    entities = {
        e.fallback_name: e
        for e in device.discover_entities()
        if e.PLATFORM == Platform.EVENT
    }
    for entity in entities.values():
        entity.on_add()
    yield entities
    for entity in entities.values():
        await entity.on_remove()


def test_button_entity_delivers_native_phases_and_repeated_holds(
    aurora, input_entities
):
    """Button events keep immediate phases and durations while the dial is idle."""
    cluster, _ = aurora
    button_events = []
    dial_events = []
    input_entities["Button"].on_event("event_triggered", button_events.append)
    input_entities["Dial"].on_event("event_triggered", dial_events.append)
    for frame in [
        "1d0b1039000100003000210000",
        "1d0b103a000100003001210c00",
        "1d0b103b000100003001211400",
        "1d0b103c000100003001211c00",
        "1d0b103d000100003003211d00",
        "1d0b103e000100003000210000",
        "1d0b103f000100003002210200",
    ]:
        feed(cluster, bytes.fromhex(frame))
    assert [
        (e.triggered.event_type, e.triggered.event_attributes["duration_seconds"])
        for e in button_events
    ] == [
        ("press_start", 0),
        ("long_press_start", 1.2),
        ("hold", 2.0),
        ("hold", 2.8),
        ("long_press_end", 2.9),
        ("press_start", 0),
        ("press_end", 0.2),
    ]
    assert not dial_events


def test_dial_entity_delivers_signed_movement_and_unavailable_reports(
    aurora, input_entities
):
    """Dial events preserve amounts and omit amounts when a report is lost."""
    cluster, _ = aurora
    events = []
    button_events = []
    input_entities["Dial"].on_event("event_triggered", events.append)
    input_entities["Button"].on_event("event_triggered", button_events.append)
    for seq, frame in [(1, CW), (2, CW), (3, CCW), (5, CW)]:
        feed(cluster, frame[:3] + bytes([seq]) + frame[4:])
    assert [e.triggered.event_type for e in events] == [
        "rotation",
        "rotation",
        "rotation",
        "rotation_unavailable",
    ]
    assert [e.triggered.event_attributes["delta_degrees"] for e in events[:3]] == [
        11.52,
        11.52,
        -5.76,
    ]
    assert events[-1].triggered.event_attributes == {
        "control_id": 20,
        "sequence": 5,
        "reason": "sequence_gap",
    }
    assert not button_events


async def test_removed_input_entity_stops_listening(aurora, input_entities):
    """Removing and re-adding an entity must not leak or duplicate listeners."""
    cluster, _ = aurora
    button = input_entities["Button"]
    events = []
    button.on_event("event_triggered", events.append)
    await button.on_remove()
    feed(cluster, PRESS)
    assert not events
    button.on_add()
    feed(cluster, RELEASE)
    assert len(events) == 1
    assert events[0].triggered.event_type == "press_end"
