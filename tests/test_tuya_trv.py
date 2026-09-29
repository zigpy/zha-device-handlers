"""Test for Tuya TRV."""

from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_trv import MoesZtrvBy100PresetMode

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
            retries=None,
            retry_delay=None,
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
            retries=None,
            retry_delay=None,
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
                retries=None,
                retry_delay=None,
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
            retries=None,
            retry_delay=None,
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
                retries=None,
                retry_delay=None,
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


# Moes ZTRV-BY-100 (_TZE200_b6wax7g0). Frames captured from a real device,
# except the negative calibration, which the device has not reported.
MOES_ZTRV_BY100_REPORTS = (
    # dp 2: setpoint 21 C
    (
        "09 d9 02 00 b0 02 02 00 04 00 00 00 15",
        "thermostat",
        "occupied_heating_setpoint",
        2100,
    ),
    # dp 3: room temperature 24.0 C
    ("09 df 02 00 b5 03 02 00 04 00 00 00 f0", "thermostat", "local_temperature", 2400),
    # dp 7: valve closed -> idle, valve open -> heating
    ("09 b1 02 01 6e 07 04 00 01 01", "thermostat", "running_state", RunningState.Idle),
    (
        "09 b2 02 00 b2 07 04 00 01 00",
        "thermostat",
        "running_state",
        RunningState.Heat_State_On,
    ),
    # dp 14: battery 68 % (ZCL half-percent units)
    (
        "09 e0 02 00 b6 0e 02 00 04 00 00 00 44",
        "power",
        "battery_percentage_remaining",
        136,
    ),
    # dp 1: preset mode manual
    ("09 ac 02 01 69 01 04 00 01 01", "tuya_manufacturer", "preset_mode", 1),
    # dp 4 / 5: boost off, countdown 0 min
    ("09 dd 02 00 b4 04 01 00 01 00", "tuya_manufacturer", "boost_heating", False),
    (
        "09 da 02 00 b1 05 02 00 04 00 00 00 00",
        "tuya_manufacturer",
        "boost_heating_countdown",
        0,
    ),
    # dp 8: open window detection on
    ("09 be 02 01 78 08 01 00 01 01", "tuya_manufacturer", "window_detection", True),
    # dp 9: the device reports 1 when the window is closed
    ("09 dc 02 00 b3 09 04 00 01 01", "tuya_manufacturer", "window_open", False),
    # dp 13: child lock off
    ("09 b2 02 01 6f 0d 01 00 01 00", "tuya_manufacturer", "child_lock", False),
    # dp 103: boost time 300 s
    ("09 c9 02 00 a0 67 02 00 04 00 00 01 2c", "tuya_manufacturer", "boost_time", 300),
    # dp 104: valve position 0 %
    (
        "09 b8 02 01 75 68 02 00 04 00 00 00 00",
        "tuya_manufacturer",
        "valve_position",
        0,
    ),
    # dp 105: calibration -2 C (constructed)
    (
        "09 01 02 00 01 69 02 00 04 ff ff ff fe",
        "tuya_manufacturer",
        "local_temperature_calibration",
        -2,
    ),
    # dp 106 / 107: eco mode off, eco temperature 18 C
    ("09 c5 02 00 67 6a 01 00 01 00", "tuya_manufacturer", "eco_mode", False),
    (
        "09 bd 02 01 77 6b 02 00 04 00 00 00 12",
        "tuya_manufacturer",
        "eco_temperature",
        18,
    ),
    # dp 108 / 109: max 25 C, min 5 C
    (
        "09 c7 02 00 73 6c 02 00 04 00 00 00 19",
        "tuya_manufacturer",
        "max_temperature",
        25,
    ),
    (
        "09 c8 02 00 77 6d 02 00 04 00 00 00 05",
        "tuya_manufacturer",
        "min_temperature",
        5,
    ),
)


@pytest.mark.parametrize(
    "frame, ep_attribute, attr_name, value", MOES_ZTRV_BY100_REPORTS
)
async def test_moes_ztrv_by100_reports(
    zigpy_device_from_v2_quirk, frame, ep_attribute, attr_name, value
):
    """Test Moes ZTRV-BY-100 datapoint reports are converted."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_b6wax7g0", "TS0601")
    ep = quirked.endpoints[1]
    assert ep.device_type == zha.DeviceType.THERMOSTAT

    hdr, data = ep.tuya_manufacturer.deserialize(bytes.fromhex(frame))
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert getattr(ep, ep_attribute).get(attr_name) == value


@pytest.mark.parametrize(
    "ep_attribute, attributes, dp_payload",
    (
        # dp 2 setpoint, value type
        (
            "thermostat",
            {"occupied_heating_setpoint": 2100},
            b"\x02\x02\x00\x04\x00\x00\x00\x15",
        ),
        # dp 2 half-degree setpoints are rounded down, as the TRV does
        (
            "thermostat",
            {"occupied_heating_setpoint": 1850},
            b"\x02\x02\x00\x04\x00\x00\x00\x12",
        ),
        (
            "thermostat",
            {"occupied_heating_setpoint": 1950},
            b"\x02\x02\x00\x04\x00\x00\x00\x13",
        ),
        # dp 1 preset mode, enum type
        (
            "tuya_manufacturer",
            {"preset_mode": MoesZtrvBy100PresetMode.Holiday},
            b"\x01\x04\x00\x01\x03",
        ),
        # dp 13 child lock, bool type
        ("tuya_manufacturer", {"child_lock": True}, b"\x0d\x01\x00\x01\x01"),
        # dp 105 calibration, signed value
        (
            "tuya_manufacturer",
            {"local_temperature_calibration": -2},
            b"\x69\x02\x00\x04\xff\xff\xff\xfe",
        ),
        # dp 103 boost time in seconds
        ("tuya_manufacturer", {"boost_time": 300}, b"\x67\x02\x00\x04\x00\x00\x01\x2c"),
    ),
)
async def test_moes_ztrv_by100_writes(
    zigpy_device_from_v2_quirk, ep_attribute, attributes, dp_payload
):
    """Test Moes ZTRV-BY-100 attribute writes are sent as the right datapoints."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_b6wax7g0", "TS0601")
    ep = quirked.endpoints[1]

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await getattr(ep, ep_attribute).write_attributes(attributes)
        await wait_for_zigpy_tasks()

        # Tuya set_data: status, sequence, then the datapoint
        assert m1.call_count == 1
        assert m1.call_args.kwargs["data"][5:] == dp_payload
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]


async def test_moes_ztrv_by100_system_mode(zigpy_device_from_v2_quirk):
    """Test the Moes ZTRV-BY-100 thermostat always heats and ignores mode writes."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_b6wax7g0", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.thermostat.get("system_mode") == Thermostat.SystemMode.Heat
    assert ep.thermostat.get("abs_max_heat_setpoint_limit") == 3500
    assert (
        ep.thermostat.get("ctrl_sequence_of_oper")
        == Thermostat.ControlSequenceOfOperation.Heating_Only
    )

    with mock.patch.object(ep.tuya_manufacturer.endpoint, "request") as m1:
        await ep.thermostat.write_attributes({"system_mode": Thermostat.SystemMode.Off})
        await wait_for_zigpy_tasks()
        m1.assert_not_called()
