"""Tests for KOF."""
from unittest import mock

import zigpy.device
import zigpy.endpoint
import zigpy.quirks

import zhaquirks.kof.kof_mr101z


def test_kof_no_reply():
    """Test KOF No reply."""

    class TestCluster(
        zhaquirks.kof.kof_mr101z.NoReplyMixin, zigpy.quirks.CustomCluster
    ):
        """Test Cluster Class."""

        cluster_id = 0x1234
        void_input_commands = [0x0002]
        server_commands = {
            0x0001: ("noop", (), False),
            0x0002: ("noop_noreply", (), False),
        }
        client_commands = {}

    end_point = mock.MagicMock()
    cluster = TestCluster(end_point)

    cluster.command(0x0001)
    end_point.request.assert_called_with(
        mock.ANY, mock.ANY, mock.ANY, expect_reply=True, command_id=mock.ANY
    )
    end_point.reset_mock()

    cluster.command(0x0001, expect_reply=False)
    end_point.request.assert_called_with(
        mock.ANY, mock.ANY, mock.ANY, expect_reply=False, command_id=mock.ANY
    )
    end_point.reset_mock()

    cluster.command(0x0002)
    end_point.request.assert_called_with(
        mock.ANY, mock.ANY, mock.ANY, expect_reply=False, command_id=mock.ANY
    )
    end_point.reset_mock()

    cluster.command(0x0002, expect_reply=True)
    end_point.request.assert_called_with(
        mock.ANY, mock.ANY, mock.ANY, expect_reply=True, command_id=mock.ANY
    )
    end_point.reset_mock()
