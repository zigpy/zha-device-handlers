"""Tests for Tuya Smoke Detector."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,msg,attr,value",
    [
        (
            "_TZE204_p3lqqy2r",
            "TS0601",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE204_p3lqqy2r",
            "TS0601",
            b"\t\x16\x02\x00\t\x18\x02\x00\x04\x00\x00\x00\x18",
            Thermostat.AttributeDefs.local_temperature,
            2400,
        ),  # Current temp 24, dp 24
        (
            "_TZE204_p3lqqy2r",
            "TS0601",
            b"\t\x15\x02\x00\x08\x10\x02\x00\x04\x00\x00\x00\x19",
            Thermostat.AttributeDefs.occupied_heating_setpoint,
            2500,
        ),  # Setpoint to 25, dp 16
    ],
)
async def test_handle_get_data(
    zigpy_device_from_v2_quirk, model, manuf, msg, attr, value
):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.thermostat is not None
    assert isinstance(ep.thermostat, Thermostat)

    thermostat_listener = ClusterListener(ep.thermostat)

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(thermostat_listener.attribute_updates) == 1
    assert thermostat_listener.attribute_updates[0][0] == attr.id
    assert thermostat_listener.attribute_updates[0][1] == value

    assert ep.thermostat.get(attr.id) == value
