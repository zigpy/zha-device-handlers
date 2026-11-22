"""Tests for Candeo."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.candeo import CANDEO
from zhaquirks.candeo.scene_switch_remote_5_button_rotary import (
    CandeoSceneSwitchRemoteButtonActionMap,
    CandeoSceneSwitchRemoteButtonNumberMap,
    CandeoSceneSwitchRemoteCluster,
    CandeoSceneSwitchRemoteClusterCommand,
    CandeoSceneSwitchRemoteMessageType,
    CandeoSceneSwitchRemoteRingActionMap,
    CandeoSceneSwitchRemoteRingDirectionMap,
)
from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_CENTRE,
    COMMAND_CONTINUED_ROTATING,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    COMMAND_STARTED_ROTATING,
    COMMAND_STOPPED_ROTATING,
    LEFT,
    RIGHT,
    ROTATED,
)

zhaquirks.setup()


# candeo motion tests
@pytest.mark.parametrize(
    "lux_in, lux_out",
    (
        (0, 1),
        (24112, 1),  # 1 lux
        (33598, 18074),  # 64 lux
        (34299, 26989),  # 500 lux
        (34977, 36895),  # 4891 lux
    ),
)
async def test_candeo_motion_illuminance(zigpy_device_from_v2_quirk, lux_in, lux_out):
    """Test that illuminance value is converted correctly."""
    device = zigpy_device_from_v2_quirk(CANDEO, "C-ZB-SEMO")

    illuminance_cluster = device.endpoints[1].illuminance
    illuminance_listener = ClusterListener(illuminance_cluster)
    illuminance_attr_id = IlluminanceMeasurement.AttributeDefs.measured_value.id

    illuminance_cluster.update_attribute(illuminance_attr_id, lux_in)
    assert len(illuminance_listener.attribute_updates) == 1
    assert illuminance_listener.attribute_updates[0][0] == illuminance_attr_id
    assert illuminance_listener.attribute_updates[0][1] == lux_out


# candeo scene switch remote 5 button rotary tests


@pytest.mark.asyncio
async def test_candeo_scene_switch_remote_apply_custom_configuration(
    zigpy_device_from_v2_quirk,
):
    """Test apply custom configuration is called and calls bind on the cluster."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")
    cluster = device.endpoints[1].candeo_scene_switch_remote
    cluster.bind = mock.AsyncMock()
    await cluster.apply_custom_configuration()
    cluster.bind.assert_awaited_once()


def test_candeo_scene_switch_remote_duplicate_sequence_number(
    zigpy_device_from_v2_quirk,
):
    """Test duplicate sequence number ignored."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()
    header.tsn = 5

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.button_press,
        0x0,
        CandeoSceneSwitchRemoteButtonNumberMap.button_1,
        CandeoSceneSwitchRemoteButtonActionMap.press,
    )

    cluster.handle_cluster_request(header, args)
    cluster.handle_cluster_request(header, args)

    assert cluster.send_default_rsp.call_count == 2
    assert listener.zha_send_event.call_count == 1


def test_candeo_scene_switch_remote_unknown_command_id(zigpy_device_from_v2_quirk):
    """Test unknown command id."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = 0x99
    header.frame_control = foundation.FrameControl.cluster()

    cluster.handle_cluster_request(header, [])

    assert listener.zha_send_event.call_count == 0


def test_candeo_scene_switch_remote_missing_schema_fields(
    zigpy_device_from_v2_quirk,
):
    """Test missing CandeoSceneSwitchRemoteClusterCommand schema fields."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(None, None, None, None)

    cluster.handle_cluster_request(header, args)

    assert listener.zha_send_event.call_count == 0


def test_candeo_scene_switch_remote_unknown_message_type(
    zigpy_device_from_v2_quirk,
):
    """Test unknown CandeoSceneSwitchRemoteMessageType."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        0x99,
        0x0,
        CandeoSceneSwitchRemoteButtonNumberMap.button_1,
        CandeoSceneSwitchRemoteButtonActionMap.press,
    )

    cluster.handle_cluster_request(header, args)

    assert listener.zha_send_event.call_count == 0


