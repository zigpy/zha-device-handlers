"""Tests for Aqara E1 thermostat."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

from zhaquirks.xiaomi.aqara.thermostat_agl001 import (
    AGL001,
    XIAOMI_SYSTEM_MODE_MAP,
    ZCL_SYSTEM_MODE,
    AqaraThermostatSpecificCluster,
)

# Avoids writing out the AqaraThermostatSpecificCluster.AttributeDefs every time.
Defs = AqaraThermostatSpecificCluster.AttributeDefs


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_external_sensor_mode(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 thermostat external sensor mode setting."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)

    # Access the Aqara specific cluster
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    # Simulate a successful response for multiple calls
    async def async_success(*args, **kwargs):
        return [foundation.Status.SUCCESS]

    # Test changing to external sensor mode (1)
    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        await aqara_cluster.write_attributes({Defs.sensor.id: 1})

        # Verify that the request was called twice (once for each write_attributes call)
        assert m1.call_count == 2

        # Verify that the SENSOR_ATTR attribute was used in both calls
        first_call_args = m1.call_args_list[0][0]
        second_call_args = m1.call_args_list[1][0]

        assert first_call_args[1] == foundation.GeneralCommand.Write_Attributes
        assert second_call_args[1] == foundation.GeneralCommand.Write_Attributes

        # Verify that the SENSOR_ATTR is present in the attributes list
        assert any(attr.attrid == Defs.sensor_attr.id for attr in first_call_args[3])
        assert any(attr.attrid == Defs.sensor_attr.id for attr in second_call_args[3])

        # Get the attribute values
        first_attr = next(
            attr for attr in first_call_args[3] if attr.attrid == Defs.sensor_attr.id
        )
        second_attr = next(
            attr for attr in second_call_args[3] if attr.attrid == Defs.sensor_attr.id
        )

        first_attr_value = first_attr.value.value
        second_attr_value = second_attr.value.value

        assert first_attr_value.startswith(b"\xaa\x71")
        assert b"\x02" in first_attr_value  # Action code for external sensor

        assert second_attr_value.startswith(b"\xaa\x71")
        assert b"\x02" in second_attr_value  # Action code for external sensor


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_internal_sensor_mode(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 thermostat internal sensor mode setting."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)

    # Access the Aqara specific cluster
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    # Simulate a successful response for multiple calls
    async def async_success(*args, **kwargs):
        return [foundation.Status.SUCCESS]

    # Test changing to internal sensor mode (0)
    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        await aqara_cluster.write_attributes({Defs.sensor.id: 0})

        # Verify that the request was called twice (once for each write_attributes call)
        assert m1.call_count == 2

        # Verify that the SENSOR_ATTR attribute was used in both calls
        first_call_args = m1.call_args_list[0][0]
        second_call_args = m1.call_args_list[1][0]

        assert first_call_args[1] == foundation.GeneralCommand.Write_Attributes
        assert second_call_args[1] == foundation.GeneralCommand.Write_Attributes

        # Verify that the SENSOR_ATTR is present in the attributes list
        assert any(attr.attrid == Defs.sensor_attr.id for attr in first_call_args[3])
        assert any(attr.attrid == Defs.sensor_attr.id for attr in second_call_args[3])

        # Get the attribute values
        first_attr = next(
            attr for attr in first_call_args[3] if attr.attrid == Defs.sensor_attr.id
        )
        second_attr = next(
            attr for attr in second_call_args[3] if attr.attrid == Defs.sensor_attr.id
        )

        first_attr_value = first_attr.value.value
        second_attr_value = second_attr.value.value

        assert first_attr_value.startswith(b"\xaa\x71")
        assert b"\x04" in first_attr_value  # Action code for internal sensor

        assert second_attr_value.startswith(b"\xaa\x71")
        assert b"\x04" in second_attr_value  # Action code for internal sensor


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_external_sensor_temperature(zigpy_device_from_quirk, quirk):
    """Test Aqara E1 thermostat external temperature setting."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)

    # Access the Aqara specific cluster
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    # Simulate a successful response
    async def async_success(*args, **kwargs):
        return [foundation.Status.SUCCESS]

    # Test sending an external temperature (2500 = 25.00°C)
    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        await aqara_cluster.write_attributes({Defs.sensor_temp.id: 2500})

        # Verify that the request was called
        assert m1.call_count == 1

        # Verify that the SENSOR_ATTR attribute was used
        args = m1.call_args[0]
        assert args[1] == foundation.GeneralCommand.Write_Attributes
        attr = next(attr for attr in args[3] if attr.attrid == Defs.sensor_attr.id)

        # Verify that the Aqara header is present
        attr_value = attr.value.value
        assert attr_value.startswith(b"\xaa\x71")
        assert b"\x05" in attr_value  # Action code for setting temperature

        # Verify that the temperature value is present
        sensor_id = b"\x00\x15\x8d\x00\x01\x9d\x1b\x98"
        assert sensor_id in attr_value


