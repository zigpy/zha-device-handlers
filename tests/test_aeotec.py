"""Tests for Aeotec."""

from zha.application import Platform
from zha.application.platforms import EntityCategory
from zha.quirks import DEVICE_REGISTRY

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.aeotec.pico_switch import WholeDegreeDeviceTemperature

zhaquirks.setup()


async def test_pico_switch_device_temperature():
    """Test that the device temperature is not divided by 100."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "aeotec-zga002-0x00000106.json", DEVICE_REGISTRY
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="ab:cd:ef:12:d0:1d:eb:0b-1-2"
        )

        assert type(entity) is WholeDegreeDeviceTemperature
        assert entity.native_value == 34
        assert entity.entity_category == EntityCategory.DIAGNOSTIC


async def test_pico_duo_switch_device_temperature():
    """Test that the device temperature is not divided by 100."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "aeotec-zga003-0x00000106.json", DEVICE_REGISTRY
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="ab:cd:ef:12:45:ea:a1:6c-1-2"
        )

        assert type(entity) is WholeDegreeDeviceTemperature
        assert entity.native_value == 17
        assert entity.entity_category == EntityCategory.DIAGNOSTIC


async def test_pico_duo_switch_child_devices():
    """Test that each input's settings are on the child device of its relay."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "aeotec-zga003-0x00000106.json", DEVICE_REGISTRY
        )

        assert {
            child_id: set(child.endpoint_ids)
            for child_id, child in device.child_devices.items()
        } == {"1": {1, 3}, "2": {2, 4}}

        def child_device_id(platform: Platform, suffix: str) -> str | None:
            entity = device.get_platform_entity(
                platform, unique_id=f"{device.ieee}-{suffix}"
            )
            return entity.child_device.id if entity.child_device is not None else None

        # S1 (endpoint 3) controls relay 1, S2 (endpoint 4) controls relay 2
        for relay, input_endpoint_id in (("1", 3), ("2", 4)):
            assert child_device_id(Platform.SWITCH, f"{relay}-6") == relay
            assert (
                child_device_id(Platform.SWITCH, f"{input_endpoint_id}-controls")
                == relay
            )
            for attribute_name in ("switch_type", "switch_actions"):
                assert (
                    child_device_id(
                        Platform.SELECT, f"{input_endpoint_id}-{attribute_name}"
                    )
                    == relay
                )

        # Device-level entities stay on the main device
        assert child_device_id(Platform.SENSOR, "1-2") is None
        assert child_device_id(Platform.BUTTON, "1-3") is None
        assert child_device_id(Platform.UPDATE, "1-25-firmware_update") is None
