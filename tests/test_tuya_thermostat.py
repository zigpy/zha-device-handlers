"""Tests for Tuya Thermostat."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr,value",
    [
        (
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            b"\t\x16\x02\x00\t\x18\x02\x00\x04\x00\x00\x00\x18",
            Thermostat.AttributeDefs.local_temperature,
            2400,
        ),  # Current temp 24, dp 24
        (
            b"\t\x15\x02\x00\x08\x10\x02\x00\x04\x00\x00\x00\x19",
            Thermostat.AttributeDefs.occupied_heating_setpoint,
            2500,
        ),  # Setpoint to 25, dp 16
        (
            b"\t\x17\x02\x00\n\x1c\x02\x00\x04\x00\x00\x00\x00",
            Thermostat.AttributeDefs.local_temperature_calibration,
            0,
        ),  # Local calibration to 0, dp 28
        (
            b"\t\x1c\x02\x00\x0fh\x01\x00\x01\x01",
            Thermostat.AttributeDefs.running_state,
            Thermostat.RunningState.Heat_State_On,
        ),  # Running state, dp 104
        (
            b"\t\x1d\x02\x00\x10k\x02\x00\x04\x00\x00\x00\x1b",
            Thermostat.AttributeDefs.max_heat_setpoint_limit,
            2700,
        ),  # Max heat set point, dp 107
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, msg, attr, value):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk("_TZE204_p3lqqy2r", "TS0601")
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
