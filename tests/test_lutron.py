"""Tests for Lutron quirks."""

from unittest import mock

import pytest
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

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    ENDPOINT_ID,
    LEFT,
    RIGHT,
    ROTARY_KNOB,
    ROTATED,
)
from zhaquirks.lutron.aurora import (
    AURORA_MODEL,
    DIAL_ROTATE_CCW,
    DIAL_ROTATE_CW,
    LUTRON,
    AuroraRemoteCluster,
)
from zhaquirks.philips import PhilipsRemoteCluster

# Raw ZCL frames (header + payload) captured from a Z3-1BRL on firmware
# 0x00000c12. Manufacturer code 0x100B, command 0x00, server -> client.
AURORA_PRESS = bytes.fromhex("1d0b1030000100003000210000")
AURORA_SHORT_RELEASE = bytes.fromhex("1d0b1031000100003002210100")
# Dial frames, in the order the device sent them (TSN 0x29, 0x2a, 0x2b, 0x2f).
# Each carries an adjusted amount and a cumulative counter:
#   CW_FAST    phase 2, adjusted  112, counter  704
#   CW_SLOW    phase 2, adjusted   32, counter  736
#   START_CCW  phase 1, adjusted -196, counter  624
#   CCW_FAST   phase 2, adjusted -224, counter -272
AURORA_DIAL_CW_FAST = bytes.fromhex(
    "1d0b102900140001300229700021900129c00221ae06297000219001"
)
AURORA_DIAL_CW_SLOW = bytes.fromhex(
    "1d0b102a00140001300229200021940229e002214209292000219001"
)
AURORA_DIAL_START_CCW = bytes.fromhex(
    "1d0b102b001400013001293cff21ba0929700221ba09293cff219001"
)
AURORA_DIAL_CCW_FAST = bytes.fromhex(
    "1d0b102f0014000130022920ff21900129f0fe2122102920ff219001"
)
# First frame of a twist after a pause, where the counter restarts: phase 1,
# adjusted -28, counter -16 (4 * adjusted == 7 * counter).
AURORA_DIAL_RESET_CCW = bytes.fromhex(
    "1d0b101400140001300129e4ff216e0029f0ff216e0029e4ff219001"
)
# Synthetic: the dial's button id on a frame with the 8-byte button layout.
AURORA_DIAL_SHORT_FRAME = bytes.fromhex("1d0b1030001400003000210000")

AURORA_CLUSTERS = {
    1: {
        Basic.cluster_id: ClusterType.Server,
        PowerConfiguration.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        LightLink.cluster_id: ClusterType.Server,
        AuroraRemoteCluster.cluster_id: ClusterType.Server,
        Groups.cluster_id: ClusterType.Client,
        OnOff.cluster_id: ClusterType.Client,
        LevelControl.cluster_id: ClusterType.Client,
        Ota.cluster_id: ClusterType.Client,
    }
}


class ManuallyFiredButtonPressQueue:
    """Button press queue that fires on demand instead of after a delay."""

    def __init__(self):
        """Init."""
        self._callback = None
        self._click_counter = 0

    def press(self, callback):
        """Record a press."""
        self._callback = callback
        self._click_counter += 1

    def fire(self):
        """Fire the callback with the accumulated click count."""
        if self._callback is not None:
            self._callback(self._click_counter)
        self._callback = None
        self._click_counter = 0


@pytest.fixture
def aurora(zigpy_device_from_v2_quirk):
    """Return the quirked Aurora remote cluster with a manual press queue."""
    device = zigpy_device_from_v2_quirk(
        LUTRON, AURORA_MODEL, cluster_ids=AURORA_CLUSTERS
    )
    cluster = device.endpoints[1].philips_remote_cluster
    assert isinstance(cluster, AuroraRemoteCluster)
    cluster.button_press_queue = {
        k: ManuallyFiredButtonPressQueue() for k in cluster.BUTTONS
    }
    listener = mock.MagicMock()
    cluster.add_listener(listener)
    return cluster, listener


def _feed(cluster, frame: bytes) -> None:
    """Deserialize a raw ZCL frame and hand it to the cluster."""
    hdr, args = cluster.deserialize(frame)
    assert hdr.manufacturer == 0x100B
    assert hdr.command_id == 0
    cluster.handle_cluster_request(hdr, args)


def test_aurora_quirk_applies(aurora):
    """The v2 quirk replaces the generic 0xFC00 cluster."""
    cluster, _ = aurora
    assert cluster.cluster_id == PhilipsRemoteCluster.cluster_id
    assert cluster.ep_attribute == "philips_remote_cluster"


def test_aurora_knob_short_press(aurora):
    """A press + short release becomes knob_press and knob_short_release."""
    cluster, listener = aurora
    _feed(cluster, AURORA_PRESS)
    _feed(cluster, AURORA_SHORT_RELEASE)
    for queue in cluster.button_press_queue.values():
        queue.fire()

    actions = [call.args[0] for call in listener.zha_send_event.call_args_list]
    assert actions == ["knob_press", "knob_short_release"]
    press_args = listener.zha_send_event.call_args_list[0].args[1]
    assert press_args["button"] == "knob"
    assert press_args["press_type"] == "press"


def test_aurora_knob_double_press(aurora):
    """Two quick presses become a single knob_double_press."""
    cluster, listener = aurora
    for frame in (
        AURORA_PRESS,
        AURORA_SHORT_RELEASE,
        AURORA_PRESS,
        AURORA_SHORT_RELEASE,
    ):
        _feed(cluster, frame)
    for queue in cluster.button_press_queue.values():
        queue.fire()

    actions = [call.args[0] for call in listener.zha_send_event.call_args_list]
    assert actions == ["knob_double_press"]


