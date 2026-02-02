"""Test for Tuya TRV."""

from unittest import mock

import pytest
from zigpy.profiles import zha
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
        b"\t\xc3\x02\x00r\x65\x01\x00\x01\x01",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Heat,
    ),  # Set to Heat (0x01), dp 3
    (
        b"\t\xc2\x02\x00q\x65\x01\x00\x01\x00",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Off,
    ),  # Set to Off (0x02), dp 3
)


TUYA_TEST_PLAN_V03 = (
    (
        b"\t\xc2\x02\x00q\x02\x04\x00\x01\x00",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Auto,
    ),  # Set to Auto (0x00), dp 2
    (
        b"\t\xc2\x02\x00q\x02\x04\x00\x01\x01",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Auto,
    ),  # Set to Auto (0x01), dp 2
    (
        b"\t\xc3\x02\x00r\x02\x04\x00\x01\x03",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Heat,
    ),  # Set to Heat (0x03), dp 2
    (
        b"\t\xc2\x02\x00q\x02\x04\x00\x01\x02",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Off,
    ),  # Set to Off (0x02), dp 2
)

TUYA_SYS_MODE_V01 = {
    Thermostat.SystemMode.Heat: [b"\x01\x02\x00\x00\x02\x02\x04\x00\x01\x01"],
    Thermostat.SystemMode.Off: [b"\x01\x03\x00\x00\x03\x02\x04\x00\x01\x02"],
}

TUYA_SYS_MODE_V02 = {
    Thermostat.SystemMode.Heat: [
        b"\x01\x02\x00\x00\x02\x65\x01\x00\x01\x01",
        b"\x01\x03\x00\x00\x03\x6c\x01\x00\x01\x00",
    ],
    Thermostat.SystemMode.Off: [
        b"\x01\x04\x00\x00\x04\x65\x01\x00\x01\x00",
        b"\x01\x05\x00\x00\x05\x6c\x01\x00\x01\x00",
    ],
}

TUYA_SYS_MODE_V03 = {
    Thermostat.SystemMode.Heat: [
        b"\x01\x02\x00\x00\x02\x65\x01\x00\x01\x01",
    ],
    Thermostat.SystemMode.Off: [
        b"\x01\x03\x00\x00\x03\x65\x01\x00\x01\x00",
    ],
}

TUYA_SYS_MODE_V04 = {
    Thermostat.SystemMode.Heat: [b"\x01\x02\x00\x00\x02\x02\x04\x00\x01\x03"],
    Thermostat.SystemMode.Off: [b"\x01\x03\x00\x00\x03\x02\x04\x00\x01\x02"],
    Thermostat.SystemMode.Auto: [b"\x01\x03\x00\x00\x03\x02\x04\x00\x01\x01"],
}


@pytest.mark.parametrize(
    "model, manuf, test_plan, set_pnt_msg, sys_mode_msg, ep_type, set_schedule_off",
    (
        (
            "_TZE204_ogx8u5z6",
            "TS0601",
            TUYA_TEST_PLAN_V01,
            TUYA_SP_V01,
            TUYA_SYS_MODE_V01,
            None,  # test device has specific device type, real one has SMART_PLUG
            False,
        ),
        (
            "_TZE200_3yp57tby",
            "TS0601",
            TUYA_TEST_PLAN_V02,
            TUYA_SP_V02,
            TUYA_SYS_MODE_V02,
            zha.DeviceType.THERMOSTAT,  # quirk replaces device type with THERMOSTAT
            True,  # Enusure schedule is turned off
        ),
        (
            "_TZE200_ne4pikwm",
            "TS0601",
            TUYA_TEST_PLAN_V02,
            TUYA_SP_V02,
            TUYA_SYS_MODE_V03,
            None,  # test device has specific device type, real one has SMART_PLUG
            False,
        ),
        (
            "_TZE204_qyr2m29i",
            "TS0601",
            TUYA_TEST_PLAN_V03,
            TUYA_SP_V01,
            TUYA_SYS_MODE_V04,
            None,  # test device has specific device type, real one has SMART_PLUG
            False,
        ),
    ),
)
async def test_handle_get_data(
    zigpy_device_from_v2_quirk,
    model,
    manuf,
    test_plan,
    set_pnt_msg,
    sys_mode_msg,
    ep_type,
    set_schedule_off,
):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.device_type == ep_type

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
            priority=None,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

    with mock.patch.object(
        ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await ep.thermostat.write_attributes(
            {
                "system_mode": Thermostat.SystemMode.Heat,
            }
        )
        await wait_for_zigpy_tasks()

        assert m1.call_args_list[0] == mock.call(
            cluster=0xEF00,
            sequence=2,
            data=sys_mode_msg[Thermostat.SystemMode.Heat][0],
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )
        if set_schedule_off:
            # Ensure schedule_enable set to off
            assert m1.call_args_list[1] == mock.call(
                cluster=0xEF00,
                sequence=3,
                data=sys_mode_msg[Thermostat.SystemMode.Heat][1],
                command_id=0,
                timeout=5,
                expect_reply=False,
                use_ieee=False,
                ask_for_ack=None,
                priority=None,
            )

        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        m1.reset_mock()

        (status,) = await ep.thermostat.write_attributes(
            {
                "system_mode": Thermostat.SystemMode.Off,
            }
        )
        await wait_for_zigpy_tasks()
        assert m1.call_args_list[0] == mock.call(
            cluster=0xEF00,
            sequence=2 + m1.call_count,
            data=sys_mode_msg[Thermostat.SystemMode.Off][0],
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )
        if set_schedule_off:
            # Ensure schedule_enable set to off
            assert m1.call_args_list[1] == mock.call(
                cluster=0xEF00,
                sequence=5,
                data=sys_mode_msg[Thermostat.SystemMode.Off][1],
                command_id=0,
                timeout=5,
                expect_reply=False,
                use_ieee=False,
                ask_for_ack=None,
                priority=None,
            )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]


@pytest.mark.parametrize(
    "manuf,msg,dp_id,value",
    [
        (
            "_TZE200_3yp57tby",
            b"\t\x1d\x02\x00\x10\x1b\x02\x00\x04\xff\xff\xff\xfa",
            27,
            -6,
        ),  # Local temp calibration to -6, dp 27
        (
            "_TZE204_rtrmfadk",
            b"\t\x1d\x02\x00\x10\x65\x02\x00\x04\xff\xff\xff\xfa",
            101,
            -6,
        ),  # Local temp calibration to -6, dp 101
        (
            "_TZE284_ogx8u5z6",
            b"\t\x1d\x02\x00\x10\x2f\x02\x00\x04\xff\xff\xff\xfa",
            47,
            -6,
        ),  # Local temp calibration to -6, dp 47
    ],
)
async def test_handle_get_data_tmcu(
    zigpy_device_from_v2_quirk, manuf, msg, dp_id, value
):
    """Test handle_get_data for multiple attributes."""

    attr_id = (0xEF << 8) | dp_id

    quirked = zigpy_device_from_v2_quirk(manuf, "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    tmcu_listener = ClusterListener(ep.tuya_manufacturer)

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(tmcu_listener.attribute_updates) == 1
    assert tmcu_listener.attribute_updates[0][0] == attr_id
    assert tmcu_listener.attribute_updates[0][1] == value

    assert ep.tuya_manufacturer.get(attr_id) == value
