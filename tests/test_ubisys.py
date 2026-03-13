"""Tests for ubisys quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import AttributeWrittenEvent, ClusterType
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import Status

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.ubisys import (
    InputMode,
    UbisysCluster,
    UbisysInputConfigCluster,
    build_onoff_actions,
)
from zhaquirks.ubisys.control_c4 import UbisysC4InputConfigCluster
from zhaquirks.ubisys.cover_j1 import (
    CalibrationState,
    UbisysJ1CalibrationCluster,
    UbisysJ1InputConfigCluster,
    UbisysWindowCovering,
)
from zhaquirks.ubisys.dimmer_d1 import (
    DimmerInputMode,
    UbisysD1InputConfigCluster,
    build_dimmer_double_actions,
    build_dimmer_single_actions,
)
from zhaquirks.ubisys.switch_s1r import UbisysS1RInputConfigCluster
from zhaquirks.ubisys.switch_s2 import UbisysS2InputConfigCluster

zhaquirks.setup()


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
def ubisys_s1r(zigpy_device_from_v2_quirk):
    """Create ubisys S1-R device."""
    return zigpy_device_from_v2_quirk(
        "ubisys",
        "S1-R (5601)",
        cluster_ids={
            1: {ElectricalMeasurement.cluster_id: ClusterType.Server},
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


# --- S1-R Tests ---


@pytest.mark.parametrize("mode", list(InputMode))
async def test_s1r_input_mode_1_write(ubisys_s1r, mode):
    """Test S1-R input_mode_1 writes actions for both inputs to endpoint 232."""
    input_config_cluster = ubisys_s1r.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_s1r.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysS1RInputConfigCluster.AttributeDefs.input_mode_1.name: mode}
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Actions for both inputs: input 1 with new mode, input 2 with default Toggle
        expected_actions = build_onoff_actions(0, 2, mode) + build_onoff_actions(
            1, 3, InputMode.Toggle
        )
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    assert (
        UbisysS1RInputConfigCluster.AttributeDefs.input_mode_1.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("mode", list(InputMode))
async def test_s1r_input_mode_2_write(ubisys_s1r, mode):
    """Test S1-R input_mode_2 writes actions for both inputs to endpoint 232."""
    input_config_cluster = ubisys_s1r.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_s1r.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysS1RInputConfigCluster.AttributeDefs.input_mode_2.name: mode}
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Actions for both inputs: input 1 with default Toggle, input 2 with new mode
        expected_actions = build_onoff_actions(
            0, 2, InputMode.Toggle
        ) + build_onoff_actions(1, 3, mode)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    assert (
        UbisysS1RInputConfigCluster.AttributeDefs.input_mode_2.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_s1r_detached_1(ubisys_s1r, detach):
    """Test S1-R detached_1 sends bind/unbind for EP2 -> EP1 on OnOff."""
    input_config_cluster = ubisys_s1r.endpoints[1].ubisys_input_config
    zdo = ubisys_s1r.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        zdo,
        "Unbind_req" if detach else "Bind_req",
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysS1RInputConfigCluster.AttributeDefs.detached_1.name: detach}
        )

        assert mock_req.call_count == 1
        args = mock_req.call_args[0]
        assert args[0] == ubisys_s1r.ieee
        assert args[1] == 2  # EP2
        assert args[2] == OnOff.cluster_id
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_s1r.ieee
        assert dst.endpoint == 1  # EP1

    assert (
        UbisysS1RInputConfigCluster.AttributeDefs.detached_1.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_s1r_detached_2(ubisys_s1r, detach):
    """Test S1-R detached_2 sends bind/unbind for EP3 -> EP1 on OnOff."""
    input_config_cluster = ubisys_s1r.endpoints[1].ubisys_input_config
    zdo = ubisys_s1r.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        zdo,
        "Unbind_req" if detach else "Bind_req",
        mock.AsyncMock(return_value=[0]),
    ) as mock_req:
        await input_config_cluster.write_attributes(
            {UbisysS1RInputConfigCluster.AttributeDefs.detached_2.name: detach}
        )

        assert mock_req.call_count == 1
        args = mock_req.call_args[0]
        assert args[0] == ubisys_s1r.ieee
        assert args[1] == 3  # EP3
        assert args[2] == OnOff.cluster_id
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_s1r.ieee
        assert dst.endpoint == 1  # EP1

    assert (
        UbisysS1RInputConfigCluster.AttributeDefs.detached_2.id,
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


def _build_d1_expected_actions(
    input_index: int, source_ep: int, mode: DimmerInputMode
) -> list[bytes]:
    """Build expected actions for a D1 input, dispatching by mode."""
    if mode == DimmerInputMode.Dimmer_single:
        return build_dimmer_single_actions(input_index, source_ep)
    return build_onoff_actions(input_index, source_ep, InputMode(mode))


_D1_PER_INPUT_MODES = [m for m in DimmerInputMode if m != DimmerInputMode.Dimmer_double]


@pytest.mark.parametrize("mode", _D1_PER_INPUT_MODES)
async def test_d1_input_mode_1_write(ubisys_d1, mode):
    """Test D1 input_mode_1 writes per-input actions to endpoint 232."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_d1.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.name: mode}
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Input 1 with new mode, input 2 with default Toggle
        expected_actions = _build_d1_expected_actions(
            0, 2, mode
        ) + _build_d1_expected_actions(1, 3, DimmerInputMode.Toggle)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    assert (
        UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("mode", _D1_PER_INPUT_MODES)
async def test_d1_input_mode_2_write(ubisys_d1, mode):
    """Test D1 input_mode_2 writes per-input actions to endpoint 232."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_d1.endpoints[232]

    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {UbisysD1InputConfigCluster.AttributeDefs.input_mode_2.name: mode}
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Input 1 with default Toggle, input 2 with new mode
        expected_actions = _build_d1_expected_actions(
            0, 2, DimmerInputMode.Toggle
        ) + _build_d1_expected_actions(1, 3, mode)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    assert (
        UbisysD1InputConfigCluster.AttributeDefs.input_mode_2.id,
        mode,
    ) in input_config_listener.attribute_updates


async def test_d1_dimmer_double_from_input_1(ubisys_d1):
    """Test setting input_mode_1 to Dimmer_double generates paired actions and syncs."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_d1.endpoints[232]
    zdo = ubisys_d1.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with (
        mock.patch.object(
            endpoint_232,
            "request",
            mock.AsyncMock(return_value=[0]),
        ),
        mock.patch.object(
            zdo,
            "Bind_req",
            mock.AsyncMock(return_value=[0]),
        ) as mock_bind,
    ):
        await input_config_cluster.write_attributes(
            {
                UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.name: DimmerInputMode.Dimmer_double
            }
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        expected_actions = build_dimmer_double_actions(0, 2, 1, 3)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

        # detached_2 defaults to True, so it should be re-bound
        assert mock_bind.call_count == 2  # OnOff + LevelControl for EP3

    # Both inputs should be updated to Dimmer_double
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.input_mode_2.id,
        DimmerInputMode.Dimmer_double,
    ) in input_config_listener.attribute_updates
    # detached_2 should have been reset to False
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.detached_2.id,
        t.Bool.false,
    ) in input_config_listener.attribute_updates


