"""Test Zemismart ZM24TQ cover calibration and positioning."""

from unittest.mock import AsyncMock, patch

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zdo.types import NodeDescriptor

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
)
from zhaquirks.tuya.mcu import TuyaCoverControl, TuyaMCUCluster
from zhaquirks.tuya.ts0601_cover import TuyaZemismartSmartCover0601_3
from zhaquirks.tuya.ts0601_zemismart import MotorDirection, ZemismartWindowCovering

zhaquirks.setup()

LIMIT_DPS = {"upper_limit": 103, "middle_limit": 104, "lower_limit": 105}
REPORT_COMMANDS = [
    TuyaMCUCluster.ClientCommandDefs.get_data.id,
    TuyaMCUCluster.ClientCommandDefs.set_data_response.id,
    TuyaMCUCluster.ClientCommandDefs.active_status_report.id,
]


@pytest.fixture
def make_device(zigpy_device_from_v2_quirk):
    """Create independently addressed motors using the upstream v2 fixture."""

    def make(address=1):
        return zigpy_device_from_v2_quirk(
            "_TZE200_fzo2pocs",
            "TS0601",
            ieee=t.EUI64([address] + [0] * 7),
            cluster_ids={
                1: {
                    Basic.cluster_id: ClusterType.Server,
                    Groups.cluster_id: ClusterType.Server,
                    Scenes.cluster_id: ClusterType.Server,
                    TUYA_CLUSTER_ID: ClusterType.Server,
                    Time.cluster_id: ClusterType.Client,
                }
            },
            firmware_version=72,
        )

    return make


@pytest.fixture
def device(make_device):
    """Return a ZM24TQ motor."""
    return make_device()


@pytest.fixture
def raw_motor(zigpy_device_mock):
    """Reproduce both original signatures claimed by the legacy handlers."""

    def make(manufacturer="_TZE200_fzo2pocs", model="TS0601", time_server=False):
        device = zigpy_device_mock()
        device.manufacturer = manufacturer
        device.model = model
        device.node_desc = NodeDescriptor(manufacturer_code=4098)
        ep = device.add_endpoint(1)
        ep.profile_id = zha.PROFILE_ID
        ep.device_type = zha.DeviceType.SMART_PLUG
        for cluster in (Basic, Groups, Scenes):
            ep.add_input_cluster(cluster.cluster_id)
        ep.add_input_cluster(TUYA_CLUSTER_ID)
        ep.add_output_cluster(Ota.cluster_id)
        if time_server:
            ep.add_input_cluster(Time.cluster_id)
        else:
            ep.add_output_cluster(Time.cluster_id)
        ep.basic.update_attribute(Basic.AttributeDefs.app_version.id, 72)
        return device

    return make


def decode_write(request):
    """Decode the entire frame, checking the command and trailing bytes too."""
    header, payload = foundation.ZCLHeader.deserialize(request.kwargs["data"])
    assert header.command_id == TuyaMCUCluster.ServerCommandDefs.set_data.id
    assert header.manufacturer is None
    command, rest = TuyaCommand.deserialize(payload)
    assert rest == b""
    assert command.status == 0
    assert len(command.datapoints) == 1
    dp = command.datapoints[0]
    return dp.dp, dp.data.dp_type, dp.data.raw


def report(
    device,
    *datapoints,
    command=TuyaMCUCluster.ClientCommandDefs.set_data_response.id,
):
    """Feed a serialized multi-DP response through the actual cluster parser."""
    cluster = device.endpoints[1].tuya_manufacturer
    header = foundation.ZCLHeader.cluster(
        tsn=31,
        command_id=command,
        direction=foundation.Direction.Server_to_Client,
    )
    header = header.replace(
        frame_control=header.frame_control.replace(disable_default_response=True)
    )
    frame = (
        header.serialize()
        + TuyaCommand(
            status=0,
            tsn=31,
            datapoints=[
                TuyaDatapointData(dp, TuyaData(value)) for dp, value in datapoints
            ],
        ).serialize()
    )
    header, args = cluster.deserialize(frame)
    cluster.handle_message(header, args)


