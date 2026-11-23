"""Tests for the XYZROE / DIYRuZ intercom adapter."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zha.zigbee.cluster_config import (
    aggregate_cluster_configs,
    configure_cluster_configs,
)
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, OnOff, PowerConfiguration

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.xyzroe.zintercom import (
    DIYZintercomDoorLockCluster,
    DIYZintercomPowerConfigurationCluster,
    ZintercomState,
)

zhaquirks.setup()


@pytest.fixture
def intercom(zigpy_device_from_v2_quirk):
    """Create an intercom with the original sparse simple descriptor."""
    return zigpy_device_from_v2_quirk(
        "xyzroe",
        "DIY_Zintercom",
        cluster_ids={
            1: {OnOff.cluster_id: ClusterType.Client, 0x0101: ClusterType.Client}
        },
    )


@pytest.mark.parametrize("manufacturer", ["xyzroe", "DIYRuZ"])
@pytest.mark.parametrize("server_clusters", [False, True])
def test_descriptor_variants(
    zigpy_device_from_v2_quirk, manufacturer, server_clusters
) -> None:
    """Match both names and descriptors without losing the original clusters."""
    clusters = {OnOff.cluster_id: ClusterType.Client, 0x0101: ClusterType.Client}
    if server_clusters:
        # The fixture cannot represent a cluster in both directions; this still
        # covers firmware advertising the management cluster as a server.
        clusters[PowerConfiguration.cluster_id] = ClusterType.Server
        clusters[DIYZintercomDoorLockCluster.cluster_id] = ClusterType.Server
    device = zigpy_device_from_v2_quirk(
        manufacturer, "DIY_Zintercom", cluster_ids={1: clusters}
    )
    endpoint = device.endpoints[1]
    assert isinstance(endpoint.basic, Basic)
    assert isinstance(endpoint.zintercom, DIYZintercomDoorLockCluster)
    assert isinstance(endpoint.power, DIYZintercomPowerConfigurationCluster)
    assert OnOff.cluster_id in endpoint.out_clusters
    state = endpoint.zintercom.AttributeDefs.state
    assert not state.access & foundation.ZCLAttributeAccess.Write
    assert not endpoint.zintercom.server_commands


async def test_real_report_frame(intercom) -> None:
    """Decode the firmware's real enum8 state, enum8 mode and boolean sound."""
    cluster = intercom.endpoints[1].zintercom
    frame = bytes.fromhex("18 01 0a 50 00 30 01 51 00 30 00 52 00 10 01")
    header, command = cluster.deserialize(frame)
    cluster.handle_message(header, command)
    await asyncio.sleep(0)
    assert cluster.get("state") == ZintercomState.Ring
    assert cluster.get("mode") == 0
    assert cluster.get("sound") == 1


@pytest.mark.parametrize(
    "name", ["time_ring", "time_talk", "time_open", "time_bell", "time_report"]
)
async def test_timer_write_wire_type(intercom, name) -> None:
    """Write exactly one uint8 without a manufacturer-specific header."""
    cluster = intercom.endpoints[1].zintercom
    cluster._write_attributes = AsyncMock(
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
    )
    await cluster.write_attributes({name: 1})
    record = cluster._write_attributes.call_args.args[0][0]
    assert record.attrid == cluster.attributes_by_name[name].id
    assert record.value.type == foundation.DataTypeId.uint8
    assert record.value.value.serialize() == b"\x01"
    assert cluster._write_attributes.call_args.kwargs.get("manufacturer") is None


async def test_battery_report_and_unknown_cache(intercom) -> None:
    """Keep raw battery units and normalize unknown cached measurements."""
    power = intercom.endpoints[1].power
    header, command = power.deserialize(
        bytes.fromhex("18 02 0a 21 00 20 64 20 00 20 1e")
    )
    power.handle_message(header, command)
    await asyncio.sleep(0)
    assert power.get("battery_percentage_remaining") == 100
    assert power.get("battery_voltage") == 30
    # Restoring a quirk's cache bypasses _update_attribute.
    power._attr_cache[PowerConfiguration.AttributeDefs.battery_voltage.id] = 255
    power._attr_cache[
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    ] = 255
    assert power.get("battery_voltage") is None
    assert power.get("battery_percentage_remaining") is None