@pytest.mark.parametrize("quirk", (AGL001,))
async def test_external_sensor_temp_message_length_regression(
    zigpy_device_from_quirk, quirk
):
    """Test that repeated external sensor temperature writes do not mutate SENSOR_ID."""

    thermostat_dev = zigpy_device_from_quirk(quirk)
    aqara_cluster = thermostat_dev.endpoints[1].opple_cluster

    async def async_success(*args, **kwargs):
        return [foundation.Status.SUCCESS]

    with mock.patch.object(aqara_cluster, "request", side_effect=async_success) as m1:
        # First call
        await aqara_cluster.write_attributes({Defs.sensor_temp.id: 2500})
        first_args = m1.call_args[0]
        first_attr = next(
            attr for attr in first_args[3] if attr.attrid == Defs.sensor_attr.id
        )
        first_value = first_attr.value.value

        # Second call
        await aqara_cluster.write_attributes({Defs.sensor_temp.id: 2500})
        second_args = m1.call_args[0]
        second_attr = next(
            attr for attr in second_args[3] if attr.attrid == Defs.sensor_attr.id
        )
        second_value = second_attr.value.value

        # Assert that the message length is the same and content is identical
        assert len(first_value) == len(second_value), (
            f"Message length changed: {len(first_value)} vs {len(second_value)}"
        )
        assert first_value == second_value, "Message content changed between calls"


@pytest.mark.parametrize("quirk", (AGL001,))
@pytest.mark.asyncio
async def test_system_mode_read_forwarding(zigpy_device_from_quirk, quirk):
    """Test that system_mode read is forwarded to the Xiaomi cluster and mapped."""

    # Create virtual device from the quirk
    thermostat_dev = zigpy_device_from_quirk(quirk)
    thermostat_cluster = thermostat_dev.endpoints[1].thermostat

    # Patch the Xiaomi cluster's read_attributes method
    opple_cluster = thermostat_dev.endpoints[1].opple_cluster
    # Simulate Xiaomi cluster returning system_mode = 1 (heat)
    xiaomi_system_mode_value = 1
    xiaomi_attr_id = Defs.system_mode.id
    xiaomi_result = ({xiaomi_attr_id: xiaomi_system_mode_value}, {})

    with mock.patch.object(
        opple_cluster, "read_attributes", new=mock.AsyncMock(return_value=xiaomi_result)
    ) as mock_read:
        # Test reading by attribute ID
        successful_r, failed_r = await thermostat_cluster.read_attributes(
            [ZCL_SYSTEM_MODE]
        )
        assert mock_read.called
        # Should be mapped to standard ZCL value
        assert ZCL_SYSTEM_MODE in successful_r
        assert (
            successful_r[ZCL_SYSTEM_MODE]
            == XIAOMI_SYSTEM_MODE_MAP[xiaomi_system_mode_value]
        )

        # Test reading by attribute name
        mock_read.reset_mock()
        successful_r, failed_r = await thermostat_cluster.read_attributes(
            [Defs.system_mode.name]
        )
        assert mock_read.called
        assert ZCL_SYSTEM_MODE in successful_r
        assert (
            successful_r[ZCL_SYSTEM_MODE]
            == XIAOMI_SYSTEM_MODE_MAP[xiaomi_system_mode_value]
        )
