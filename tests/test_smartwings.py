"""Tests for Smartwings."""

from unittest import mock

import pytest
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.smartwings.wm25lz import WM25LBlinds


@pytest.mark.parametrize("quirk", (WM25LBlinds,))
async def test_smartwings_inverted_commands(zigpy_device_from_quirk, quirk):
    """Test that the Smartwings WM25/L-Z blind quirk inverts the up/down commands."""

    device = zigpy_device_from_quirk(quirk)
    device.request = mock.AsyncMock()

    covering_cluster = device.endpoints[1].window_covering

    close_command_id = WindowCovering.commands_by_name["down_close"].id
    open_command_id = WindowCovering.commands_by_name["up_open"].id

    # close cover and check if the command is inverted
    await covering_cluster.command(close_command_id)
    assert len(device.request.mock_calls) == 1
    assert device.request.mock_calls[0].kwargs["data"] == b"\x01\x01\x00"

    # open cover and check if the command is inverted
    await covering_cluster.command(open_command_id)
    assert len(device.request.mock_calls) == 2
    assert device.request.mock_calls[1].kwargs["data"] == b"\x01\x02\x01"
