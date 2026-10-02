"""Tests for Tuya TS000x/TS011F modules with stub (always-zero) metering clusters."""

import pytest
from zha.quirks import DEVICE_REGISTRY, TUYA_PLUG_ONOFF
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Groups, Identify, OnOff, Scenes
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.builder.metadata import ZCLEnumMetadata
from zhaquirks.tuya import (
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)

zhaquirks.setup()

STUB_METERING_EP1 = {
    Identify.cluster_id: ClusterType.Server,
    Groups.cluster_id: ClusterType.Server,
    Scenes.cluster_id: ClusterType.Server,
    OnOff.cluster_id: ClusterType.Server,
    Metering.cluster_id: ClusterType.Server,
    ElectricalMeasurement.cluster_id: ClusterType.Server,
    TuyaZBE000Cluster.cluster_id: ClusterType.Server,
    TuyaZBExternalSwitchTypeCluster.cluster_id: ClusterType.Server,
}
GANG_EP = {
    Groups.cluster_id: ClusterType.Server,
    Scenes.cluster_id: ClusterType.Server,
    OnOff.cluster_id: ClusterType.Server,
}


@pytest.mark.parametrize(
    "manufacturer,model,gangs,has_switch_type_select",
    [
        ("_TZ3000_tqlv4ug4", "TS0001", [], True),
        ("_TZ3000_prits6g4", "TS0001", [], True),
        ("_TZ3000_46t1rvdu", "TS0001", [], True),
        ("_TZ3000_fdxihpp7", "TS0001", [], True),
        ("_TZ3000_fdxihpp7", "TS000F", [], True),
        ("_TZ3000_eei0ubpy", "TS0002", [2], True),
        ("_TZ3000_lmlsduws", "TS0002", [2], True),
        ("_TZ3000_zmy4lslw", "TS0002", [2], True),
        ("_TZ3000_ly9apzky", "TS0003", [2, 3], True),
        ("_TZ3000_knoj8lpk", "TS0004", [2, 3, 4], True),
        ("_TZ3000_o1jzcxou", "TS011F", [], False),
    ],
)
def test_no_metering_quirk(
    zigpy_device_from_v2_quirk, manufacturer, model, gangs, has_switch_type_select
):
    """Devices with stub metering clusters lose them; the rest is preserved."""
    quirked = zigpy_device_from_v2_quirk(
        manufacturer,
        model,
        cluster_ids={1: dict(STUB_METERING_EP1), **{g: dict(GANG_EP) for g in gangs}},
    )

    ep1 = quirked.endpoints[1]
    assert Metering.cluster_id not in ep1.in_clusters
    assert ElectricalMeasurement.cluster_id not in ep1.in_clusters

    for ep_id in [1, *gangs]:
        onoff = quirked.endpoints[ep_id].in_clusters[OnOff.cluster_id]
        assert isinstance(onoff, TuyaZBOnOffAttributeCluster)
    assert isinstance(ep1.in_clusters[TuyaZBE000Cluster.cluster_id], TuyaZBE000Cluster)
    assert isinstance(
        ep1.in_clusters[TuyaZBExternalSwitchTypeCluster.cluster_id],
        TuyaZBExternalSwitchTypeCluster,
    )

    # Tuya spell parity with the replaced v1 EnchantedDevice quirks
    assert quirked.tuya_spell_read_attributes is True
    assert quirked.tuya_spell_data_query is False

    entry = DEVICE_REGISTRY.match_entry(quirked)
    definition = entry.zha_device_factory.quirk_definition

    # keeps backlight_mode / power_on_state selects (and child lock) working
    assert TUYA_PLUG_ONOFF in {f.feature for f in definition.exposes_features}

    switch_type_enums = [
        m
        for m in definition.entity_metadata
        if isinstance(m, ZCLEnumMetadata)
        and m.attribute_name
        == TuyaZBExternalSwitchTypeCluster.AttributeDefs.external_switch_type.name
    ]
    assert bool(switch_type_enums) is has_switch_type_select


def test_bseed_socket_without_stub_clusters(zigpy_device_from_v2_quirk):
    """The BSEED firmware flavor without metering clusters resolves to the same quirk."""
    quirked = zigpy_device_from_v2_quirk(
        "_TZ3000_o1jzcxou",
        "TS011F",
        cluster_ids={
            1: {
                Identify.cluster_id: ClusterType.Server,
                Groups.cluster_id: ClusterType.Server,
                Scenes.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
                TuyaZBE000Cluster.cluster_id: ClusterType.Server,
                TuyaZBExternalSwitchTypeCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    ep1 = quirked.endpoints[1]
    assert Metering.cluster_id not in ep1.in_clusters
    assert ElectricalMeasurement.cluster_id not in ep1.in_clusters
    assert isinstance(ep1.in_clusters[OnOff.cluster_id], TuyaZBOnOffAttributeCluster)
    assert quirked.tuya_spell_read_attributes is True


def test_metering_ts0001_variants_unaffected(zigpy_device_from_v2_quirk):
    """Fingerprints with real metering hardware keep their metering clusters."""
    quirked = zigpy_device_from_v2_quirk(
        "_TZ3000_xkap8wtb",
        "TS0001",
        cluster_ids={1: dict(STUB_METERING_EP1)},
    )
    ep1 = quirked.endpoints[1]
    assert Metering.cluster_id in ep1.in_clusters
    assert ElectricalMeasurement.cluster_id in ep1.in_clusters
