"""Tests for Ikea Starkvind quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, LevelControl, PowerConfiguration
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.clusters.measurement import PM25

from tests.common import ClusterListener
import zhaquirks
from zhaquirks import LevelControlWithMoveDirection
from zhaquirks.const import (
    COMMAND,
    COMMAND_MOVE_DOWN_RELEASE,
    COMMAND_MOVE_UP_RELEASE,
    DIM_DOWN,
    DIM_UP,
    LONG_RELEASE,
)
from zhaquirks.ikea import IKEA
from zhaquirks.ikea.fivebtnremote import (
    IkeaTradfriRemote1,
    IkeaTradfriRemote2,
    IkeaTradfriRemote3,
    IkeaTradfriRemote4,
    IkeaTradfriRemote5,
)
import zhaquirks.ikea.starkvind
from zhaquirks.ikea.starkvind import IkeaAirpurifier
from zhaquirks.ikea.twobtnremote import (
    IkeaRodretRemote2Btn,
    IkeaRodretRemote2BtnNew,
    IkeaTradfriRemote2Btn,
    IkeaTradfriRemote2BtnZLL,
)

zhaquirks.setup()


@pytest.fixture
def starkvind_device(zigpy_device_from_v2_quirk):
    """Return a quirked STARKVIND air purifier."""
    return zigpy_device_from_v2_quirk(
        IKEA,
        "STARKVIND Air purifier",
        cluster_ids={
            1: {
                Fan.cluster_id: ClusterType.Server,
                IkeaAirpurifier.cluster_id: ClusterType.Server,
                PM25.cluster_id: ClusterType.Client,
            }
        },
    )


def test_starkvind_replaced_clusters(starkvind_device):
    """Test the unimplemented Fan cluster is removed and no PM25 cluster is added."""

    endpoint = starkvind_device.endpoints[1]
    assert isinstance(endpoint.in_clusters[IkeaAirpurifier.cluster_id], IkeaAirpurifier)

    # the device's `Fan` cluster is not implemented, so it must not create an entity
    assert Fan.cluster_id not in endpoint.in_clusters

    # PM2.5 is read from the manufacturer specific cluster, so no virtual server
    # side `PM25` cluster is added anymore. The device's own client side cluster
    # is left alone, as it never created an entity to begin with.
    assert PM25.cluster_id not in endpoint.in_clusters
    assert PM25.cluster_id in endpoint.out_clusters


@pytest.mark.parametrize("attribute", ["fan_speed", "fan_mode"])
@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),  # off
        (1, 1),  # auto
        (10, 2),
        (20, 4),
        (50, 10),
    ],
)
def test_fan_speed_mode_update(starkvind_device, attribute, value, expected):
    """Test reading the fan speed and mode."""

    ikea_cluster = starkvind_device.endpoints[1].in_clusters[IkeaAirpurifier.cluster_id]
    ikea_listener = ClusterListener(ikea_cluster)

    attr_id = getattr(IkeaAirpurifier.AttributeDefs, attribute).id

    ikea_cluster.update_attribute(attr_id, value)
    assert len(ikea_listener.attribute_updates) == 1
    assert ikea_listener.attribute_updates[0] == (attr_id, expected)


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, 0),  # off
        (1, 1),  # auto
        (2, 10),
        (4, 20),
        (10, 50),
        (11, 11),  # out of range, written as-is
    ],
)
async def test_fan_mode_write(starkvind_device, value, expected):
    """Test writing the fan mode scales it back up to the device's range."""

    ikea_cluster = starkvind_device.endpoints[1].in_clusters[IkeaAirpurifier.cluster_id]

    write_mock = mock.AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )
    with mock.patch.object(ikea_cluster, "_write_attributes", write_mock):
        # other attributes written in the same call are passed through untouched
        await ikea_cluster.write_attributes({"fan_mode": value, "child_lock": 1})

    written = {
        attr.attrid: attr.value.value for attr in write_mock.mock_calls[0].args[0]
    }
    assert written == {
        IkeaAirpurifier.AttributeDefs.fan_mode.id: expected,
        IkeaAirpurifier.AttributeDefs.child_lock.id: 1,
    }


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
@pytest.mark.parametrize(
    "firmware, pct_device, pct_correct, expected_pct_updates, expect_log_warning",
    (
        ("1.0.024", 50, 100, 2, False),  # old firmware, doubling
        ("2.3.075", 50, 100, 2, False),  # old firmware, doubling
        ("2.4.5", 50, 50, 1, False),  # new firmware, no doubling
        ("3.0.0", 50, 50, 1, False),  # new firmware, no doubling
        ("24.4.5", 50, 50, 1, False),  # new firmware, no doubling
        ("invalid_fw_string_1", 50, 50, 1, False),  # treated as new, no doubling
        ("invalid.fw.string.2", 50, 50, 1, True),  # treated as new, no doubling + log
        ("", 50, 50, 1, False),  # treated as new fw, no doubling
    ),
)
async def test_double_power_config_firmware(
    caplog,
    zigpy_device_from_quirk,
    firmware,
    pct_device,
    pct_correct,
    expected_pct_updates,
    expect_log_warning,
):
    """Test battery percentage remaining is doubled for old firmware."""

    device = zigpy_device_from_quirk(zhaquirks.ikea.fivebtnremote.IkeaTradfriRemote1)

    basic_cluster = device.endpoints[1].basic
    ClusterListener(basic_cluster)
    sw_build_id = Basic.AttributeDefs.sw_build_id.id

    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)
    battery_pct_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    # fake read response for attributes: return plug_read argument for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.SUCCESS, foundation.TypeValue(None, firmware)
            )
            for attr in attributes
        ]
        return (records,)

    p1 = mock.patch.object(power_cluster, "create_catching_task")
    p2 = mock.patch.object(
        basic_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )

    with p1 as mock_task, p2 as request_mock:
        # update battery percentage with no firmware in attr cache, check pct not doubled for now
        power_cluster.update_attribute(battery_pct_id, pct_device)
        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0] == (battery_pct_id, pct_device)

        # but also check that sw_build_id read is requested in the background for next update
        assert mock_task.call_count == 1
        await mock_task.call_args[0][0]  # await coroutine to read attribute
        assert request_mock.call_count == 1  # verify request to read sw_build_id
        assert request_mock.mock_calls[0][1][0][0] == sw_build_id

        # battery pct is updated again when the attribute read returned old firmware, check pct doubled only once then
        # if firmware turned out to be new or still unknown, do not update battery pct again, as it's correct already
        assert len(power_listener.attribute_updates) == expected_pct_updates
        if expected_pct_updates > 1:
            assert power_listener.attribute_updates[1] == (battery_pct_id, pct_correct)

        # reset mocks for testing when sw_build_id is known next
        mock_task.reset_mock()
        request_mock.reset_mock()
        power_listener = ClusterListener(power_cluster)

        # update battery percentage with firmware in attr cache, check pct doubled if needed
        basic_cluster.update_attribute(sw_build_id, firmware)
        power_cluster.update_attribute(battery_pct_id, pct_device)
        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0] == (battery_pct_id, pct_correct)

        # check no attribute reads were requested when sw_build_id is known
        assert mock_task.call_count == 0
        assert request_mock.call_count == 0

        # make sure a call to bind() always reads sw_build_id (e.g. on join or to refresh when repaired/reconfigured)
        await power_cluster.bind()
        assert request_mock.call_count == 1
        assert request_mock.mock_calls[0][1][0][0] == sw_build_id

        # check log output if we expect a warning
        if expect_log_warning:
            assert f"sw_build_id is not a number: {firmware} for device" in caplog.text


