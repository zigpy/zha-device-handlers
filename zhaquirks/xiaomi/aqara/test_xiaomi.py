"""Tests for xiaomi."""
from unittest import mock
from unittest.mock import call

from zigpy.device import Device

from .ctrl_neutral1 import CtrlNeutral1


def test_ctrl_neutral():
    sec = 8
    ieee = 0
    nwk = 1234
    data = b"\x01\x08\x01"
    # data = b'\x00\x10\x02"\xff \x12'
    cluster = 6
    src_ep = 1
    dst_ep = 2

    app = mock.MagicMock()
    app.get_sequence = mock.MagicMock(return_value=sec)
    rep = Device(app, ieee, nwk)
    rep.add_endpoint(1)
    rep.add_endpoint(2)
    dev = CtrlNeutral1(app, ieee, nwk, rep)
    dev.request = mock.MagicMock()
    dev[2].in_clusters[cluster].command(1)

    assert dev.request.call_args == call(None, cluster, src_ep, dst_ep, sec, data, expect_reply=True)
