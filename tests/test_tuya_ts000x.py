"""Test the Tuya TS000X switch module quirks."""

import pytest
from zha.application import Platform
from zha.application.platforms.switch import Switch
from zha.quirks import DEVICE_REGISTRY, TUYA_PLUG_ONOFF

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks.tuya.ts000x  # noqa: F401


@pytest.mark.parametrize(
    ("diagnostics", "ieee", "endpoints"),
    [
        # Switch_1G_GPP
        ("tz3000-p26flek3-ts0001-0x00000053.json", "ab:cd:ef:12:37:1f:21:53", (1,)),
        # Switch_1G_Metering
        ("tz3000-tqlv4ug4-ts0001-0x00000048.json", "ab:cd:ef:12:ab:aa:f0:9a", (1,)),
        # Switch_3G_Metering
        (
            "tz3000-mw1pqqqt-ts0003-0x0000004a.json",
            "ab:cd:ef:12:2c:e2:6d:88",
            (1, 2, 3),
        ),
        # Switch_4G_GPP
        (
            "tz3000-u3oupgdy-ts0004-0x00000050.json",
            "ab:cd:ef:12:64:23:80:ed",
            (1, 2, 3, 4),
        ),
    ],
)
async def test_switch_module_has_switch_and_disabled_light(
    diagnostics: str, ieee: str, endpoints: tuple[int, ...]
) -> None:
    """Test that every gang is a switch, and its light is disabled by default."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, diagnostics, DEVICE_REGISTRY
        )

        assert TUYA_PLUG_ONOFF in device.exposes_features

        for endpoint_id in endpoints:
            light = device.get_platform_entity(
                Platform.LIGHT, unique_id=f"{ieee}-{endpoint_id}"
            )
            switch = device.get_platform_entity(
                Platform.SWITCH, unique_id=f"{ieee}-{endpoint_id}-switch"
            )

            # The light keeps its unique ID, so existing installations keep it
            assert light.entity_registry_enabled_default is False
            assert type(switch) is Switch
            assert switch.entity_registry_enabled_default is True
            assert switch.endpoint.id == endpoint_id