async def test_d1_dimmer_double_from_input_2(ubisys_d1):
    """Test setting input_mode_2 to Dimmer_double generates paired actions and syncs."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_d1.endpoints[232]
    zdo = ubisys_d1.zdo

    input_config_listener = ClusterListener(input_config_cluster)

    with (
        mock.patch.object(
            endpoint_232,
            "request",
            mock.AsyncMock(return_value=[0]),
        ),
        mock.patch.object(
            zdo,
            "Bind_req",
            mock.AsyncMock(return_value=[0]),
        ) as mock_bind,
    ):
        await input_config_cluster.write_attributes(
            {
                UbisysD1InputConfigCluster.AttributeDefs.input_mode_2.name: DimmerInputMode.Dimmer_double
            }
        )

        assert endpoint_232.request.call_count == 1

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        expected_actions = build_dimmer_double_actions(0, 2, 1, 3)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

        # detached_2 defaults to True, so it should be re-bound
        assert mock_bind.call_count == 2  # OnOff + LevelControl for EP3

    # Both inputs should be updated to Dimmer_double
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.id,
        DimmerInputMode.Dimmer_double,
    ) in input_config_listener.attribute_updates
    # detached_2 should have been reset to False
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.detached_2.id,
        t.Bool.false,
    ) in input_config_listener.attribute_updates


async def test_d1_dimmer_double_exit_resets_other(ubisys_d1):
    """Test leaving Dimmer_double resets the other input to Dimmer_single."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_d1.endpoints[232]
    zdo = ubisys_d1.zdo

    # First, set both to Dimmer_double (also re-binds detached_2)
    with (
        mock.patch.object(
            endpoint_232,
            "request",
            mock.AsyncMock(return_value=[0]),
        ),
        mock.patch.object(
            zdo,
            "Bind_req",
            mock.AsyncMock(return_value=[0]),
        ),
    ):
        await input_config_cluster.write_attributes(
            {
                UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.name: DimmerInputMode.Dimmer_double
            }
        )

    # Now change input_mode_1 to Toggle — input_mode_2 should reset to Dimmer_single
    input_config_listener = ClusterListener(input_config_cluster)

    with mock.patch.object(
        endpoint_232,
        "request",
        mock.AsyncMock(return_value=[0]),
    ):
        await input_config_cluster.write_attributes(
            {
                UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.name: DimmerInputMode.Toggle
            }
        )

        sent_data = endpoint_232.request.call_args.kwargs["data"]
        tsn = sent_data[1]

        # Both should now be per-input: Toggle + Dimmer_single
        expected_actions = _build_d1_expected_actions(
            0, 2, DimmerInputMode.Toggle
        ) + _build_d1_expected_actions(1, 3, DimmerInputMode.Dimmer_single)
        expected = _build_expected_frame(expected_actions, tsn=tsn)
        assert sent_data == expected

    # input_mode_2 should have been reset to Dimmer_single
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.input_mode_2.id,
        DimmerInputMode.Dimmer_single,
    ) in input_config_listener.attribute_updates


