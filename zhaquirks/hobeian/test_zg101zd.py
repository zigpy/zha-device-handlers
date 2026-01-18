"""Tests for HOBEIAN ZG-101ZD rotary dimmer knob quirk."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.hobeian.zg101zd import HobeianOnOffCluster


@pytest.fixture
def hobeian_cluster():
    """Create a HobeianOnOffCluster instance for testing."""
    cluster = HobeianOnOffCluster(mock.MagicMock())
    cluster.listener_event = mock.MagicMock()
    return cluster


def _make_hdr(command_id: int) -> foundation.ZCLHeader:
    """Create a ZCL header with the given command ID."""
    return foundation.ZCLHeader(
        frame_control=foundation.FrameControl(
            frame_type=foundation.FrameType.CLUSTER_COMMAND,
            is_manufacturer_specific=False,
            direction=foundation.Direction.Client_to_Server,
            disable_default_response=True,
        ),
        tsn=1,
        command_id=command_id,
    )


class TestHobeianOnOffCluster:
    """Tests for HobeianOnOffCluster."""

    def test_rotation_step_right(self, hobeian_cluster):
        """Test rotation step right command (0x03)."""
        hdr = _make_hdr(HobeianOnOffCluster.ROTATION_STEP_RIGHT_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [])

        hobeian_cluster.listener_event.assert_called_once_with(
            "zha_send_event",
            "step_with_on_off",
            {"step_mode": 0, "step_size": 13, "transition_time": 1},
        )

    def test_rotation_step_left(self, hobeian_cluster):
        """Test rotation step left command (0x04)."""
        hdr = _make_hdr(HobeianOnOffCluster.ROTATION_STEP_LEFT_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [])

        hobeian_cluster.listener_event.assert_called_once_with(
            "zha_send_event",
            "step_with_on_off",
            {"step_mode": 1, "step_size": 13, "transition_time": 1},
        )

    def test_rotation_direction_right(self, hobeian_cluster):
        """Test rotation direction right command (0xFC with 0x00)."""
        hdr = _make_hdr(HobeianOnOffCluster.ROTATION_DIRECTION_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [b"\x00"])

        hobeian_cluster.listener_event.assert_called_once_with(
            "zha_send_event",
            "rotation_direction",
            {"direction": "right", "direction_raw": 0},
        )

    def test_rotation_direction_left(self, hobeian_cluster):
        """Test rotation direction left command (0xFC with 0x01)."""
        hdr = _make_hdr(HobeianOnOffCluster.ROTATION_DIRECTION_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [b"\x01"])

        hobeian_cluster.listener_event.assert_called_once_with(
            "zha_send_event",
            "rotation_direction",
            {"direction": "left", "direction_raw": 1},
        )

    def test_rotation_direction_int_arg(self, hobeian_cluster):
        """Test rotation direction with int argument."""
        hdr = _make_hdr(HobeianOnOffCluster.ROTATION_DIRECTION_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [0])

        hobeian_cluster.listener_event.assert_called_once_with(
            "zha_send_event",
            "rotation_direction",
            {"direction": "right", "direction_raw": 0},
        )

    def test_rotation_direction_empty_args(self, hobeian_cluster):
        """Test rotation direction with empty args defaults to right."""
        hdr = _make_hdr(HobeianOnOffCluster.ROTATION_DIRECTION_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [])

        hobeian_cluster.listener_event.assert_not_called()

    def test_toggle(self, hobeian_cluster):
        """Test toggle command (0x02)."""
        hdr = _make_hdr(HobeianOnOffCluster.TOGGLE_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [])

        hobeian_cluster.listener_event.assert_called_once_with(
            "zha_send_event",
            "toggle",
            {},
        )

    def test_button_press_indicator_ignored(self, hobeian_cluster):
        """Test button press indicator (0xFD) is ignored."""
        hdr = _make_hdr(HobeianOnOffCluster.BUTTON_PRESS_INDICATOR_CMD)
        hobeian_cluster.handle_cluster_request(hdr, [])

        hobeian_cluster.listener_event.assert_not_called()
