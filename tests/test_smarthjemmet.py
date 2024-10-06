"""Tests for smarthjemmet.dk quirks."""

import pytest
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, OnOff, OnOffConfiguration

import zhaquirks
from zhaquirks.smarthjemmet.quadzigsw import (
    QUAD_ZIG_SW_V1,
    QUAD_ZIG_SW_V2,
    CR2032PowerConfigurationCluster,
    CustomMultistateInputCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize("quirk_cls", [QUAD_ZIG_SW_V1, QUAD_ZIG_SW_V2])
async def test_quad_zig_sw_signature(zigpy_device_from_quirk, quirk_cls):
    """Test the endpoints and clusters for QUAD-ZIG-SW device."""

    device = zigpy_device_from_quirk(quirk_cls)

    ep1 = device.endpoints[1]
    assert ep1.profile_id == zha.PROFILE_ID
    assert ep1.device_type == 65534 or 6
    assert set(ep1.in_clusters.keys()) == {
        Basic.cluster_id,
        CR2032PowerConfigurationCluster.cluster_id,
    } or {
        Basic.cluster_id,
        CR2032PowerConfigurationCluster.cluster_id,
        OnOffConfiguration.cluster_id,
    }
    assert set(ep1.out_clusters.keys()) == {
        Basic.cluster_id,
        CR2032PowerConfigurationCluster.cluster_id,
        CustomMultistateInputCluster.cluster_id,
    } or {
        Basic.cluster_id,
        CR2032PowerConfigurationCluster.cluster_id,
        CustomMultistateInputCluster.cluster_id,
        OnOff.cluster_id,
    }

    for endpoint_id in range(2, 6):
        ep = device.endpoints[endpoint_id]
        assert ep.profile_id == zha.PROFILE_ID
        assert ep.device_type == 65534 or 6
        assert set(ep.in_clusters.keys()) == {
            CustomMultistateInputCluster.cluster_id,
            OnOff.cluster_id,
        } or {OnOffConfiguration.cluster_id}
        assert set(ep.out_clusters.keys()) == {
            CustomMultistateInputCluster.cluster_id
        } or {CustomMultistateInputCluster.cluster_id, OnOff.cluster_id}