@pytest.mark.parametrize(
    "move_cmd,move_mode,stop_cmd,expected_event",
    [
        (
            None,
            None,
            LevelControl.ServerCommandDefs.stop_with_on_off.id,
            None,
        ),  # stop_with_on_off without prior move
        (
            LevelControl.ServerCommandDefs.move_with_on_off.id,
            0,
            LevelControl.ServerCommandDefs.stop_with_on_off.id,
            COMMAND_MOVE_UP_RELEASE,
        ),  # move up + stop_with_on_off (0x07)
        (
            LevelControl.ServerCommandDefs.move_with_on_off.id,
            0,
            LevelControl.ServerCommandDefs.stop.id,
            COMMAND_MOVE_UP_RELEASE,
        ),  # move up + stop (0x03)
        (
            LevelControl.ServerCommandDefs.move.id,
            1,
            LevelControl.ServerCommandDefs.stop.id,
            COMMAND_MOVE_DOWN_RELEASE,
        ),  # move down + stop (0x03)
        (
            LevelControl.ServerCommandDefs.move.id,
            1,
            LevelControl.ServerCommandDefs.stop_with_on_off.id,
            COMMAND_MOVE_DOWN_RELEASE,
        ),  # move down + stop_with_on_off (0x07)
    ],
)
async def test_ikea_level_control_direction_tracking(
    zigpy_device_from_v2_quirk, move_cmd, move_mode, stop_cmd, expected_event
):
    """Test that a dim hold release is attributed to the button that was held."""
    device = zigpy_device_from_v2_quirk(
        IKEA,
        "09B9",
        cluster_ids={1: {LevelControl.cluster_id: ClusterType.Server}},
    )

    level_cluster = device.endpoints[1].in_clusters[LevelControl.cluster_id]
    assert isinstance(level_cluster, LevelControlWithMoveDirection)

    listener = mock.MagicMock()
    level_cluster.add_listener(listener)

    # Send move command if provided
    if move_cmd is not None:
        hdr_move = foundation.ZCLHeader.cluster(tsn=1, command_id=move_cmd)
        level_cluster.handle_cluster_request(hdr_move, [move_mode, 83])

    # Send stop command
    hdr_stop = foundation.ZCLHeader.cluster(tsn=2, command_id=stop_cmd)
    level_cluster.handle_cluster_request(hdr_stop, [])

    # Verify expected directional release event
    if expected_event is None:
        listener.zha_send_event.assert_not_called()
    else:
        # Find the directional release event among all fired events
        release_calls = [
            c
            for c in listener.zha_send_event.call_args_list
            if c == mock.call(expected_event, [])
        ]
        assert len(release_calls) == 1