@pytest.mark.parametrize("time_server", [False, True])
def test_original_signatures_resolve_to_v2(raw_motor, time_server):
    """Built-in loading must select v2 for both migrated legacy signatures."""
    device = DEVICE_REGISTRY.resolve(raw_motor(time_server=time_server))
    ep = device.endpoints[1]
    assert isinstance(ep.window_covering, ZemismartWindowCovering)
    assert ep.device_type == zha.DeviceType.WINDOW_COVERING_DEVICE
    assert ep.profile_id == zha.PROFILE_ID
    assert Ota.cluster_id in ep.out_clusters
    assert Time.cluster_id in (ep.in_clusters if time_server else ep.out_clusters)


@pytest.mark.parametrize(
    "manufacturer",
    [
        "_TZE200_iossyxra",
        "_TZE200_pw7mji0l",
        "_TZE200_9vpe3fl1",
        "_TZE200_sq6affpe",
    ],
)
def test_other_motors_retain_legacy_handler(raw_motor, manufacturer):
    """Migrating one manufacturer must not change the other legacy matches."""
    device = DEVICE_REGISTRY.resolve(raw_motor(manufacturer=manufacturer))
    assert isinstance(device, TuyaZemismartSmartCover0601_3)


@pytest.mark.parametrize(
    "manufacturer,model",
    [
        ("_TZE284_fzo2pocs", "TS0601"),
        ("_TZE200_fzo2pocs", "OTHER"),
    ],
)
def test_other_models_do_not_match(raw_motor, manufacturer, model):
    """Do not apply this motor protocol to another identifier."""
    device = DEVICE_REGISTRY.resolve(raw_motor(manufacturer, model))
    assert not isinstance(
        getattr(device.endpoints[1], "window_covering", None), ZemismartWindowCovering
    )


@pytest.mark.parametrize(
    "command,value",
    [
        (WindowCovering.ServerCommandDefs.up_open.id, TuyaCoverControl.Open),
        (WindowCovering.ServerCommandDefs.down_close.id, TuyaCoverControl.Close),
        (WindowCovering.ServerCommandDefs.stop.id, TuyaCoverControl.Stop),
    ],
)
async def test_open_close_stop_wire_payload(device, command, value):
    """Encode each travel command as the expected Tuya enum."""
    ep = device.endpoints[1]
    with patch.object(
        ep, "request", new=AsyncMock(return_value=foundation.Status.SUCCESS)
    ) as request:
        result = await ep.window_covering.command(command)
        await wait_for_zigpy_tasks()
    assert result.status == foundation.Status.SUCCESS
    request.assert_awaited_once()
    assert decode_write(request.call_args) == (1, TuyaDPType.ENUM, bytes([value]))


@pytest.mark.parametrize("ha_position", [0, 25, 50, 75, 100])
@pytest.mark.parametrize("keyword", [False, True])
async def test_percentage_writes_only_dp2_and_preserves_actual_position(
    device, ha_position, keyword
):
    """Send one target DP without modifying the measured position."""
    ep = device.endpoints[1]
    report(device, (3, 12))
    with patch.object(
        ep, "request", new=AsyncMock(return_value=foundation.Status.SUCCESS)
    ) as request:
        if keyword:
            await ep.window_covering.command(
                WindowCovering.ServerCommandDefs.go_to_lift_percentage.id,
                percentage_lift_value=100 - ha_position,
            )
        else:
            await ep.window_covering.command(
                WindowCovering.ServerCommandDefs.go_to_lift_percentage.id,
                100 - ha_position,
            )
        await wait_for_zigpy_tasks()
    request.assert_awaited_once()
    assert decode_write(request.call_args) == (
        2,
        TuyaDPType.VALUE,
        ha_position.to_bytes(4, "big"),
    )
    assert ep.window_covering.get("current_position_lift_percentage") == 88


@pytest.mark.parametrize("value", [-1, 101, None, True, "50"])
async def test_invalid_percentage_does_not_move_motor(device, value):
    """Reject invalid target positions without sending a command."""
    ep = device.endpoints[1]
    with patch.object(ep, "request", new=AsyncMock()) as request:
        result = await ep.window_covering.command(
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id, value
        )
        await wait_for_zigpy_tasks()
    assert result.status == foundation.Status.INVALID_VALUE
    request.assert_not_called()