async def test_d1_dimmer_double_unbinds_detached(ubisys_d1):
    """Test entering Dimmer_double re-binds any detached inputs."""
    input_config_cluster = ubisys_d1.endpoints[1].ubisys_input_config
    endpoint_232 = ubisys_d1.endpoints[232]
    zdo = ubisys_d1.zdo

    # Pre-detach both inputs by setting cache directly
    input_config_cluster._attr_cache[
        UbisysD1InputConfigCluster.AttributeDefs.detached_1.id
    ] = t.Bool.true
    input_config_cluster._attr_cache[
        UbisysD1InputConfigCluster.AttributeDefs.detached_2.id
    ] = t.Bool.true

    input_config_listener = ClusterListener(input_config_cluster)

    with (
        mock.patch.object(
            endpoint_232,
            "request",
            mock.AsyncMock(return_value=[0]),
        ),
        mock.patch.object(
            zdo,
            "Bind_req",
            mock.AsyncMock(return_value=[0]),
        ) as mock_bind,
    ):
        await input_config_cluster.write_attributes(
            {
                UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.name: DimmerInputMode.Dimmer_double
            }
        )

        # Should have called Bind_req for both inputs (2 clusters each = 4 calls)
        assert mock_bind.call_count == 4

        # EP2 -> EP1 binds (OnOff + LevelControl)
        args_ep2_onoff = mock_bind.call_args_list[0][0]
        assert args_ep2_onoff[1] == 2  # EP2
        assert args_ep2_onoff[2] == OnOff.cluster_id
        assert args_ep2_onoff[3].endpoint == 1

        args_ep2_level = mock_bind.call_args_list[1][0]
        assert args_ep2_level[1] == 2  # EP2
        assert args_ep2_level[2] == LevelControl.cluster_id
        assert args_ep2_level[3].endpoint == 1

        # EP3 -> EP1 binds (OnOff + LevelControl)
        args_ep3_onoff = mock_bind.call_args_list[2][0]
        assert args_ep3_onoff[1] == 3  # EP3
        assert args_ep3_onoff[2] == OnOff.cluster_id
        assert args_ep3_onoff[3].endpoint == 1

        args_ep3_level = mock_bind.call_args_list[3][0]
        assert args_ep3_level[1] == 3  # EP3
        assert args_ep3_level[2] == LevelControl.cluster_id
        assert args_ep3_level[3].endpoint == 1

    # Both detached attributes should have been reset to False
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.detached_1.id,
        t.Bool.false,
    ) in input_config_listener.attribute_updates
    assert (
        UbisysD1InputConfigCluster.AttributeDefs.detached_2.id,
        t.Bool.false,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_d1_detached_1(ubisys_d1, detach):
    """Test D1 detached_1 sends bind/unbind for EP2 -> EP1 on OnOff + LevelControl."""
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
            {UbisysD1InputConfigCluster.AttributeDefs.detached_1.name: detach}
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
        UbisysD1InputConfigCluster.AttributeDefs.detached_1.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_d1_detached_2(ubisys_d1, detach):
    """Test D1 detached_2 sends bind/unbind for EP3 -> EP1 on OnOff + LevelControl."""
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
            {UbisysD1InputConfigCluster.AttributeDefs.detached_2.name: detach}
        )

        # Should be called twice: once for OnOff, once for LevelControl
        assert mock_req.call_count == 2

        # First call: OnOff
        args_onoff = mock_req.call_args_list[0][0]
        assert args_onoff[0] == ubisys_d1.ieee
        assert args_onoff[1] == 3  # EP3
        assert args_onoff[2] == OnOff.cluster_id
        dst = args_onoff[3]
        assert dst.endpoint == 1  # EP1

        # Second call: LevelControl
        args_level = mock_req.call_args_list[1][0]
        assert args_level[0] == ubisys_d1.ieee
        assert args_level[1] == 3  # EP3
        assert args_level[2] == LevelControl.cluster_id
        dst = args_level[3]
        assert dst.endpoint == 1  # EP1

    assert (
        UbisysD1InputConfigCluster.AttributeDefs.detached_2.id,
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


async def test_j1_config_to_standard_sync(ubisys_j1):
    """Test writing a config attr updates the corresponding standard attr."""
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    wc_listener = ClusterListener(wc_cluster)

    with mock.patch.object(
        wc_cluster.endpoint,
        "request",
        mock.AsyncMock(return_value=[0x00]),
    ):
        await wc_cluster.write_attributes(
            {
                UbisysWindowCovering.AttributeDefs.window_covering_type_config.name: WindowCovering.WindowCoveringType.Shutter
            }
        )

    # TODO: Update zigpy version
    # Standard window_covering_type should have been updated via _update_attribute
    assert (
        WindowCovering.AttributeDefs.window_covering_type.id,
        WindowCovering.WindowCoveringType.Shutter,
    ) in wc_listener.attribute_updates


async def test_j1_config_to_standard_sync_via_update(ubisys_j1):
    """Test _update_attribute on a config attr syncs the standard attr."""
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    wc_listener = ClusterListener(wc_cluster)

    # _update_attribute fires AttributeUpdatedEvent, which the handler should catch
    wc_cluster._update_attribute(
        UbisysWindowCovering.AttributeDefs.installed_closed_limit_lift_config,
        240,
    )

    assert (
        WindowCovering.AttributeDefs.installed_closed_limit_lift.id,
        240,
    ) in wc_listener.attribute_updates


async def test_j1_prepare_calibration(ubisys_j1):
    """Test prepare_calibration button resets state and writes defaults."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    # Simulate a previous calibration run
    cal_cluster._set_state(CalibrationState.Complete)

    cal_listener = ClusterListener(cal_cluster)

    with mock.patch.object(
        wc_cluster,
        "write_attributes",
        mock.AsyncMock(return_value=[[0x00]]),
    ) as mock_write:
        await cal_cluster.write_attributes(
            {UbisysJ1CalibrationCluster.AttributeDefs.prepare_calibration.name: True}
        )

        mock_write.assert_called_once()
        written_attrs = mock_write.call_args[0][0]
        attrs = UbisysWindowCovering.AttributeDefs
        assert written_attrs[attrs.installed_open_limit_lift_config] == 0x0000
        assert written_attrs[attrs.installed_closed_limit_lift_config] == 0x00F0
        assert written_attrs[attrs.installed_open_limit_tilt_config] == 0x0000
        assert written_attrs[attrs.installed_closed_limit_tilt_config] == 0x0384
        assert written_attrs[attrs.lift_to_tilt_transition_steps] == 0xFFFF
        assert written_attrs[attrs.total_steps] == 0xFFFF
        assert written_attrs[attrs.lift_to_tilt_transition_steps_2] == 0xFFFF
        assert written_attrs[attrs.total_steps_2] == 0xFFFF

    # Verify state was reset to Idle
    state_attr = UbisysJ1CalibrationCluster.AttributeDefs.calibration_state
    assert (state_attr.id, CalibrationState.Idle) in cal_listener.attribute_updates


async def test_j1_wait_until_stopped(ubisys_j1):
    """Test _wait_until_stopped polls until operational_status is 0."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering
    attr = UbisysWindowCovering.AttributeDefs.operational_status

    # Simulate motor running for 2 polls, then stopped
    poll_values = [0x01, 0x01, 0x00]
    poll_index = 0

    async def mock_read_attributes(_attrs):
        nonlocal poll_index
        wc_cluster._update_attribute(attr, poll_values[poll_index])
        poll_index += 1
        return [{}, {}]

    with (
        mock.patch.object(
            wc_cluster, "read_attributes", side_effect=mock_read_attributes
        ),
        mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
    ):
        await cal_cluster._wait_until_stopped()

    assert poll_index == 3


async def test_j1_wait_until_stopped_timeout(ubisys_j1):
    """Test _wait_until_stopped raises TimeoutError when motor doesn't stop."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering
    attr = UbisysWindowCovering.AttributeDefs.operational_status

    async def mock_read_attributes(_attrs):
        wc_cluster._update_attribute(attr, 0x01)
        return [{}, {}]

    with (
        mock.patch.object(
            wc_cluster, "read_attributes", side_effect=mock_read_attributes
        ),
        mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
        pytest.raises(TimeoutError, match="Motor did not stop"),
    ):
        await cal_cluster._wait_until_stopped()


async def test_j1_read_calibration_attributes(ubisys_j1):
    """Test _read_calibration_attributes reads all 14 calibration attrs."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    with mock.patch.object(
        wc_cluster,
        "read_attributes",
        mock.AsyncMock(return_value=[{}, {}]),
    ) as mock_read:
        await cal_cluster._read_calibration_attributes()

        mock_read.assert_called_once()
        attrs = UbisysWindowCovering.AttributeDefs
        requested = mock_read.call_args[0][0]
        assert attrs.window_covering_type_config in requested
        assert attrs.config_status_config in requested
        assert attrs.installed_open_limit_lift_config in requested
        assert attrs.installed_closed_limit_lift_config in requested
        assert attrs.installed_open_limit_tilt_config in requested
        assert attrs.installed_closed_limit_tilt_config in requested
        assert attrs.lift_to_tilt_transition_steps in requested
        assert attrs.total_steps in requested
        assert attrs.lift_to_tilt_transition_steps_2 in requested
        assert attrs.total_steps_2 in requested
        assert attrs.additional_steps in requested
        assert attrs.inactive_power_threshold in requested
        assert attrs.startup_steps in requested
        assert attrs.turnaround_guard_time in requested
        assert len(requested) == 14


