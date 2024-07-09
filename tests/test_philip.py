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

@pytest.mark.parametrize("quirk", (zhaquirks.philips.PhilipsRDM001.bind,))
async def test_singleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test philips single switch bind attributes"""
    switch_dev = zigpy_device_from_quirk(quirk)
    switch_cluster = switch_dev.endpoints[1].on_off
    switch_listener = ClusterListener(switch_cluster)
