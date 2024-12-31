"""Test for Tuya TRV."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya import TUYA_QUERY_DATA
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_trv_v2 import EnchantedDeviceV2

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr,value",
    [
        (
            b"\t\xc2\x02\x00q\x02\x04\x00\x01\x00",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Auto,
        ),  # Set to Auto (0x00), dp 2
        (
            b"\t\xc3\x02\x00r\x02\x04\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to Heat (0x01), dp 2
        (
            b"\t\xc2\x02\x00q\x02\x04\x00\x01\x02",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Off,
        ),  # Set to Off (0x02), dp 2
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, msg, attr, value):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk("_TZE204_ogx8u5z6", "TS0601")
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


async def test_tuya_spell(zigpy_device_from_v2_quirk):
    """Test that enchanted Tuya devices have their spells applied during configuration."""
    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        device = zigpy_device_from_v2_quirk("_TZE204_ogx8u5z6", "TS0601")
        assert isinstance(device, EnchantedDeviceV2)

        # call apply_custom_configuration() on each EnchantedDevice
        # ZHA does this during device configuration normally
        await device.apply_custom_configuration()

        # the number of Tuya spells that are allowed to be cast, so the sum of enabled Tuya spells
        enabled_tuya_spells_num = (
            device.tuya_spell_read_attributes + device.tuya_spell_data_query
        )

        # verify request was called the correct number of times
        assert request_mock.call_count == enabled_tuya_spells_num

        # used to check list of mock calls below
        messages = 0

        # check 'attribute read spell' was cast correctly (if enabled)
        if device.tuya_spell_read_attributes:
            assert (
                request_mock.mock_calls[messages][1][1]
                == foundation.GeneralCommand.Read_Attributes
            )
            assert request_mock.mock_calls[messages][1][3] == [4, 0, 1, 5, 7, 65534]
            messages += 1

        # check 'query data spell' was cast correctly (if enabled)
        if device.tuya_spell_data_query:
            assert not request_mock.mock_calls[messages][1][0]
            assert request_mock.mock_calls[messages][1][1] == TUYA_QUERY_DATA
            messages += 1

        request_mock.reset_mock()