@pytest.mark.parametrize("state", list(ZintercomState))
async def test_state_updates_do_not_poll_battery(intercom, state) -> None:
    """Leave battery delivery to standard reporting, even after Idle."""
    power = intercom.endpoints[1].power
    power.read_attributes = AsyncMock()
    intercom.endpoints[1].zintercom.update_attribute(
        DIYZintercomDoorLockCluster.AttributeDefs.state.id, state
    )
    await asyncio.sleep(0)
    power.read_attributes.assert_not_called()


async def test_entities_from_device_diagnostics() -> None:
    """Create real ZHA entities from the anonymized physical device diagnostics."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "xyzroe-diy-zintercom.json", DEVICE_REGISTRY
        )
        ieee = str(device.device.ieee)
        cluster = device.device.endpoints[1].zintercom
        call = device.get_platform_entity(Platform.SENSOR, f"{ieee}-1-state")
        ringing = device.get_platform_entity(
            Platform.BINARY_SENSOR, f"{ieee}-1-ringing"
        )
        opening = device.get_platform_entity(
            Platform.BINARY_SENSOR, f"{ieee}-1-opening_signal"
        )
        cluster.update_attribute(cluster.AttributeDefs.state.id, ZintercomState.Ring)
        assert ringing.is_on
        assert not opening.is_on
        assert call.native_value == "Ring"
        cluster.update_attribute(cluster.AttributeDefs.state.id, ZintercomState.Open)
        assert not ringing.is_on
        assert opening.is_on
        assert call.native_value == "Open"
        # Preserve the legacy call-active entity rather than creating a second one.
        assert (
            device.get_platform_entity(
                Platform.BINARY_SENSOR, f"{ieee}-1-{OnOff.cluster_id}"
            ).device_class
            == "sound"
        )
        batteries = [
            entity
            for entity in device.platform_entities.values()
            if type(entity).__name__ == "Battery"
        ]
        assert len(batteries) == 1
        assert batteries[0].native_value == 100
        # The standard battery entity binds Power Configuration and configures
        # both firmware-reportable measurements without custom wake polling.
        configs = aggregate_cluster_configs(device.platform_entities.values())
        power_config = configs[(1, PowerConfiguration.cluster_id, True)]
        assert power_config.bind
        for name in ("battery_voltage", "battery_percentage_remaining"):
            config = power_config.attributes[name]
            assert config.read_on_startup
            assert config.reporting is not None
            assert config.reporting.min_interval == 3600
            assert config.reporting.max_interval == 10800
            assert config.reporting.reportable_change == 1
        power = device.device.endpoints[1].power
        power.bind.reset_mock()
        power.configure_reporting_multiple.reset_mock()
        await configure_cluster_configs(
            device, {(1, PowerConfiguration.cluster_id, True): power_config}
        )
        power.bind.assert_awaited_once()
        reports = power.configure_reporting_multiple.call_args.args[0]
        assert {attribute.name for attribute in reports} == {
            "battery_voltage",
            "battery_percentage_remaining",
        }
        header, report = power.deserialize(bytes.fromhex("18 03 0a 21 00 20 96"))
        power.handle_message(header, report)
        assert batteries[0].native_value == 75
        timer = device.get_platform_entity(Platform.NUMBER, f"{ieee}-1-time_talk")
        assert timer.native_min_value == 1
        assert timer.native_max_value == 32


def test_other_manufacturer_not_matched(zigpy_device_from_v2_quirk) -> None:
    """Do not apply this device-specific handler to unrelated manufacturers."""
    device = zigpy_device_from_v2_quirk("Other", "DIY_Zintercom")
    assert DIYZintercomDoorLockCluster.cluster_id not in device.endpoints[1].in_clusters
