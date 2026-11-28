"""Tests for Heiman custom quirks."""

import json
from pathlib import Path

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import DeviceTemperature, PollControl
from zigpy.zcl.clusters.security import IasWd, IasZone

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks.heiman.hs1rm_e
import zhaquirks.heiman.smoke  # noqa: F401

zhaquirks.setup()

CURRENT_TEMP_ID = DeviceTemperature.AttributeDefs.current_temperature.id
MIN_TEMP_ID = DeviceTemperature.AttributeDefs.min_temp_experienced.id


def test_heiman_hs1rm_e_temperature_scaling(zigpy_device_from_v2_quirk):
    """Test that the Heiman HS1RM-E scales raw device temperatures by 100."""
    device = zigpy_device_from_v2_quirk("HEIMAN", "RelayModule-EF-3.0")
    device_temp_cluster = device.endpoints[1].device_temperature

    # current_temperature is scaled *100 to centidegrees for ZHA's /100 divisor
    device_temp_cluster.update_attribute(CURRENT_TEMP_ID, 25)
    assert device_temp_cluster.get(CURRENT_TEMP_ID) == 2500

    # other attributes pass through unchanged
    device_temp_cluster.update_attribute(MIN_TEMP_ID, 25)
    assert device_temp_cluster.get(MIN_TEMP_ID) == 25

    # a None current_temperature must not raise (no multiplication)
    device_temp_cluster.update_attribute(CURRENT_TEMP_ID, None)
    assert device_temp_cluster.get(CURRENT_TEMP_ID) is None


@pytest.mark.parametrize(
    "model", ["SmokeSensor-N-3.0", "SmokeSensor-EF-3.0", "SmokeSensor-EM"]
)
@pytest.mark.parametrize(
    "extra_clusters",
    [
        {},
        # SmokeSensor-EF-3.0 exists both with and without PollControl
        {PollControl.cluster_id: ClusterType.Server},
    ],
)
def test_heiman_smoke_sensor_has_no_siren(
    zigpy_device_from_v2_quirk, model, extra_clusters
):
    """The IAS WD cluster is removed whatever other clusters the firmware has."""
    device = zigpy_device_from_v2_quirk(
        "HEIMAN",
        model,
        cluster_ids={
            1: {
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                **extra_clusters,
            }
        },
    )

    assert IasWd.cluster_id not in device.endpoints[1].in_clusters
    assert IasZone.cluster_id in device.endpoints[1].in_clusters


async def test_heiman_smoke_ef_3_0_zha_entities():
    """No siren or siren settings for a SmokeSensor-EF-3.0 without PollControl."""
    diagnostics_file = "heiman-smokesensor-ef-3-0.json"
    diagnostics = json.loads(
        (Path(__file__).parent / "data" / "devices" / diagnostics_file).read_text()
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, diagnostics_file, DEVICE_REGISTRY
        )

        assert {
            (platform, unique_id)
            for platform, unique_id in device.platform_entities
            if platform != Platform.VIRTUAL
        } == {
            (Platform(platform), entity["unique_id"])
            for platform, entities in diagnostics["zha_lib_entities"].items()
            for entity in entities
        }
        assert not {
            platform
            for platform, _ in device.platform_entities
            if platform in (Platform.SIREN, Platform.SELECT)
        }
