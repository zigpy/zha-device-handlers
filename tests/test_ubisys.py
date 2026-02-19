"""Tests for ubisys quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.common import ClusterListener
from zhaquirks.ubisys.switch_s1 import (
    _INPUT_ACTION_TEMPLATES,
    InputMode,
    UbisysCluster,
    UbisysInputConfigCluster,
)


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


@pytest.mark.parametrize(
    "mode",
    [
        InputMode.Toggle,
        InputMode.Toggle_switch,
        InputMode.On_off_switch,
    ],
)
async def test_input_mode_write(ubisys_s1, mode):
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
        expected = _build_expected_frame(_INPUT_ACTION_TEMPLATES[mode], tsn=tsn)
        assert sent_data == expected

    # Verify local cache was updated
    assert (
        UbisysInputConfigCluster.AttributeDefs.input_mode.id,
        mode,
    ) in input_config_listener.attribute_updates


@pytest.mark.parametrize("detach", [True, False])
async def test_detached_mode(ubisys_s1, detach):
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
        assert args[1] == UbisysInputConfigCluster.INPUT_ENDPOINT
        # Cluster
        assert args[2] == OnOff.cluster_id
        # Destination: self-bind to output endpoint
        dst = args[3]
        assert dst.addrmode == 0x03
        assert dst.ieee == ubisys_s1.ieee
        assert dst.endpoint == UbisysInputConfigCluster.OUTPUT_ENDPOINT

    # Verify local cache was updated
    assert (
        UbisysInputConfigCluster.AttributeDefs.detached.id,
        t.Bool(detach),
    ) in input_config_listener.attribute_updates
