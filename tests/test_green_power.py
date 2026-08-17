"""Tests for the Green Power quirk builder."""

from unittest.mock import MagicMock

import pytest
from zha.quirks import DEVICE_REGISTRY, QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.device import GreenPowerDevice as ZigpyGreenPowerDevice
from zigpy.types import EUI64
from zigpy.zgp.types import ApplicationID, DeviceID, GPDCommandID, SrcID

from zhaquirks.builder import GreenPowerQuirkBuilder
from zhaquirks.builder.green_power import QuirkGreenPowerDevice


@pytest.fixture
def zigpy_gpd(MockAppController):
    """Create a commissioned SrcID-addressed zigpy GPD."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x01700001),
    )
    gpd.device_id = DeviceID.OnOffSwitch
    gpd.commands = [
        GPDCommandID.Toggle,
        GPDCommandID.Press1of1,
        GPDCommandID.Release1of1,
    ]
    return gpd


def test_green_power_quirk_builder(zigpy_gpd):
    """Test matching and resolving a Green Power quirk."""
    with DEVICE_REGISTRY.preserve_state():
        entry = (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .src_id_range(0x01700000, 0x0170FFFF)
            .filter(lambda device: GPDCommandID.Toggle in device.commands)
            .friendly_name(manufacturer="EnOcean", model="PTM 215Z")
            .add_to_registry()
        )

        assert DEVICE_REGISTRY.match_green_power_entry(zigpy_gpd) is entry

        resolved = DEVICE_REGISTRY.resolve(zigpy_gpd)
        assert resolved is zigpy_gpd
        assert getattr(resolved, QUIRK_REGISTRY_ENTRY_ATTR) is entry

        zha_device = entry.zha_device_factory(resolved, MagicMock())
        assert isinstance(zha_device, QuirkGreenPowerDevice)
        assert zha_device.manufacturer == "EnOcean"
        assert zha_device.model == "PTM 215Z"
        assert zha_device.name == "EnOcean PTM 215Z"


def test_green_power_quirk_builder_no_match(zigpy_gpd):
    """Test that a non-matching quirk leaves the device unquirked."""
    with DEVICE_REGISTRY.preserve_state():
        (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.GenericSwitch)
            .add_to_registry()
        )
        (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .src_id_range(0x00400000, 0x0040FFFF)
            .add_to_registry()
        )

        assert DEVICE_REGISTRY.match_green_power_entry(zigpy_gpd) is None
        assert DEVICE_REGISTRY.resolve(zigpy_gpd) is zigpy_gpd
        assert not hasattr(zigpy_gpd, QUIRK_REGISTRY_ENTRY_ATTR)


def test_green_power_quirk_builder_ieee_prefix(MockAppController):
    """Test matching an IEEE-addressed GPD by address prefix."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.IEEE,
        ieee=EUI64.convert("04:cd:15:00:11:22:33:44"),
        endpoint=1,
    )

    with DEVICE_REGISTRY.preserve_state():
        entry = GreenPowerQuirkBuilder().ieee_prefix("04:cd:15").add_to_registry()

        assert DEVICE_REGISTRY.match_green_power_entry(gpd) is entry


def test_green_power_quirk_builder_requires_criteria():
    """Test that a quirk without matching criteria is rejected."""
    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().friendly_name(
            manufacturer="Acme", model="Switch"
        ).add_to_registry()

    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().applies_to()


def test_green_power_quirk_custom_device_class(zigpy_gpd):
    """Test that a custom ZHA device class is used by the factory."""

    class CustomGreenPowerDevice(QuirkGreenPowerDevice):
        """Custom quirk device class."""

    with DEVICE_REGISTRY.preserve_state():
        entry = (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .device_class(CustomGreenPowerDevice)
            .add_to_registry()
        )

        zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
        assert isinstance(zha_device, CustomGreenPowerDevice)
