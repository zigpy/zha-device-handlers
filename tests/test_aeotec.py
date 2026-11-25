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