@pytest.mark.parametrize(
    "button_number, button_action, expected_button_name, expected_button_action_name",
    [
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_1,
            CandeoSceneSwitchRemoteButtonActionMap.press,
            BUTTON_1,
            COMMAND_PRESS,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_1,
            CandeoSceneSwitchRemoteButtonActionMap.double,
            BUTTON_1,
            COMMAND_DOUBLE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_1,
            CandeoSceneSwitchRemoteButtonActionMap.hold,
            BUTTON_1,
            COMMAND_HOLD,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_1,
            CandeoSceneSwitchRemoteButtonActionMap.release,
            BUTTON_1,
            COMMAND_RELEASE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_2,
            CandeoSceneSwitchRemoteButtonActionMap.press,
            BUTTON_2,
            COMMAND_PRESS,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_2,
            CandeoSceneSwitchRemoteButtonActionMap.double,
            BUTTON_2,
            COMMAND_DOUBLE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_2,
            CandeoSceneSwitchRemoteButtonActionMap.hold,
            BUTTON_2,
            COMMAND_HOLD,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_2,
            CandeoSceneSwitchRemoteButtonActionMap.release,
            BUTTON_2,
            COMMAND_RELEASE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_3,
            CandeoSceneSwitchRemoteButtonActionMap.press,
            BUTTON_3,
            COMMAND_PRESS,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_3,
            CandeoSceneSwitchRemoteButtonActionMap.double,
            BUTTON_3,
            COMMAND_DOUBLE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_3,
            CandeoSceneSwitchRemoteButtonActionMap.hold,
            BUTTON_3,
            COMMAND_HOLD,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_3,
            CandeoSceneSwitchRemoteButtonActionMap.release,
            BUTTON_3,
            COMMAND_RELEASE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_4,
            CandeoSceneSwitchRemoteButtonActionMap.press,
            BUTTON_4,
            COMMAND_PRESS,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_4,
            CandeoSceneSwitchRemoteButtonActionMap.double,
            BUTTON_4,
            COMMAND_DOUBLE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_4,
            CandeoSceneSwitchRemoteButtonActionMap.hold,
            BUTTON_4,
            COMMAND_HOLD,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_4,
            CandeoSceneSwitchRemoteButtonActionMap.release,
            BUTTON_4,
            COMMAND_RELEASE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_centre,
            CandeoSceneSwitchRemoteButtonActionMap.press,
            BUTTON_CENTRE,
            COMMAND_PRESS,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_centre,
            CandeoSceneSwitchRemoteButtonActionMap.double,
            BUTTON_CENTRE,
            COMMAND_DOUBLE,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_centre,
            CandeoSceneSwitchRemoteButtonActionMap.hold,
            BUTTON_CENTRE,
            COMMAND_HOLD,
        ),
        (
            CandeoSceneSwitchRemoteButtonNumberMap.button_centre,
            CandeoSceneSwitchRemoteButtonActionMap.release,
            BUTTON_CENTRE,
            COMMAND_RELEASE,
        ),
    ],
)
def test_candeo_scene_switch_remote_button_number_and_button_action_combinations(
    zigpy_device_from_v2_quirk,
    button_number,
    button_action,
    expected_button_name,
    expected_button_action_name,
):
    """Test button numbers and button actions generate events correctly."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.button_press,
        0x0,
        button_number,
        button_action,
    )

    cluster.handle_cluster_request(header, args)

    button_event = listener.zha_send_event.call_args[0]

    assert button_event[0] == expected_button_action_name

    assert button_event[1][BUTTON] == expected_button_name


@pytest.mark.parametrize(
    "button_number, button_action",
    [
        (0x99, CandeoSceneSwitchRemoteButtonActionMap.press),
        (CandeoSceneSwitchRemoteButtonNumberMap.button_1, 0x99),
    ],
)
def test_candeo_scene_switch_remote_unknown_button_number_or_button_action(
    zigpy_device_from_v2_quirk, button_number, button_action
):
    """Test unknown button numbers and button actions are ignored."""

    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.button_press,
        0x0,
        button_number,
        button_action,
    )

    cluster.handle_cluster_request(header, args)

    assert listener.zha_send_event.call_count == 0


@pytest.mark.parametrize(
    "ring_direction",
    [
        (CandeoSceneSwitchRemoteRingDirectionMap.left),
        (CandeoSceneSwitchRemoteRingDirectionMap.right),
    ],
)
def test_candeo_scene_switch_remote_ring_started_rotating(
    zigpy_device_from_v2_quirk, ring_direction
):
    """Test ring started rotating actions generate events correctly."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        ring_direction,
        CandeoSceneSwitchRemoteRingActionMap.started_rotating,
        0x01,
    )

    cluster.handle_cluster_request(header, args)

    ring_event = listener.zha_send_event.call_args[0]

    assert ring_event[0] == COMMAND_STARTED_ROTATING

    expected_ring_direction_name = (
        LEFT
        if ring_direction == CandeoSceneSwitchRemoteRingDirectionMap.left
        else RIGHT
    )

    assert ring_event[1][ROTATED] == expected_ring_direction_name

    assert listener.zha_send_event.call_count == 1


