"""Tests for NodOn quirks."""

from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import DeviceTemperature
from zigpy.zcl.clusters.measurement import RelativeHumidity
from zigpy.zcl.clusters.smartenergy import Metering

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
from zhaquirks.nodon.pilot_wire import NodOnPilotWireCluster, NodOnPilotWireMode


async def test_nodon_fps_4_1_00_entities():
    """Test the entities created for the NodOn FPS-4-1-00 pilot wire module."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "nodon-fps-4-1-00-0x00000202.json", DEVICE_REGISTRY
        )
        endpoint = device.device.endpoints[1]

        assert isinstance(
            endpoint.in_clusters[NodOnPilotWireCluster.cluster_id],
            NodOnPilotWireCluster,
        )
        assert RelativeHumidity.cluster_id not in endpoint.in_clusters

        pilot_wire_mode = device.get_platform_entity(
            Platform.SELECT, unique_id=f"{device.ieee}-1-pilot_wire_mode"
        )
        assert pilot_wire_mode.current_option == NodOnPilotWireMode.FrostProtection.name

        power = device.get_platform_entity(
            Platform.SENSOR, unique_id=f"{device.ieee}-1-{Metering.cluster_id}"
        )
        assert power.translation_key == "power"
        assert power.fallback_name == "Power"

        energy = device.get_platform_entity(
            Platform.SENSOR,
            unique_id=f"{device.ieee}-1-{Metering.cluster_id}-summation_delivered",
        )
        assert energy.translation_key != "power"

        unique_ids = {entity.unique_id for entity in device.platform_entities.values()}
        assert f"{device.ieee}-1-{RelativeHumidity.cluster_id}" not in unique_ids
        assert f"{device.ieee}-1-{DeviceTemperature.cluster_id}" not in unique_ids
