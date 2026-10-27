"""Tests for Heiman custom quirks."""

from zigpy.zcl.clusters.general import DeviceTemperature

import zhaquirks.heiman.hs1rm_e

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
