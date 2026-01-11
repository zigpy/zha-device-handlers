"""Tests for CentraLite quirks."""

import pytest
from unittest import mock
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasAce

import zhaquirks
from zhaquirks.centralite import cl_3400_G
from zhaquirks.const import MOTION_EVENT

zhaquirks.setup()

CENTRALITE = "CentraLite"


@pytest.mark.asyncio
async def test_centralite_3400g_quirk_loads(zigpy_device_from_v2_quirk):
    """Test that CentraLite 3400-G quirk loads correctly."""
    device = zigpy_device_from_v2_quirk(CENTRALITE, "3400-G")

    # Verify device loaded with correct type
    assert isinstance(device, cl_3400_G.CentraLiteDeviceV2)

    # Verify motion_bus exists
    assert hasattr(device, "motion_bus")

    # Check endpoint 1 has custom power cluster
    ep1 = device.endpoints[1]
    assert ep1.power is not None
    assert isinstance(ep1.power, cl_3400_G.CustomPowerConfigurationCluster)

    # Check voltage range is set correctly for CR123A batteries
    assert ep1.power.MIN_VOLTS == 2.1
    assert ep1.power.MAX_VOLTS == 3.0

    # Verify custom IAS ACE output cluster
    ias_ace = ep1.out_clusters.get(0x0501)
    assert ias_ace is not None
    assert isinstance(ias_ace, cl_3400_G.CustomIasAce)

    # Check endpoint 2 has virtual motion sensor
    assert 2 in device.endpoints
    ep2 = device.endpoints[2]
    assert ep2.ias_zone is not None
    assert isinstance(ep2.ias_zone, cl_3400_G.MotionCluster)


@pytest.mark.asyncio
async def test_centralite_3400g_motion_trigger(zigpy_device_from_v2_quirk):
    """Test that GetPanelStatus command triggers motion event."""
    device = zigpy_device_from_v2_quirk(CENTRALITE, "3400-G")

    # Get the IAS ACE cluster
    ias_ace = device.endpoints[1].out_clusters[IasAce.cluster_id]

    # Mock the motion_bus listener_event to verify it gets called
    with mock.patch.object(device.motion_bus, "listener_event") as mock_listener:
        # Create GetPanelStatus command header
        hdr = foundation.ZCLHeader.cluster(
            tsn=1,
            command_id=IasAce.ServerCommandDefs.get_panel_status.id,
        )

        # Trigger the command
        ias_ace.handle_cluster_request(hdr, [])

        # Verify motion event was triggered on the bus
        mock_listener.assert_called_once_with(MOTION_EVENT)
