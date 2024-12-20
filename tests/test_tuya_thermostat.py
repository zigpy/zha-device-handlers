"""Tests for Tuya Smoke Detector."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf",
    [
        ("_TZE204_p3lqqy2r", "TS0601"),
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, model, manuf):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.thermostat is not None
    assert isinstance(ep.thermostat, Thermostat)

    thermostat_listener = ClusterListener(ep.thermostat)

    message = b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01"  # Set to Heat
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(thermostat_listener.attribute_updates) == 1
    assert (
        thermostat_listener.attribute_updates[0][0]
        == Thermostat.AttributeDefs.system_mode.id
    )
    assert thermostat_listener.attribute_updates[0][1] == Thermostat.SystemMode.Heat

    assert (
        ep.thermostat.get(Thermostat.AttributeDefs.system_mode.id)
        == Thermostat.SystemMode.Heat
    )
