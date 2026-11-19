"""Tests for Adeo quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import KeepAlive, Ota


@pytest.mark.parametrize("model", ["ZBEK-1", "ZBEK-4"])
@pytest.mark.parametrize("advertises_keepalive", [False, True])
async def test_zbek_keepalive(zigpy_device_mock, model, advertises_keepalive):
    """Expose KeepAlive as a client whether or not the bulb advertises it."""
    raw_device = zigpy_device_mock()
    raw_device.manufacturer = "Adeo"
    raw_device.model = model
    raw_endpoint = raw_device.add_endpoint(1)
    raw_endpoint.add_output_cluster(Ota.cluster_id)
    keepalive_base = KeepAlive.AttributeDefs.tc_keep_alive_base.id
    if advertises_keepalive:
        raw_endpoint.add_output_cluster(KeepAlive.cluster_id).update_attribute(
            keepalive_base, 10
        )

    device = DEVICE_REGISTRY.resolve(raw_device)
    endpoint = device.endpoints[1]

    assert set(endpoint.out_clusters) == {Ota.cluster_id, KeepAlive.cluster_id}
    keepalive = endpoint.out_clusters[KeepAlive.cluster_id]
    assert isinstance(keepalive, KeepAlive)
    assert keepalive.is_client
    assert KeepAlive.cluster_id not in endpoint.in_clusters
    if advertises_keepalive:
        assert keepalive.get(keepalive_base) == 10
