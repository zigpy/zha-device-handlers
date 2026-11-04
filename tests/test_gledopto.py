"""Tests for GLEDOPTO quirks."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

import zhaquirks
import zhaquirks.gledopto.glc009

zhaquirks.setup()


def test_gledopto_glc009_signature(assert_signature_matches_quirk):
    """Test GLEDOPTO GL-C-009 signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=0, maximum_buffer_size=80, maximum_incoming_transfer_size=160, server_mask=0, maximum_outgoing_transfer_size=160, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "11": {
                "profile_id": 49246,
                "device_type": "0x0100",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0300",
                ],
                "out_clusters": [],
            },
            "13": {
                "profile_id": 49246,
                "device_type": "0x0100",
                "in_clusters": ["0x1000"],
                "out_clusters": ["0x1000"],
            },
        },
        "manufacturer": "GLEDOPTO",
        "model": "GL-C-009",
        "class": "zigpy.device.Device",
    }

    assert_signature_matches_quirk(zhaquirks.gledopto.glc009.GLC009, signature)


@pytest.mark.parametrize("endpoint_id", [1, 11])
def test_gledopto_glc009p_removes_color_cluster(
    zigpy_device_from_v2_quirk, endpoint_id
):
    """Test the GL-C-009P quirk removes Color from the light endpoint it has.

    Older firmware exposes the light on endpoint 1 (plus Green Power endpoint 242),
    newer firmware on endpoint 11.
    """
    light_clusters = dict.fromkeys(
        (
            Basic.cluster_id,
            Identify.cluster_id,
            Groups.cluster_id,
            Scenes.cluster_id,
            OnOff.cluster_id,
            LevelControl.cluster_id,
            Color.cluster_id,
            LightLink.cluster_id,
        ),
        ClusterType.Server,
    )
    light_clusters[Ota.cluster_id] = ClusterType.Client
    cluster_ids = {endpoint_id: light_clusters}
    if endpoint_id == 1:
        cluster_ids[242] = {GreenPowerProxy.cluster_id: ClusterType.Client}

    device = zigpy_device_from_v2_quirk(
        "GLEDOPTO", "GL-C-009P", endpoint_ids=[], cluster_ids=cluster_ids
    )

    endpoint = device.endpoints[endpoint_id]
    assert Color.cluster_id not in endpoint.in_clusters
    assert OnOff.cluster_id in endpoint.in_clusters
    assert LevelControl.cluster_id in endpoint.in_clusters
