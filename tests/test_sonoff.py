"""Test Sonoff devices."""

from zigpy.zcl.clusters.general import Basic

import zhaquirks
from zhaquirks.sonoff.zbminil2 import BasicConfigCluster

zhaquirks.setup()


async def test_basic_cluster_zbminil2(zigpy_device_from_v2_quirk):
    """Make sure the basic cluster returns Mains power."""

    device = zigpy_device_from_v2_quirk(model="ZBMINIL2", manufacturer="SONOFF")

    basic_cluster: BasicConfigCluster = device.endpoints[1].in_clusters[
        Basic.cluster_id
    ]
    assert isinstance(basic_cluster, BasicConfigCluster)

    attrs, fail = await basic_cluster.read_attributes(
        [Basic.AttributeDefs.power_source]
    )
    assert (
        attrs[Basic.AttributeDefs.power_source] == Basic.PowerSource.Mains_single_phase
    )
    assert len(fail) == 0