@pytest.mark.parametrize(
    "ring_direction, ring_action",
    [
        (0x99, CandeoSceneSwitchRemoteRingActionMap.started_rotating),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x99),
    ],
)
def test_candeo_scene_switch_remote_unknown_ring_direction_or_ring_action(
    zigpy_device_from_v2_quirk, ring_direction, ring_action
):
    """Test unknown ring directions and ring actions are ignored."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        ring_direction,
        ring_action,
        0x01,
    )

    cluster.handle_cluster_request(header, args)

    assert listener.zha_send_event.call_count == 0


@pytest.mark.parametrize(
    "ring_direction, ring_clicks",
    [
        (CandeoSceneSwitchRemoteRingDirectionMap.left, 0x01),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x01),
        (CandeoSceneSwitchRemoteRingDirectionMap.left, 0x02),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x03),
        (CandeoSceneSwitchRemoteRingDirectionMap.left, 0x09),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x06),
    ],
)
def test_candeo_scene_switch_remote_ring_continued_rotating_after_started_rotating(
    zigpy_device_from_v2_quirk, ring_direction, ring_clicks
):
    """Test ring continued rotating actions (after started rotating) generate events correctly."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        ring_direction,
        CandeoSceneSwitchRemoteRingActionMap.started_rotating,
        ring_clicks,
    )

    cluster.handle_cluster_request(header, args)

    calls = listener.zha_send_event.call_args_list

    assert len(calls) == ring_clicks

    expected_ring_direction_name = (
        LEFT
        if ring_direction == CandeoSceneSwitchRemoteRingDirectionMap.left
        else RIGHT
    )

    for x, call in enumerate(calls):
        ring_event_action, ring_event_direction = call[0]

        expected_ring_action_name = (
            COMMAND_STARTED_ROTATING if x == 0 else COMMAND_CONTINUED_ROTATING
        )

        assert ring_event_action == expected_ring_action_name

        assert ring_event_direction[ROTATED] == expected_ring_direction_name

    assert listener.zha_send_event.call_count == ring_clicks