def _dial_events(listener) -> list[tuple[str, dict]]:
    """Return the (action, event_args) pairs sent so far."""
    return [call.args for call in listener.zha_send_event.call_args_list]


def test_aurora_knob_event_args_unchanged(aurora):
    """Button events carry the five Philips fields, without the dial's extras."""
    cluster, listener = aurora
    _feed(cluster, AURORA_PRESS)
    _feed(cluster, AURORA_SHORT_RELEASE)
    for queue in cluster.button_press_queue.values():
        queue.fire()

    for _, event_args in _dial_events(listener):
        assert len(event_args["args"]) == 5
        assert None not in list(event_args["args"])


@pytest.mark.parametrize(
    ("previous", "frame", "action", "expected"),
    [
        # Mid-twist: the counter moved 704 -> 736.
        (
            AURORA_DIAL_CW_FAST,
            AURORA_DIAL_CW_SLOW,
            DIAL_ROTATE_CW,
            {"rotation": 32, "direction": "cw", "speed": "slow", "phase": "rotate"},
        ),
        # Reversal: the counter moved 736 -> 624. The frame's own adjusted
        # amount (-196) overstates this by 7/4.
        (
            AURORA_DIAL_CW_SLOW,
            AURORA_DIAL_START_CCW,
            DIAL_ROTATE_CCW,
            {"rotation": -112, "direction": "ccw", "speed": "fast", "phase": "start"},
        ),
        # Three frames were not captured in between: the counter difference
        # still covers the whole movement, 624 -> -272.
        (
            AURORA_DIAL_START_CCW,
            AURORA_DIAL_CCW_FAST,
            DIAL_ROTATE_CCW,
            {"rotation": -896, "direction": "ccw", "speed": "fast", "phase": "rotate"},
        ),
        # A restarted counter is the movement itself, whatever came before.
        (
            AURORA_DIAL_CW_SLOW,
            AURORA_DIAL_RESET_CCW,
            DIAL_ROTATE_CCW,
            {"rotation": -16, "direction": "ccw", "speed": "step", "phase": "start"},
        ),
        (
            None,
            AURORA_DIAL_RESET_CCW,
            DIAL_ROTATE_CCW,
            {"rotation": -16, "direction": "ccw", "speed": "step", "phase": "start"},
        ),
    ],
)
def test_aurora_dial_rotation(aurora, previous, frame, action, expected):
    """Dial frames become dial_rotate_cw/ccw with the counter's movement."""
    cluster, listener = aurora
    if previous is not None:
        _feed(cluster, previous)
        listener.reset_mock()
    _feed(cluster, frame)

    listener.zha_send_event.assert_called_once()
    called_action, event_args = listener.zha_send_event.call_args.args
    assert called_action == action
    for key, value in expected.items():
        assert event_args[key] == value
    assert event_args["command_id"] == 0
    assert event_args["args"][0] == 0x14


def test_aurora_dial_twist_sums_to_counter(aurora):
    """Over a twist the rotations add up to the counter's net movement."""
    cluster, listener = aurora
    for frame in (
        AURORA_DIAL_CW_FAST,
        AURORA_DIAL_CW_SLOW,
        AURORA_DIAL_START_CCW,
        AURORA_DIAL_CCW_FAST,
    ):
        _feed(cluster, frame)

    rotations = [args["rotation"] for _, args in _dial_events(listener)]
    assert rotations == [32, -112, -896]
    assert sum(rotations) == -272 - 704


def test_aurora_dial_without_baseline_ignored(aurora):
    """A mid-twist frame with nothing to compare against only sets the baseline."""
    cluster, listener = aurora
    _feed(cluster, AURORA_DIAL_CW_FAST)
    listener.zha_send_event.assert_not_called()


def test_aurora_dial_repeated_frame_ignored(aurora):
    """A frame that does not move the counter does not emit an event."""
    cluster, listener = aurora
    _feed(cluster, AURORA_DIAL_CW_FAST)
    _feed(cluster, AURORA_DIAL_CW_SLOW)
    _feed(cluster, AURORA_DIAL_CW_SLOW)
    listener.zha_send_event.assert_called_once()


def test_aurora_dial_unknown_layout_ignored(aurora):
    """A dial frame without the counter is not read as a rotation."""
    cluster, listener = aurora
    _feed(cluster, AURORA_DIAL_SHORT_FRAME)
    listener.zha_send_event.assert_not_called()


def test_aurora_device_automation_triggers(zigpy_device_from_v2_quirk):
    """Button and dial triggers are exposed for the device automation UI."""
    device = zigpy_device_from_v2_quirk(
        LUTRON, AURORA_MODEL, cluster_ids=AURORA_CLUSTERS
    )
    triggers = device.device_automation_triggers
    assert triggers[(ROTATED, RIGHT)] == {COMMAND: DIAL_ROTATE_CW}
    assert triggers[(ROTATED, LEFT)] == {COMMAND: DIAL_ROTATE_CCW}
    assert triggers[("remote_button_short_press", ROTARY_KNOB)] == {
        COMMAND: "knob_press"
    }
    # Older firmware reports the button and the dial through LevelControl.
    assert triggers[(ROTATED, ROTARY_KNOB)] == {
        COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
        CLUSTER_ID: LevelControl.cluster_id,
        ENDPOINT_ID: 1,
    }
