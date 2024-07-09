"""Tests for Philips RDM004 quirks."""
import pytest

from tests.common import ClusterListener

import zhaquirks
import zhaquirks.philips.PhilipsRDM001
import zhaquirks.philips.PhilipsRDM004

zhaquirks.setup()

@pytest.mark.parametrize("quirk", (zhaquirks.philips.PhilipsRDM001.bind,))
async def test_singleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test philips single switch bind attributes."""
    switch_dev = zigpy_device_from_quirk(quirk)
    switch_cluster = switch_dev.endpoints[1]
    switch_listener = ClusterListener(switch_cluster.OnOff)

    assert switch_listener.cluster_commands[1][4] == "left" #remote cluster = 