@pytest.mark.parametrize(
    "ring_direction, ring_clicks",
    [
        (CandeoSceneSwitchRemoteRingDirectionMap.left, 0x01),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x01),
        (CandeoSceneSwitchRemoteRingDirectionMap.left, 0x02),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x03),
        (CandeoSceneSwitchRemoteRingDirectionMap.left, 0x09),
        (CandeoSceneSwitchRemoteRingDirectionMap.right, 0x06),
    ],
)
def test_candeo_scene_switch_remote_ring_continued_rotating_after_continued_rotating(
    zigpy_device_from_v2_quirk, ring_direction, ring_clicks
):
    """Test ring continued rotating actions (after continued rotating) generate events correctly."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    cluster.previous_rotation_event = COMMAND_STARTED_ROTATING
    cluster.previous_rotation_direction = ring_direction

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        ring_direction,
        CandeoSceneSwitchRemoteRingActionMap.continued_rotating,
        ring_clicks,
    )

    cluster.handle_cluster_request(header, args)

    calls = listener.zha_send_event.call_args_list

    assert len(calls) == ring_clicks

    expected_ring_direction_name = (
        LEFT
        if ring_direction == CandeoSceneSwitchRemoteRingDirectionMap.left
        else RIGHT
    )

    for _x, call in enumerate(calls):
        ring_event_action, ring_event_direction = call[0]

        assert ring_event_action == COMMAND_CONTINUED_ROTATING

        assert ring_event_direction[ROTATED] == expected_ring_direction_name

    assert listener.zha_send_event.call_count == ring_clicks


def test_candeo_scene_switch_remote_ring_direction_and_ring_action_persistence(
    zigpy_device_from_v2_quirk,
):
    """Test ring direction and ring action persistence data set correctly."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()
    header.tsn = 1

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        CandeoSceneSwitchRemoteRingDirectionMap.left,
        CandeoSceneSwitchRemoteRingActionMap.started_rotating,
        0x01,
    )

    cluster.handle_cluster_request(header, args)

    assert cluster.previous_rotation_direction == LEFT
    assert cluster.previous_rotation_event == COMMAND_STARTED_ROTATING

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        0x0,
        CandeoSceneSwitchRemoteRingActionMap.stopped_rotating,
        0x0,
    )

    header.tsn = 2

    cluster.handle_cluster_request(header, args)

    assert cluster.previous_rotation_direction == LEFT
    assert cluster.previous_rotation_event == COMMAND_STOPPED_ROTATING

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        CandeoSceneSwitchRemoteRingDirectionMap.right,
        CandeoSceneSwitchRemoteRingActionMap.started_rotating,
        0x01,
    )

    header.tsn = 3

    cluster.handle_cluster_request(header, args)

    assert cluster.previous_rotation_direction == RIGHT
    assert cluster.previous_rotation_event == COMMAND_STARTED_ROTATING

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        0x0,
        CandeoSceneSwitchRemoteRingActionMap.stopped_rotating,
        0x0,
    )

    header.tsn = 4

    cluster.handle_cluster_request(header, args)

    assert cluster.previous_rotation_direction == RIGHT
    assert cluster.previous_rotation_event == COMMAND_STOPPED_ROTATING

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        CandeoSceneSwitchRemoteRingDirectionMap.left,
        CandeoSceneSwitchRemoteRingActionMap.started_rotating,
        0x03,
    )

    header.tsn = 5

    cluster.handle_cluster_request(header, args)

    assert cluster.previous_rotation_direction == LEFT
    assert cluster.previous_rotation_event == COMMAND_CONTINUED_ROTATING

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        0x0,
        CandeoSceneSwitchRemoteRingActionMap.stopped_rotating,
        0x0,
    )

    header.tsn = 6

    cluster.handle_cluster_request(header, args)

    assert cluster.previous_rotation_direction == LEFT
    assert cluster.previous_rotation_event == COMMAND_STOPPED_ROTATING


@pytest.mark.parametrize(
    "previous_rotation_direction, previous_rotation_event",
    [
        (LEFT, COMMAND_STARTED_ROTATING),
        (RIGHT, COMMAND_STARTED_ROTATING),
        (LEFT, COMMAND_CONTINUED_ROTATING),
        (RIGHT, COMMAND_CONTINUED_ROTATING),
    ],
)
def test_candeo_scene_switch_remote_ring_stopped_rotating(
    zigpy_device_from_v2_quirk, previous_rotation_direction, previous_rotation_event
):
    """Test ring stopped rotating actions generate events correctly."""
    device = zigpy_device_from_v2_quirk(manufacturer=CANDEO, model="C-ZB-SR5BR")

    cluster = device.endpoints[1].candeo_scene_switch_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.send_default_rsp = mock.MagicMock()

    cluster.previous_rotation_direction = previous_rotation_direction
    cluster.previous_rotation_event = previous_rotation_event

    header = foundation.ZCLHeader()
    header.command_id = (
        CandeoSceneSwitchRemoteCluster.ServerCommandDefs.candeo_scene_switch_remote.id
    )
    header.frame_control = foundation.FrameControl.cluster()

    args = CandeoSceneSwitchRemoteClusterCommand(
        CandeoSceneSwitchRemoteMessageType.ring_rotation,
        0x0,
        CandeoSceneSwitchRemoteRingActionMap.stopped_rotating,
        0x0,
    )

    cluster.handle_cluster_request(header, args)

    ring_event = listener.zha_send_event.call_args[0]

    assert ring_event[0] == COMMAND_STOPPED_ROTATING

    assert ring_event[1][ROTATED] == previous_rotation_direction

    assert listener.zha_send_event.call_count == 1
