"""Test the `light_as_switch` quirk builder method."""

from unittest.mock import AsyncMock, patch

from zha.application import Platform
from zha.application.platforms.switch import Switch
from zha.quirks import DeviceRegistry
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import Status

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
from zhaquirks.builder import QuirkBuilder
from zhaquirks.tuya import (
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)

IEEE = "ab:cd:ef:12:37:1f:21:53"


def _tuya_ts0001_quirk(registry: DeviceRegistry, *, light_as_switch: bool):
    """Build a quirk for the TS0001 in the diagnostics file."""
    builder = (
        QuirkBuilder("_TZ3000_p26flek3", "TS0001")
        .replaces(TuyaZBOnOffAttributeCluster)
        .replaces(TuyaZBE000Cluster)
        .replaces(TuyaZBExternalSwitchTypeCluster)
    )

    if light_as_switch:
        builder = builder.light_as_switch()

    builder.add_to_registry(registry)


async def test_light_as_switch() -> None:
    """Test that a switch is added, and the light is disabled by default."""
    registry = DeviceRegistry()
    _tuya_ts0001_quirk(registry, light_as_switch=True)

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "tz3000-p26flek3-ts0001-0x00000053.json", registry
        )
        light = device.get_platform_entity(Platform.LIGHT, unique_id=f"{IEEE}-1")
        switch = device.get_platform_entity(
            Platform.SWITCH, unique_id=f"{IEEE}-1-switch"
        )

        # The light keeps its unique ID, so existing installations keep their entity
        assert light.entity_registry_enabled_default is False
        assert light.primary is False

        assert type(switch) is Switch
        assert switch.entity_registry_enabled_default is True
        # The switch takes over the primary entity of the light (by weight)
        assert device.primary_entity is switch
        assert (
            switch.cluster is device.device.endpoints[1].in_clusters[OnOff.cluster_id]
        )

        # The switch controls the relay with the On/Off commands
        cluster = switch.cluster

        with patch.object(
            cluster,
            "on",
            new=AsyncMock(return_value=[OnOff.ServerCommandDefs.on.id, Status.SUCCESS]),
        ) as on:
            await switch.async_turn_on()

        on.assert_awaited_once_with()


async def test_no_light_as_switch() -> None:
    """Test that a quirk without `light_as_switch` keeps the plain light."""
    registry = DeviceRegistry()
    _tuya_ts0001_quirk(registry, light_as_switch=False)

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "tz3000-p26flek3-ts0001-0x00000053.json", registry
        )
        light = device.get_platform_entity(Platform.LIGHT, unique_id=f"{IEEE}-1")

        assert light.entity_registry_enabled_default is True
        assert (Platform.SWITCH, f"{IEEE}-1-switch") not in device.platform_entities
