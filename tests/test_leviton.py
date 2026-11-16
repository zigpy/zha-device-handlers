"""Tests for Leviton dimmers."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl
import zigpy.zdo.types as zdo_t

import zhaquirks
from zhaquirks.leviton.dimmer import LevitonLevelControl

zhaquirks.setup()

Default_Response = foundation.GENERAL_COMMANDS[
    foundation.GeneralCommand.Default_Response
].schema


@pytest.mark.parametrize(
    "manufacturer, model",
    [
        ("LEVITON", "ZK700-D0W"),
        ("Leviton Inc", "LU107"),
    ],
)
async def test_leviton_dimmer_level_control(
    zigpy_device_from_v2_quirk, manufacturer, model
):
    """Test Leviton dimmer replaces LevelControl with NoReplyMixin variant."""

    device = zigpy_device_from_v2_quirk(manufacturer, model)
    level_cluster = device.endpoints[1].in_clusters[LevelControl.cluster_id]

    assert isinstance(level_cluster, LevitonLevelControl)

    # All LevelControl server commands should be in void_input_commands
    for cmd in LevelControl.commands_by_name.values():
        assert cmd.id in level_cluster.void_input_commands

    # Verify a representative command uses expect_reply=False via NoReplyMixin
    ep = level_cluster.endpoint
    ep.request = mock.AsyncMock(return_value=None)

    rsp = await level_cluster.command(
        LevelControl.ServerCommandDefs.move_to_level.id, 128, 10
    )

    assert ep.request.call_count == 1
    assert ep.request.call_args.kwargs["expect_reply"] is False

    assert rsp == Default_Response(
        command_id=LevelControl.ServerCommandDefs.move_to_level.id,
        status=zdo_t.Status.SUCCESS,
    )
