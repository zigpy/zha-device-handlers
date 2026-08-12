"""Tests for LiXee ZLinky_TIC quirks."""

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.lixee import LIXEE, ZLINKY_MANUFACTURER_CLUSTER_ID
from zhaquirks.lixee.zlinky import ZLinkyTICManufacturerCluster, ZLinkyTICMetering
from zhaquirks.tuya import TuyaManufCluster

zhaquirks.setup()


def _zlinky_definition():
    """Return the QuirkDefinition registered for the ZLinky_TIC."""
    (entry,) = [
        entry
        for entry in DEVICE_REGISTRY
        if isinstance(entry.zha_device_factory, QuirkV2Factory)
        and any(
            model_info.manufacturer == LIXEE and model_info.model == "ZLinky_TIC"
            for model_info in entry.device_match.applies_to
        )
    ]
    return entry.zha_device_factory.quirk_definition


def test_zlinky_clusters_replaced(zigpy_device_from_v2_quirk) -> None:
    """Test that the ZLinky_TIC quirk replaces the expected clusters."""
    device = zigpy_device_from_v2_quirk(
        LIXEE,
        "ZLinky_TIC",
        cluster_ids={
            1: {
                Metering.cluster_id: None,
                ZLINKY_MANUFACTURER_CLUSTER_ID: None,
            }
        },
    )
    endpoint = device.endpoints[1]

    assert isinstance(endpoint.smartenergy_metering, ZLinkyTICMetering)
    assert isinstance(
        endpoint.zlinky_manufacturer_specific, ZLinkyTICManufacturerCluster
    )
    # Not all firmware variants report it, the quirk adds it unconditionally
    assert PowerConfiguration.cluster_id in endpoint.in_clusters


def test_zlinky_tariff_entities() -> None:
    """Test that the tariff and diagnostic sensors are exposed."""
    attribute_defs = ZLinkyTICManufacturerCluster.AttributeDefs
    definition = _zlinky_definition()

    assert {
        entity_metadata.attribute_name for entity_metadata in definition.entity_metadata
    } == {
        attribute_defs.linky_tariff_period.name,
        attribute_defs.hist_tariff_option_or_std_supplier_price_schedule_name.name,
        attribute_defs.hist_subscribed_power_exceeding_warning.name,
        attribute_defs.hist_schedule_peak_hours_off_peak_hours.name,
        attribute_defs.linky_status.name,
        attribute_defs.linky_mode.name,
    }

    # Every entity reads from the manufacturer specific cluster on endpoint 1
    for entity_metadata in definition.entity_metadata:
        assert entity_metadata.cluster_id == ZLINKY_MANUFACTURER_CLUSTER_ID
        assert entity_metadata.endpoint_id == 1


def test_zlinky_tuya_cluster_removed(zigpy_device_from_v2_quirk) -> None:
    """Test that the Tuya cluster firmware v14+ reports is removed."""
    device = zigpy_device_from_v2_quirk(
        LIXEE,
        "ZLinky_TIC",
        cluster_ids={
            1: {
                ZLINKY_MANUFACTURER_CLUSTER_ID: None,
                TuyaManufCluster.cluster_id: ClusterType.Server,
            }
        },
    )
    endpoint = device.endpoints[1]

    assert TuyaManufCluster.cluster_id not in endpoint.in_clusters
    assert TuyaManufCluster.cluster_id not in endpoint.out_clusters