@pytest.mark.parametrize("command", REPORT_COMMANDS)
@pytest.mark.parametrize("ha_position", [0, 12, 25, 88, 100])
def test_position_reports_and_target_echo(device, command, ha_position):
    """Update measured position only from DP 3 for every report command."""
    report(device, (3, ha_position), command=command)
    cover = device.endpoints[1].window_covering
    assert cover.get("current_position_lift_percentage") == 100 - ha_position
    # A target echo is not evidence of actual travel.
    report(device, (2, 50), command=command)
    assert cover.get("current_position_lift_percentage") == 100 - ha_position


@pytest.mark.parametrize("direction", list(MotorDirection))
async def test_direction_is_enum_dp5(device, direction):
    """Encode direction changes as enum DP 5."""
    ep = device.endpoints[1]
    with patch.object(
        ep, "request", new=AsyncMock(return_value=foundation.Status.SUCCESS)
    ) as request:
        await ep.tuya_manufacturer.write_attributes({"motor_direction": direction})
        await wait_for_zigpy_tasks()
    request.assert_awaited_once()
    assert decode_write(request.call_args) == (5, TuyaDPType.ENUM, bytes([direction]))


@pytest.mark.parametrize("name,dp", LIMIT_DPS.items())
@pytest.mark.parametrize("value", [True, False])
async def test_limit_buttons_use_boolean_payload_and_can_repeat(
    device, name, dp, value
):
    """Encode repeatable limit writes as bool rather than enum."""
    ep = device.endpoints[1]
    with patch.object(
        ep, "request", new=AsyncMock(return_value=foundation.Status.SUCCESS)
    ) as request:
        for _ in range(2):
            await ep.tuya_manufacturer.write_attributes({name: value})
            await wait_for_zigpy_tasks()
    assert request.await_count == 2
    assert all(
        decode_write(call) == (dp, TuyaDPType.BOOL, bytes([value]))
        for call in request.call_args_list
    )


def test_multi_datapoint_report_updates_position_and_configuration(device):
    """Handle position and configuration datapoints in the same report."""
    report(device, (3, 75), (5, t.enum8(1)), (103, t.Bool.true), (105, t.Bool.false))
    ep = device.endpoints[1]
    assert ep.window_covering.get("current_position_lift_percentage") == 25
    assert ep.tuya_manufacturer.get("motor_direction") == MotorDirection.Back
    assert ep.tuya_manufacturer.get("upper_limit") == 1
    assert ep.tuya_manufacturer.get("lower_limit") == 0


def test_motors_have_independent_state(make_device):
    """Keep state independent across multiple motors."""
    devices = [make_device(address=i + 1) for i in range(3)]
    for i, device in enumerate(devices):
        report(device, (3, i * 20), (5, t.enum8(i % 2)))
    for i, device in enumerate(devices):
        assert (
            device.endpoints[1].window_covering.get("current_position_lift_percentage")
            == 100 - i * 20
        )
        assert device.endpoints[1].tuya_manufacturer.get("motor_direction") == i % 2


def test_entity_metadata(device):
    """Expose one direction select and six repeatable limit buttons."""
    metadata = (
        device._quirk_registry_entry.zha_device_factory.quirk_definition.entity_metadata
    )
    assert len({entry.unique_id_suffix for entry in metadata}) == len(metadata)
    assert all(entry.cluster_id == TUYA_CLUSTER_ID for entry in metadata)

    (select,) = [
        entry for entry in metadata if entry.entity_platform == Platform.SELECT
    ]
    assert select.attribute_name == "motor_direction"
    assert select.enum == MotorDirection
    assert select.fallback_name == "Motor direction"

    buttons = [entry for entry in metadata if entry.entity_platform == Platform.BUTTON]
    assert len(buttons) == 6
    assert {entry.fallback_name for entry in buttons} == {
        f"{action} {level} limit"
        for action in ("Set", "Delete")
        for level in ("upper", "middle", "lower")
    }
    for button in buttons:
        action, level, _ = button.unique_id_suffix.split("_")
        assert button.translation_key == button.unique_id_suffix
        assert button.attribute_name == f"{level}_limit"
        assert button.attribute_value == (action == "set")
        assert button.attribute_name in LIMIT_DPS

    assert len(metadata) == 7
