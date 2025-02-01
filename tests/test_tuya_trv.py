"""Test for Tuya TRV."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()

TUYA_SP_V01 = b"\x01\x01\x00\x00\x01\x04\x02\x00\x04\x00\x00\x00\xfa"  # dp 2
TUYA_SP_V02 = b"\x01\x01\x00\x00\x01g\x02\x00\x04\x00\x00\x00\xfa"  # dp 103


TUYA_TEST_PLAN_V01 = (
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
)

TUYA_TEST_PLAN_V02 = (
    (
        b"\t\xc3\x02\x00r\x65\x04\x00\x01\x01",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Heat,
    ),  # Set to Heat (0x01), dp 3
    (
        b"\t\xc2\x02\x00q\x65\x04\x00\x01\x02",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Off,
    ),  # Set to Off (0x02), dp 3
)


@pytest.mark.parametrize(
    "model, manuf, test_plan, set_pnt_msg",
    (
        ("_TZE204_ogx8u5z6", "TS0601", TUYA_TEST_PLAN_V01, TUYA_SP_V01),
        ("_TZE200_3yp57tby", "TS0601", TUYA_TEST_PLAN_V02, TUYA_SP_V02),
    ),
)
async def test_handle_get_data(
    zigpy_device_from_v2_quirk, model, manuf, test_plan, set_pnt_msg
):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.thermostat is not None
    assert isinstance(ep.thermostat, Thermostat)

    for msg, attr, value in test_plan:
        thermostat_listener = ClusterListener(ep.thermostat)

        hdr, data = ep.tuya_manufacturer.deserialize(msg)
        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

        assert len(thermostat_listener.attribute_updates) == 1
        assert thermostat_listener.attribute_updates[0][0] == attr.id
        assert thermostat_listener.attribute_updates[0][1] == value

        assert ep.thermostat.get(attr.id) == value

        async def async_success(*args, **kwargs):
            return foundation.Status.SUCCESS

    with mock.patch.object(
        ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await ep.thermostat.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=set_pnt_msg,
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]
