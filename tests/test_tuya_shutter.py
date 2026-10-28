"""Tests for Tuya Shutter quirks."""

from zigpy.zcl.clusters.general import PowerConfiguration

import zhaquirks
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


def test_valid_attributes(zigpy_device_from_v2_quirk):
    """Test that valid attributes on virtual clusters are populated by Tuya datapoints mappings."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_myikb7qz", "TS0601")
    ep = quirked.endpoints[1]

    power_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    power_config_cluster = ep.power

    assert isinstance(power_config_cluster, TuyaLocalCluster)

    # check that the virtual clusters have expected valid attributes
    assert {power_attr_id} == power_config_cluster._VALID_ATTRIBUTES


async def test_tuya(zigpy_device_from_v2_quirk):
    """Example Tuya Test."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_myikb7qz", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)
