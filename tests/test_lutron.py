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

from zhaquirks.const import COMMAND
from zhaquirks.lutron.aurora import (
    AURORA_MODEL,
    CLOCKWISE,
    COUNTERCLOCKWISE,
    DIAL_ROTATE_CCW,
    DIAL_ROTATE_CW,
    DIAL_ROTATED,
    LUTRON,
    AuroraRemoteCluster,
)
from zhaquirks.philips import PhilipsRemoteCluster

# Raw ZCL frames (header + payload) captured from a Z3-1BRL on firmware
# 0x00000c12. Manufacturer code 0x100B, command 0x00, server -> client.
AURORA_PRESS = bytes.fromhex("1d0b1030000100003000210000")
AURORA_SHORT_RELEASE = bytes.fromhex("1d0b1031000100003002210100")
AURORA_DIAL_START_CCW = bytes.fromhex(
    "1d0b102b001400013001293cff21ba0929700221ba09293cff219001"
)
AURORA_DIAL_CCW_FAST = bytes.fromhex(
    "1d0b102f0014000130022920ff21900129f0fe2122102920ff219001"
)
AURORA_DIAL_CW_FAST = bytes.fromhex(
    "1d0b102900140001300229700021900129c00221ae06297000219001"
)
AURORA_DIAL_CW_SLOW = bytes.fromhex(
    "1d0b102a00140001300229200021940229e002214209292000219001"
)
# Synthetic variants of the slow frame: rotation 10 (a single step) and 0.
AURORA_DIAL_CW_STEP = bytes.fromhex(
    "1d0b102a001400013002290a0021940229e002214209290a00219001"
)
AURORA_DIAL_ZERO = bytes.fromhex(
    "1d0b102a00140001300229000021940229e002214209290000219001"
)

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


@pytest.mark.parametrize(
    ("frame", "action", "expected"),
    [
        (
            AURORA_DIAL_START_CCW,
            DIAL_ROTATE_CCW,
            {"rotation": -196, "direction": "ccw", "speed": "fast", "phase": "start"},
        ),
        (
            AURORA_DIAL_CCW_FAST,
            DIAL_ROTATE_CCW,
            {"rotation": -224, "direction": "ccw", "speed": "fast", "phase": "rotate"},
        ),
        (
            AURORA_DIAL_CW_FAST,
            DIAL_ROTATE_CW,
            {"rotation": 112, "direction": "cw", "speed": "fast", "phase": "rotate"},
        ),
        (
            AURORA_DIAL_CW_SLOW,
            DIAL_ROTATE_CW,
            {"rotation": 32, "direction": "cw", "speed": "slow", "phase": "rotate"},
        ),
        (
            AURORA_DIAL_CW_STEP,
            DIAL_ROTATE_CW,
            {"rotation": 10, "direction": "cw", "speed": "step", "phase": "rotate"},
        ),
    ],
)
def test_aurora_dial_rotation(aurora, frame, action, expected):
    """Dial frames become dial_rotate_cw/ccw with a signed rotation."""
    cluster, listener = aurora
    _feed(cluster, frame)

    listener.zha_send_event.assert_called_once()
    called_action, event_args = listener.zha_send_event.call_args.args
    assert called_action == action
    for key, value in expected.items():
        assert event_args[key] == value
    assert event_args["command_id"] == 0
    assert event_args["args"][0] == 0x14


def test_aurora_dial_zero_rotation_ignored(aurora):
    """A dial frame with zero rotation does not emit an event."""
    cluster, listener = aurora
    _feed(cluster, AURORA_DIAL_ZERO)
    listener.zha_send_event.assert_not_called()


def test_aurora_device_automation_triggers(zigpy_device_from_v2_quirk):
    """Button and dial triggers are exposed for the device automation UI."""
    device = zigpy_device_from_v2_quirk(
        LUTRON, AURORA_MODEL, cluster_ids=AURORA_CLUSTERS
    )
    triggers = device.device_automation_triggers
    assert triggers[(DIAL_ROTATED, CLOCKWISE)] == {COMMAND: DIAL_ROTATE_CW}
    assert triggers[(DIAL_ROTATED, COUNTERCLOCKWISE)] == {COMMAND: DIAL_ROTATE_CCW}
    assert ("remote_button_short_press", "knob") in triggers
    assert triggers[("remote_button_short_press", "knob")] == {COMMAND: "knob_press"}
