"""Tests for KOF."""

from unittest import mock

import zigpy.device
import zigpy.endpoint
import zigpy.quirks
from zigpy.zcl import foundation
import zigpy.zdo.types as zdo_t

import zhaquirks
import zhaquirks.kof.kof_mr101z

zhaquirks.setup()

Default_Response = foundation.GENERAL_COMMANDS[
    foundation.GeneralCommand.Default_Response
].schema


async def test_kof_no_reply():
    """Test KOF No reply."""

    class TestCluster(
        zhaquirks.kof.kof_mr101z.NoReplyMixin, zigpy.quirks.CustomCluster
    ):
        """Test Cluster Class."""

        cluster_id = 0x1234
        void_input_commands = {0x02}
        server_commands = {
            0x01: foundation.ZCLCommandDef("noop", {}, False),
            0x02: foundation.ZCLCommandDef("noop_noreply", {}, False),
        }
        client_commands = {}

    ep = mock.AsyncMock()
    ep.device.get_sequence = mock.MagicMock(return_value=4)

    cluster = TestCluster(ep)

    async def mock_req(*args, expect_reply=True, **kwargs):
        if not expect_reply:
            return None
        else:
            return mock.sentinel.real_response

    ep.request.side_effect = mock_req

    rsp = await cluster.noop()
    assert rsp is mock.sentinel.real_response

    rsp = await cluster.noop(expect_reply=True)
    assert rsp is mock.sentinel.real_response

    rsp = await cluster.noop_noreply()
    assert rsp == Default_Response(
        command_id=TestCluster.commands_by_name["noop_noreply"].id,
        status=zdo_t.Status.SUCCESS,
    )

    rsp = await cluster.noop_noreply(expect_reply=False)
    assert rsp is None

    rsp = await cluster.noop_noreply(expect_reply=True)
    assert rsp is mock.sentinel.real_response
