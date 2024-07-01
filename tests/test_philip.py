"""Tests for Philips RDM004 quirks."""

import asyncio
import datetime
from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, get_device
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration

from tests.common import ClusterListener, MockDatetime, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATUS_CHANGE_COMMAND,
)
from zhaquirks.philips import Data, PhilipsBasicCluster, PhilipsRemoteCluster
import zhaquirks.philips.PhilipsRDM001
import zhaquirks.philips.PhilipsRDM004

zhaquirks.setup()

@pytest.mark.parametrize("quirk", (zhaquirk.sphilips.PhilipsRDM001.bind,))
async def test_singleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test philips single switch bind attributes"""
    switch_dev = zigpy_device_from_quirk(quirk)
    switch_cluster = switch_dev.endpoints[1].on_off
    switch_listener = ClusterListener(switch_cluster)
  
    hdr, args = tuya_cluster.deserialize(SHORT_PRESS)
    tuya_cluster.handle_message(hdr, args)
    hdr, args = tuya_cluster.deserialize(SHORT_RELEASE)
    tuya_cluster.handle_message(hdr, args)

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == TURN_ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == TURN_ON