@pytest.mark.parametrize(
    ("attr_name", "enable"),
    [
        (UbisysJ1CalibrationCluster.AttributeDefs.enter_calibration_mode.name, True),
        (UbisysJ1CalibrationCluster.AttributeDefs.exit_calibration_mode.name, False),
    ],
)
async def test_j1_calibration_mode(ubisys_j1, attr_name, enable):
    """Test enter/exit calibration mode does read-modify-write on mode bitmap."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    # Pre-set mode with bit 0 (motor reversed) to verify it's preserved
    existing_mode = 0x01
    mode_attr = WindowCovering.AttributeDefs.window_covering_mode
    wc_cluster._update_attribute(mode_attr, existing_mode)

    with (
        mock.patch.object(
            wc_cluster,
            "read_attributes",
            mock.AsyncMock(return_value=[{}, {}]),
        ),
        mock.patch.object(
            wc_cluster,
            "write_attributes",
            mock.AsyncMock(return_value=[[0x00]]),
        ) as mock_write,
        mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
    ):
        await cal_cluster.write_attributes({attr_name: True})

        mock_write.assert_called_once()
        written_attrs = mock_write.call_args[0][0]
        if enable:
            assert written_attrs[mode_attr] == existing_mode | 0x02
        else:
            assert written_attrs[mode_attr] == existing_mode & ~0x02


async def test_j1_auto_calibration(ubisys_j1):
    """Test run_calibration button launches and runs the full sequence."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    call_log = []

    original_set_state = cal_cluster._set_state

    def mock_set_state(state):
        call_log.append(("state", state))
        original_set_state(state)

    async def mock_set_calibration_mode(enable):
        call_log.append(("set_calibration_mode", enable))

    async def mock_wait_until_stopped():
        call_log.append(("wait_until_stopped",))

    async def mock_write_preparation_defaults():
        call_log.append(("write_preparation_defaults",))

    async def mock_read_calibration_attributes():
        call_log.append(("read_calibration_attributes",))

    async def mock_up_open():
        call_log.append(("up_open",))

    async def mock_down_close():
        call_log.append(("down_close",))

    async def mock_stop():
        call_log.append(("stop",))

    with (
        mock.patch.object(cal_cluster, "create_catching_task") as mock_task,
        mock.patch.object(cal_cluster, "_set_state", side_effect=mock_set_state),
        mock.patch.object(
            cal_cluster, "_set_calibration_mode", side_effect=mock_set_calibration_mode
        ),
        mock.patch.object(
            cal_cluster, "_wait_until_stopped", side_effect=mock_wait_until_stopped
        ),
        mock.patch.object(
            cal_cluster,
            "_write_preparation_defaults",
            side_effect=mock_write_preparation_defaults,
        ),
        mock.patch.object(
            cal_cluster,
            "_read_calibration_attributes",
            side_effect=mock_read_calibration_attributes,
        ),
        mock.patch.object(wc_cluster, "up_open", side_effect=mock_up_open),
        mock.patch.object(wc_cluster, "down_close", side_effect=mock_down_close),
        mock.patch.object(wc_cluster, "stop", side_effect=mock_stop),
        mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
    ):
        # Write the run_calibration attribute via the button
        await cal_cluster.write_attributes(
            {UbisysJ1CalibrationCluster.AttributeDefs.run_calibration.name: True}
        )

        # Verify create_catching_task was called with the coroutine
        assert mock_task.call_count == 1
        coro = mock_task.call_args[0][0]

        # Await the captured coroutine to run the full sequence
        await coro

    assert call_log == [
        # Cancel any active calibration and move to top
        ("state", CalibrationState.Moving_to_top),
        ("set_calibration_mode", False),
        ("up_open",),
        ("wait_until_stopped",),
        # Write preparation defaults (Step 2)
        ("state", CalibrationState.Writing_defaults),
        ("write_preparation_defaults",),
        # Enter calibration mode (Step 3)
        ("state", CalibrationState.Entering_calibration),
        ("set_calibration_mode", True),
        # Move down briefly, then stop (Step 4)
        ("state", CalibrationState.Moving_down),
        ("down_close",),
        ("stop",),
        # Move up to detect upper limit (Step 5)
        ("state", CalibrationState.Detecting_upper_limit),
        ("up_open",),
        ("wait_until_stopped",),
        # Move down to count steps (Step 6)
        ("state", CalibrationState.Counting_open_to_close),
        ("down_close",),
        ("wait_until_stopped",),
        # Move up to count steps (Step 7)
        ("state", CalibrationState.Counting_close_to_open),
        ("up_open",),
        ("wait_until_stopped",),
        # Exit calibration mode (Step 9)
        ("state", CalibrationState.Exiting_calibration),
        ("set_calibration_mode", False),
        # Complete
        ("state", CalibrationState.Complete),
        # Finally: read back results
        ("read_calibration_attributes",),
    ]