@pytest.mark.parametrize(
    "quirk,v2_model",
    [
        (IkeaTradfriRemote2Btn, None),
        (IkeaTradfriRemote2BtnZLL, None),
        (IkeaRodretRemote2Btn, None),
        (IkeaRodretRemote2BtnNew, None),
        (IkeaTradfriRemote1, None),
        (IkeaTradfriRemote2, None),
        (IkeaTradfriRemote3, None),
        (IkeaTradfriRemote4, None),
        (IkeaTradfriRemote5, None),
        (None, "Remote Control N2"),  # STYRBAR
        (None, "09B9"),  # BILRESA 2 button
    ],
)
@pytest.mark.parametrize(
    "move_cmd,move_mode,expected_event",
    [
        (
            LevelControl.ServerCommandDefs.move_with_on_off.id,
            LevelControl.MoveMode.Up,
            COMMAND_MOVE_UP_RELEASE,
        ),
        (
            LevelControl.ServerCommandDefs.move.id,
            LevelControl.MoveMode.Down,
            COMMAND_MOVE_DOWN_RELEASE,
        ),
    ],
)
@pytest.mark.parametrize(
    "stop_cmd",
    [
        LevelControl.ServerCommandDefs.stop.id,
        LevelControl.ServerCommandDefs.stop_with_on_off.id,
    ],
)
async def test_ikea_dim_release_direction(
    zigpy_device_from_quirk,
    zigpy_device_from_v2_quirk,
    quirk,
    v2_model,
    move_cmd,
    move_mode,
    expected_event,
    stop_cmd,
):
    """Test that every IKEA dim remote reports which dim button ended its hold.

    The remotes send the same stop for both dim buttons on most firmware, so either
    stop has to end the hold of the button that was held.
    """
    if quirk is not None:
        device = zigpy_device_from_quirk(quirk)
        level_cluster = device.endpoints[1].out_clusters[LevelControl.cluster_id]
    else:
        device = zigpy_device_from_v2_quirk(
            IKEA,
            v2_model,
            cluster_ids={1: {LevelControl.cluster_id: ClusterType.Client}},
        )
        level_cluster = device.endpoints[1].out_clusters[LevelControl.cluster_id]

    assert isinstance(level_cluster, LevelControlWithMoveDirection)

    listener = mock.MagicMock()
    level_cluster.add_listener(listener)

    hdr_move = foundation.ZCLHeader.cluster(tsn=1, command_id=move_cmd)
    level_cluster.handle_cluster_request(hdr_move, [move_mode, 83])
    hdr_stop = foundation.ZCLHeader.cluster(tsn=2, command_id=stop_cmd)
    level_cluster.handle_cluster_request(hdr_stop, [])

    other_event = (
        COMMAND_MOVE_DOWN_RELEASE
        if expected_event == COMMAND_MOVE_UP_RELEASE
        else COMMAND_MOVE_UP_RELEASE
    )
    events = listener.zha_send_event.call_args_list
    assert events.count(mock.call(expected_event, [])) == 1
    assert mock.call(other_event, []) not in events

    # the long release triggers of the quirk fire on these events, not on the stop
    triggers = device.device_automation_triggers
    assert triggers[(LONG_RELEASE, DIM_UP)][COMMAND] == COMMAND_MOVE_UP_RELEASE
    assert triggers[(LONG_RELEASE, DIM_DOWN)][COMMAND] == COMMAND_MOVE_DOWN_RELEASE
