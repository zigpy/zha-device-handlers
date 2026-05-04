"""Tests for Engo Tuya thermostat quirks."""

from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


def test_engo_thermostat_entities(zigpy_device_from_v2_quirk):
    """Test the shared Engo thermostat entities and cluster defaults."""

    device = zigpy_device_from_v2_quirk("_TZE204_ca3i8m8p", "TS0601")
    ep = device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.thermostat is not None
    assert isinstance(ep.thermostat, Thermostat)
    assert (
        ep.thermostat.get(Thermostat.AttributeDefs.ctrl_sequence_of_oper.id)
        == Thermostat.ControlSequenceOfOperation.Heating_Only
    )

    assert ep.humidity is not None
    assert ep.humidity.device_class == SensorDeviceClass.HUMIDITY
    assert ep.humidity.state_class == SensorStateClass.MEASUREMENT


def test_engo_e40_has_no_humidity_sensor(zigpy_device_from_v2_quirk):
    """Test that the E40 variant does not expose humidity by default."""

    device = zigpy_device_from_v2_quirk("_TZE204_glk6viwg", "TS0601")
    ep = device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.thermostat is not None
    assert isinstance(ep.thermostat, Thermostat)
    assert not hasattr(ep, "humidity")