async def test_j1_auto_calibration_failure(ubisys_j1):
    """Test auto-calibration sets Failed state and still reads attributes on error."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration
    wc_cluster = ubisys_j1.endpoints[1].window_covering

    call_log = []

    original_set_state = cal_cluster._set_state

    def mock_set_state(state):
        call_log.append(("state", state))
        original_set_state(state)

    async def mock_set_calibration_mode(enable):
        call_log.append(("set_calibration_mode", enable))

    async def mock_wait_until_stopped():
        raise TimeoutError("Motor did not stop within 300s")

    async def mock_write_preparation_defaults():
        call_log.append(("write_preparation_defaults",))

    async def mock_read_calibration_attributes():
        call_log.append(("read_calibration_attributes",))

    async def mock_up_open():
        call_log.append(("up_open",))

    with (
        mock.patch.object(cal_cluster, "_set_state", side_effect=mock_set_state),
        mock.patch.object(
            cal_cluster, "_set_calibration_mode", side_effect=mock_set_calibration_mode
        ),
        mock.patch.object(
            cal_cluster, "_wait_until_stopped", side_effect=mock_wait_until_stopped
        ),
        mock.patch.object(
            cal_cluster,
            "_write_preparation_defaults",
            side_effect=mock_write_preparation_defaults,
        ),
        mock.patch.object(
            cal_cluster,
            "_read_calibration_attributes",
            side_effect=mock_read_calibration_attributes,
        ),
        mock.patch.object(wc_cluster, "up_open", side_effect=mock_up_open),
        mock.patch("asyncio.sleep", new_callable=mock.AsyncMock),
        pytest.raises(TimeoutError, match="Motor did not stop"),
    ):
        await cal_cluster._run_calibration()

    assert call_log == [
        # Cancel any active calibration and move to top
        ("state", CalibrationState.Moving_to_top),
        ("set_calibration_mode", False),
        ("up_open",),
        # _wait_until_stopped raises TimeoutError here
        # State set to Failed via except block
        ("state", CalibrationState.Failed),
        # finally block still reads attributes
        ("read_calibration_attributes",),
    ]


async def test_j1_config_sync_skips_failed_write(ubisys_j1):
    """Test _handle_config_attr_sync ignores failed AttributeWrittenEvents."""
    wc_cluster = ubisys_j1.endpoints[1].window_covering
    wc_listener = ClusterListener(wc_cluster)

    wc_cluster._handle_config_attr_sync(
        AttributeWrittenEvent(
            device_ieee=str(ubisys_j1.ieee),
            endpoint_id=1,
            cluster_type=0,
            cluster_id=WindowCovering.cluster_id,
            attribute_name="window_covering_type_config",
            attribute_id=0x0000,
            manufacturer_code=0x10F2,
            value=WindowCovering.WindowCoveringType.Shutter,
            status=Status.UNSUPPORTED_ATTRIBUTE,
        )
    )

    # Standard attr should NOT have been updated
    assert (
        WindowCovering.AttributeDefs.window_covering_type.id,
        WindowCovering.WindowCoveringType.Shutter,
    ) not in wc_listener.attribute_updates


async def test_j1_calibration_cluster_unknown_attribute(ubisys_j1):
    """Test write_attributes with unknown attr falls through to super()."""
    cal_cluster = ubisys_j1.endpoints[1].ubisys_j1_calibration

    # calibration_state is a known attribute but not handled in write_attributes,
    # so it falls through to super() (LocalDataCluster) which updates the cache
    cal_listener = ClusterListener(cal_cluster)
    await cal_cluster.write_attributes(
        {
            UbisysJ1CalibrationCluster.AttributeDefs.calibration_state.name: CalibrationState.Idle
        }
    )

    state_attr = UbisysJ1CalibrationCluster.AttributeDefs.calibration_state
    assert (state_attr.id, CalibrationState.Idle) in cal_listener.attribute_updates


def test_build_onoff_actions_unknown_mode():
    """Test build_onoff_actions returns empty list for unknown mode."""
    # Use an invalid mode value that doesn't match any known InputMode
    result = build_onoff_actions(0, 2, InputMode(0xFF))
    assert result == []


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
