from unittest import mock

import pytest
from zigpy.zcl import foundation

from zhaquirks.xiaomi.aqara.thermostat_agl001 import (
    AGL001,
    SENSOR,
    SENSOR_ATTR_NAME,
    SENSOR_TEMP,
)


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_external_sensor_mode(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 thermostat external sensor mode setting."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)

    # Access the Aqara specific cluster
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    # Simulate a successful response
    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    # Test changing to external sensor mode (1)
    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        await aqara_cluster.write_attributes({SENSOR: 1})

        # Verify that the request was called
        assert m1.call_count == 1

        # Verify that the SENSOR_ATTR_NAME attribute was used
        args = m1.call_args[0]
        assert args[0] == foundation.Command.Write_Attributes
        assert SENSOR_ATTR_NAME in args[1]

        # Verify that the Aqara header is present
        attr_value = args[1][SENSOR_ATTR_NAME]
        assert attr_value.startswith(b"\xaa\x71")
        assert b"\x02" in attr_value  # Action code for external sensor


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_internal_sensor_mode(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 thermostat internal sensor mode setting."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)

    # Access the Aqara specific cluster
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    # Simulate a successful response
    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    # Test changing to internal sensor mode (0)
    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        await aqara_cluster.write_attributes({SENSOR: 0})

        # Verify that the request was called
        assert m1.call_count == 1

        # Verify that the SENSOR_ATTR_NAME attribute was used
        args = m1.call_args[0]
        assert args[0] == foundation.Command.Write_Attributes
        assert SENSOR_ATTR_NAME in args[1]

        # Verify that the Aqara header is present
        attr_value = args[1][SENSOR_ATTR_NAME]
        assert attr_value.startswith(b"\xaa\x71")
        assert b"\x04" in attr_value  # Action code for internal sensor


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_external_sensor_temperature(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 thermostat external temperature setting."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)

    # Access the Aqara specific cluster
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    # Simulate a successful response
    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    # Test sending an external temperature (2500 = 25.00°C)
    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        await aqara_cluster.write_attributes({SENSOR_TEMP: 2500})

        # Verify that the request was called
        assert m1.call_count == 1

        # Verify that the SENSOR_ATTR_NAME attribute was used
        args = m1.call_args[0]
        assert args[0] == foundation.Command.Write_Attributes
        assert SENSOR_ATTR_NAME in args[1]

        # Verify that the Aqara header is present
        attr_value = args[1][SENSOR_ATTR_NAME]
        assert attr_value.startswith(b"\xaa\x71")
        assert b"\x05" in attr_value  # Action code for setting temperature

        # Verify that the temperature value is present
        sensor_id = b"\x00\x15\x8d\x00\x01\x9d\x1b\x98"
        assert sensor_id in attr_value
