"""Tests for ubisys quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.common import ClusterListener
from zhaquirks.ubisys import (
    InputMode,
    UbisysCluster,
    UbisysInputConfigCluster,
    build_onoff_actions,
)
from zhaquirks.ubisys.control_c4 import UbisysC4InputConfigCluster
from zhaquirks.ubisys.cover_j1 import UbisysJ1InputConfigCluster
from zhaquirks.ubisys.dimmer_d1 import UbisysD1InputConfigCluster
import zhaquirks.ubisys.switch_s1  # noqa: F401 - registers QuirkBuilder
from zhaquirks.ubisys.switch_s2 import UbisysS2InputConfigCluster


@pytest.fixture
def ubisys_s1(zigpy_device_from_v2_quirk):
    """Create ubisys S1 device."""
    return zigpy_device_from_v2_quirk(
        "ubisys",
        "S1 (5501)",
        cluster_ids={
            3: {ElectricalMeasurement.cluster_id: ClusterType.Server},
            232: {UbisysCluster.cluster_id: ClusterType.Server},
        },
    )


@pytest.fixture
def ubisys_s2(zigpy_device_from_v2_quirk):
    """Create ubisys S2 device."""
    return zigpy_device_from_v2_quirk(
        "ubisys",
        "S2 (5502)",
        cluster_ids={
            5: {ElectricalMeasurement.cluster_id: ClusterType.Server},
            232: {UbisysCluster.cluster_id: ClusterType.Server},
        },
    )


@pytest.fixture
def ubisys_d1(zigpy_device_from_v2_quirk):
    """Create ubisys D1 device."""
    return zigpy_device_from_v2_quirk(
        "ubisys",
        "D1 (5503)",
        cluster_ids={
            4: {ElectricalMeasurement.cluster_id: ClusterType.Server},
            232: {UbisysCluster.cluster_id: ClusterType.Server},
        },
    )


@pytest.fixture
def ubisys_j1(zigpy_device_from_v2_quirk):
    """Create ubisys J1 device."""
    return zigpy_device_from_v2_quirk(
        "ubisys",
        "J1 (5502)",
        cluster_ids={
            3: {ElectricalMeasurement.cluster_id: ClusterType.Server},
            232: {UbisysCluster.cluster_id: ClusterType.Server},
        },
    )


@pytest.fixture
def ubisys_c4(zigpy_device_from_v2_quirk):
    """Create ubisys C4 device."""
    return zigpy_device_from_v2_quirk(
        "ubisys",
        "C4 (5504)",
        cluster_ids={
            232: {UbisysCluster.cluster_id: ClusterType.Server},
        },
    )


def _build_expected_frame(actions: list[bytes], tsn: int = 0) -> bytes:
    """Build the expected ZCL Write Attributes Structured frame."""
    frame = bytearray()
    # ZCL Header
    frame.append(0x00)  # Frame control
    frame.append(tsn)
    frame.append(0x0F)  # Write Attributes Structured
    # Attribute ID 0x0001 (input_actions) LE
    frame.extend(b"\x01\x00")
    # Selector: 0x00 (whole attribute)
    frame.append(0x00)
    # Data Type: 0x48 (Array), Element Type: 0x41 (OCTET_STR)
    frame.extend(b"\x48\x41")
    # Count (uint16 LE)
    frame.extend(len(actions).to_bytes(2, byteorder="little"))
    # Elements
    for action in actions:
        frame.append(len(action))
        frame.extend(action)
    return bytes(frame)


# --- S1 Tests ---


@pytest.mark.parametrize(
    "mode",
    [
        InputMode.Toggle,
        InputMode.Toggle_switch,
        InputMode.On_off_switch,
    ],
)
async def test_s1_input_mode_write(ubisys_s1, mode):
    """Test writing input_mode sends correct input_actions to endpoint 232."""
    input_config_cluster = ubisys_s1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_s1.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysInputConfigCluster.AttributeDefs.input_mode.name: mode}
        )

        # Verify structured write was sent to endpoint 232
        assert endpoint_232.request.call_count == 1

        call_kwargs = endpoint_232.request.call_args
        assert call_kwargs.kwargs["cluster"] == UbisysCluster.cluster_id
        assert call_kwargs.kwargs["command_id"] == 0x0F

        # Verify the raw frame payload contains the correct actions
        sent_data = call_kwargs.kwargs["data"]
        tsn = sent_data[1]  # extract actual TSN from the frame
        expected_actions = build_onoff_actions(0, 2, mode)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    # Verify local cache was updated
    assert (
        UbisysInputConfigCluster.AttributeDefs.input_mode.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_s1_detached_mode(ubisys_s1, detach):
    """Test detached switch sends bind/unbind for self-binding on OnOff."""
    input_config_cluster = ubisys_s1.endpoints[1].ubisys_input_config
    zdo = ubisys_s1.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        zdo,
        "Unbind_req" if detach else "Bind_req",
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysInputConfigCluster.AttributeDefs.detached.name: detach}
        )

        assert mock_req.call_count == 1

        args = mock_req.call_args[0]
        # Source IEEE
        assert args[0] == ubisys_s1.ieee
        # Source endpoint (input)
        assert args[1] == 2  # EP2
        # Cluster
        assert args[2] == OnOff.cluster_id
        # Destination: self-bind to output endpoint
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_s1.ieee
        assert dst.endpoint == 1  # EP1

    # Verify local cache was updated
    assert (
        UbisysInputConfigCluster.AttributeDefs.detached.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


# --- S2 Tests ---


@pytest.mark.parametrize("mode", list(InputMode))
async def test_s2_input_mode_1_write(ubisys_s2, mode):
    """Test S2 input_mode_1 writes actions for both inputs to endpoint 232."""
    input_config_cluster = ubisys_s2.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_s2.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysS2InputConfigCluster.AttributeDefs.input_mode_1.name: mode}
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Actions for both inputs: input 1 with new mode, input 2 with default Toggle
        expected_actions = build_onoff_actions(0, 3, mode) + build_onoff_actions(
            1, 4, InputMode.Toggle
        )
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    assert (
        UbisysS2InputConfigCluster.AttributeDefs.input_mode_1.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("mode", list(InputMode))
async def test_s2_input_mode_2_write(ubisys_s2, mode):
    """Test S2 input_mode_2 writes actions for both inputs to endpoint 232."""
    input_config_cluster = ubisys_s2.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_s2.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysS2InputConfigCluster.AttributeDefs.input_mode_2.name: mode}
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Actions for both inputs: input 1 with default Toggle, input 2 with new mode
        expected_actions = build_onoff_actions(
            0, 3, InputMode.Toggle
        ) + build_onoff_actions(1, 4, mode)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    assert (
        UbisysS2InputConfigCluster.AttributeDefs.input_mode_2.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_s2_detached_1(ubisys_s2, detach):
    """Test S2 detached_1 sends bind/unbind for EP3 -> EP1 on OnOff."""
    input_config_cluster = ubisys_s2.endpoints[1].ubisys_input_config
    zdo = ubisys_s2.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        zdo,
        "Unbind_req" if detach else "Bind_req",
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysS2InputConfigCluster.AttributeDefs.detached_1.name: detach}
        )

        assert mock_req.call_count == 1
        args = mock_req.call_args[0]
        assert args[0] == ubisys_s2.ieee
        assert args[1] == 3  # EP3
        assert args[2] == OnOff.cluster_id
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_s2.ieee
        assert dst.endpoint == 1  # EP1

    assert (
        UbisysS2InputConfigCluster.AttributeDefs.detached_1.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_s2_detached_2(ubisys_s2, detach):
    """Test S2 detached_2 sends bind/unbind for EP4 -> EP2 on OnOff."""
    input_config_cluster = ubisys_s2.endpoints[1].ubisys_input_config
    zdo = ubisys_s2.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        zdo,
        "Unbind_req" if detach else "Bind_req",
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysS2InputConfigCluster.AttributeDefs.detached_2.name: detach}
        )

        assert mock_req.call_count == 1
        args = mock_req.call_args[0]
        assert args[0] == ubisys_s2.ieee
        assert args[1] == 4  # EP4
        assert args[2] == OnOff.cluster_id
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_s2.ieee
        assert dst.endpoint == 2  # EP2

    assert (
        UbisysS2InputConfigCluster.AttributeDefs.detached_2.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


# --- D1 Tests ---


@pytest.mark.parametrize("detach", [True, False])
async def test_d1_detached_mode(ubisys_d1, detach):
    """Test D1 detached sends bind/unbind for both OnOff and LevelControl."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    zdo = ubisys_d1.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    req_name = "Unbind_req" if detach else "Bind_req"
    with mock.patch.object(
        zdo,
        req_name,
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysD1InputConfigCluster.AttributeDefs.detached.name: detach}
        )

        # Should be called twice: once for OnOff, once for LevelControl
        assert mock_req.call_count == 2

        # First call: OnOff
        args_onoff = mock_req.call_args_list[0][0]
        assert args_onoff[0] == ubisys_d1.ieee
        assert args_onoff[1] == 2  # EP2
        assert args_onoff[2] == OnOff.cluster_id
        dst = args_onoff[3]
        assert dst.endpoint == 1  # EP1

        # Second call: LevelControl
        args_level = mock_req.call_args_list[1][0]
        assert args_level[0] == ubisys_d1.ieee
        assert args_level[1] == 2  # EP2
        assert args_level[2] == LevelControl.cluster_id
        dst = args_level[3]
        assert dst.endpoint == 1  # EP1

    assert (
        UbisysD1InputConfigCluster.AttributeDefs.detached.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


# --- J1 Tests ---


@pytest.mark.parametrize("detach", [True, False])
async def test_j1_detached_mode(ubisys_j1, detach):
    """Test J1 detached sends bind/unbind for WindowCovering."""
    input_config_cluster = ubisys_j1.endpoints[1].ubisys_input_config
    zdo = ubisys_j1.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        zdo,
        "Unbind_req" if detach else "Bind_req",
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysJ1InputConfigCluster.AttributeDefs.detached.name: detach}
        )

        assert mock_req.call_count == 1
        args = mock_req.call_args[0]
        assert args[0] == ubisys_j1.ieee
        assert args[1] == 2  # EP2
        assert args[2] == WindowCovering.cluster_id
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_j1.ieee
        assert dst.endpoint == 1  # EP1

    assert (
        UbisysJ1InputConfigCluster.AttributeDefs.detached.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


# --- C4 Tests ---


@pytest.mark.parametrize(
    ("attr_name", "input_index", "source_ep"),
    [
        (UbisysC4InputConfigCluster.AttributeDefs.input_mode_1.name, 0, 1),
        (UbisysC4InputConfigCluster.AttributeDefs.input_mode_2.name, 1, 2),
        (UbisysC4InputConfigCluster.AttributeDefs.input_mode_3.name, 2, 3),
        (UbisysC4InputConfigCluster.AttributeDefs.input_mode_4.name, 3, 4),
    ],
)
async def test_c4_input_mode_write(ubisys_c4, attr_name, input_index, source_ep):
    """Test C4 input_mode writes actions for all 4 inputs to endpoint 232."""
    input_config_cluster = ubisys_c4.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_c4.endpoints[232]

    mode = InputMode.On_off_switch

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes({attr_name: mode})

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Build expected: the changed input gets On_off_switch, others stay Toggle
        expected_actions: list[bytes] = []
        for idx, sep in [(0, 1), (1, 2), (2, 3), (3, 4)]:
            if idx == input_index:
                expected_actions.extend(build_onoff_actions(idx, sep, mode))
            else:
                expected_actions.extend(build_onoff_actions(idx, sep, InputMode.Toggle))
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    # Verify the correct attribute was cached
    attr_def = getattr(UbisysC4InputConfigCluster.AttributeDefs, attr_name)
    assert (attr_def.id, mode) in input_config_listener.attribute_updates
