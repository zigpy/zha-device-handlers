"""Tests for Tuya quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks

zhaquirks.setup()


async def test_command_rcbo(zigpy_device_from_quirk):
    """Test executing cluster commands for RCBO."""

    rcbo_dev = zigpy_device_from_quirk(zhaquirks.tuya.ts0601_rcbo.TuyaCircuitBreaker)
    tuya_cluster = rcbo_dev.endpoints[1].tuya_manufacturer
    switch_cluster = rcbo_dev.endpoints[1].on_off
    metering_cluster = rcbo_dev.endpoints[1].smartenergy_metering
    tuya_listener = ClusterListener(tuya_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await switch_cluster.command(0x01)  # turn_on

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x01\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp.status == foundation.Status.SUCCESS

        m1.reset_mock()
        rsp = await switch_cluster.command(0x74)  # clear_locking

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02t\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp.status == foundation.Status.SUCCESS

        m1.reset_mock()
        rsp = await metering_cluster.command(0x73)  # clear_device_data

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=3,
            data=b"\x01\x03\x00\x00\x03s\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp.status == foundation.Status.SUCCESS


@pytest.mark.parametrize(
    "frame, cluster, attributes",
    (
        (  # TuyaDatapointData(dp=1, data=TuyaData(dp_type=<TuyaDPType.BOOL: 1>, function=0, raw=b'\x01', *payload=<Bool.true: 1>))
            b"\x09\x00\x01\x02\x03\x01\x01\x00\x01\x01",
            "on_off",
            {0x0000: 1},
        ),
        (  # TuyaDatapointData(dp=9, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x2c\x01\x00\x00', *payload=300))
            b"\x09\x01\x01\x02\x03\x09\x02\x00\x04\x00\x00\x01\x2c",
            "on_off",
            {0xF090: 300},
        ),
        (  # TuyaDatapointData(dp=26, data=TuyaData(dp_type=<TuyaDPType.ENUM: 4>, function=0, raw=b'\x00', *payload=<enum8.undefined_0x00: 0>))
            b"\x09\x02\x01\x02\x03\x1a\x04\x00\x01\x00",
            "electrical_measurement",
            {0xF1A0: 0},
        ),
        (  # TuyaDatapointData(dp=27, data=TuyaData(dp_type=<TuyaDPType.ENUM: 4>, function=0, raw=b'\x02', *payload=<enum8.undefined_0x02: 2>))
            b"\x09\x03\x01\x02\x03\x1b\x04\x00\x01\x02",
            "on_off",
            {0x8002: 2},
        ),
        (  # TuyaDatapointData(dp=29, data=TuyaData(dp_type=<TuyaDPType.BOOL: 1>, function=0, raw=b'\x00', *payload=<Bool.false: 0>))
            b"\x09\x04\x01\x02\x03\x1d\x01\x00\x01\x00",
            "on_off",
            {0x8000: 0},
        ),
        (  # TuyaDatapointData(dp=101, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\x00\x00\xad\x08', *payload=b'\x08\xad\x00\x00\x00\x00'))
            b"\x09\x05\x01\x02\x03e\x00\x00\x06\x08\xad\x00\x00\x00\x00",
            "electrical_measurement",
            {0x0505: 2221},
        ),
        (  # TuyaDatapointData(dp=102, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\x00\x00\x00\x00\xdf\x02\x00', *payload=b'\x00\x02\xdf\x00\x00\x00\x00\x00\x00'))
            b"\x09\x06\x01\x02\x03f\x00\x00\x09\x00\x02\xdf\x00\x00\x00\x00\x00\x00",
            "electrical_measurement",
            {0x0508: 735},
        ),
        (  # TuyaDatapointData(dp=103, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\x00\x00\x00\x00\xbf\x09\x00\xbf\x09\x00', *payload=b'\x00\x09\xbf\x00\x09\xbf\x00\x00\x00\x00\x00\x00'))
            b"\x09\x07\x01\x02\x03g\x00\x00\x0c\x00\x09\xbf\x00\x09\xbf\x00\x00\x00\x00\x00\x00",
            "electrical_measurement",
            {0x050B: 2495},
        ),
        (  # TuyaDatapointData(dp=104, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x05\x00\x00\x00', *payload=5))
            b"\x09\x08\x01\x02\x03h\x02\x00\x04\x00\x00\x00\x05",
            "electrical_measurement",
            {0xF680: 5},
        ),
        (  # TuyaDatapointData(dp=105, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x1d\x00\x00\x00', *payload=29))
            b"\x09\x09\x01\x02\x03i\x02\x00\x04\x00\x00\x00\x1d",
            "device_temperature",
            {0x0000: 2900},
        ),
        (  # TuyaDatapointData(dp=106, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x00\x00\x00\x00', *payload=0))
            b"\x09\x0a\x01\x02\x03j\x02\x00\x04\x00\x00\x00\x00",
            "smartenergy_metering",
            {0xF6A0: 0},
        ),
        (  # TuyaDatapointData(dp=108, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\xb4\x14', *payload=b'\x14\xb4\x00'))
            b"\x09\x0c\x01\x02\x03l\x00\x00\x03\x14\xb4\x00",
            "smartenergy_metering",
            {0xF6C0: 5300, 0xF6C1: 0},
        ),
        (  # TuyaDatapointData(dp=109, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\x00\x19\x00\x00\x00\x01', *payload=b'\x01\x00\x00\x00\x19\x00\x00\x00'))
            b"\x09\x0d\x01\x02\x03m\x00\x00\x08\x01\x00\x00\x00\x19\x00\x00\x00",
            "electrical_measurement",
            {
                0xF6D0: 1,
                0xF6D1: 0,
                0xF6D2: 0,
                0xF6D3: 25,
                0xF6D5: 0,
                0xF6D6: 0,
                0xF6D7: 0,
            },
        ),
        (  # TuyaDatapointData(dp=110, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\xf4\x01\x00\x00"\x0b', *payload=b'\x0b"\x00\x00\x01\xf4\x00\x00'))
            b'\x09\x0e\x01\x02\x03n\x00\x00\x08\x0b"\x00\x00\x01\xf4\x00\x00',
            "electrical_measurement",
            {0x0807: 2850, 0xF6E3: 0, 0x0800: 0, 0x0808: 500, 0xF6E7: 0},
        ),
        (  # TuyaDatapointData(dp=111, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\xa0\x86\x01', *payload=b'\x01\x86\xa0\x00\x00'))
            b"\x09\x0f\x01\x02\x03o\x00\x00\x05\x01\x86\xa0\x00\x00",
            "electrical_measurement",
            {0x0802: 100000, 0xF6F3: 0, 0x0800: 0},
        ),
        (  # TuyaDatapointData(dp=112, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00d', *payload=b'd\x00\x00'))
            b"\x09\x10\x01\x02\x03p\x00\x00\x03d\x00\x00",
            "device_temperature",
            {0x0012: 100, 0xFF10: 0, 0x0010: 0},
        ),
        (  # TuyaDatapointData(dp=113, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'Cr\x00\x00', *payload=29251))
            b"\x09\x11\x01\x02\x04q\x02\x00\x04\x00\x00rC",
            "smartenergy_metering",
            {0x0000: 29251},
        ),
        (  # TuyaDatapointData(dp=114, data=TuyaData(dp_type=<TuyaDPType.STRING: 3>, function=0, raw=b'220100000082        ', *payload='220100000082        '))
            b"\x09\x12\x01\x02\x03r\x03\x00\x14220100000082        ",
            "smartenergy_metering",
            {0xF720: "220100000082"},
        ),
        (  # TuyaDatapointData(dp=116, data=TuyaData(dp_type=<TuyaDPType.BOOL: 1>, function=0, raw=b'\x00', *payload=<Bool.false: 0>))
            b"\x09\x14\x01\x02\x03t\x01\x00\x01\x00",
            "on_off",
            {0xF740: 0},
        ),
        (  # TuyaDatapointData(dp=117, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x00\x00\x00\x00', *payload=0))
            b"\x09\x15\x01\x02\x03u\x02\x00\x04\x00\x00\x00\x00",
            "smartenergy_metering",
            {0x0001: 0},
        ),
        (  # TuyaDatapointData(dp=118, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\x00\x00\xa9\x08', *payload=b'\x08\xa9\x00\x00\x00\x00'))
            b"\x09\x16\x01\x02\x03v\x00\x00\x06\x08\xa9\x00\x00\x00\x00",
            "electrical_measurement",
            {0xF760: 2217},
        ),
        (  # TuyaDatapointData(dp=119, data=TuyaData(dp_type=<TuyaDPType.RAW: 0>, function=0, raw=b'\x00\x00\x00\x00\x00\x00\x92\x03\x00', *payload=b'\x00\x03\x92\x00\x00\x00\x00\x00\x00'))
            b"\x09\x17\x01\x02\x03w\x00\x00\x09\x00\x03\x92\x00\x00\x00\x00\x00\x00",
            "electrical_measurement",
            {0xF770: 914},
        ),
    ),
)
async def test_report_values_rcbo(zigpy_device_from_quirk, frame, cluster, attributes):
    """Test receiving attributes from RCBO."""

    rcbo_dev = zigpy_device_from_quirk(zhaquirks.tuya.ts0601_rcbo.TuyaCircuitBreaker)
    tuya_cluster = rcbo_dev.endpoints[1].tuya_manufacturer
    target_cluster = rcbo_dev.endpoints[1].__getattr__(cluster)
    tuya_listener = ClusterListener(target_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert tuya_listener.attribute_updates == list(attributes.items())


@pytest.mark.parametrize(
    "frames_pre, frame, cluster, attributes",
    (
        (
            [],
            b"\x01\x01\x00\x00\x01\t\x02\x00\x04\x00\x00\x02X",
            "on_off",
            {"countdown_timer": 600},
        ),
        ([], b"\x01\x01\x00\x00\x01\x1d\x01\x00\x01\x01", "on_off", {"child_lock": 1}),
        (
            [],
            b"\x01\x01\x00\x00\x01\x1b\x04\x00\x01\x01",
            "on_off",
            {"power_on_state": 1},
        ),
        ([], b"\x01\x01\x00\x00\x01t\x01\x00\x01\x00", "on_off", {"trip": 0}),
        (
            [],
            b"\x01\x03\x00\x00\x03p\x00\x00\x03Z\x00\x00",
            "device_temperature",
            {"high_temp_thres": 90, "over_temp_trip": 0, "dev_temp_alarm_mask": 0},
        ),
        (
            [],
            b"\x01\x07\x00\x00\x07m\x00\x00\x08\x01\x00\x00\x01,\x00\x00\x00",
            "electrical_measurement",
            {
                "self_test_auto_days": 1,
                "self_test_auto_hours": 0,
                "self_test_auto": False,
                "over_leakage_current_threshold": 300,
                "over_leakage_current_trip": False,
                "over_leakage_current_alarm": False,
                "self_test": 0,
            },
        ),
        (
            [],
            b'\x01\x04\x00\x00\x06n\x00\x00\x08\x0b"\x00\x00\x01\xf4\x00\x00',
            "electrical_measurement",
            {
                "rms_extreme_over_voltage": 2850,
                "over_voltage_trip": 0,
                "ac_alarms_mask": 0,
                "rms_extreme_under_voltage": 500,
                "under_voltage_trip": 0,
            },
        ),
        (
            [
                b'\x09\x0e\x01\x02\x03n\x00\x00\x08\x0b"\x00\x00\x01\xf4\x00\x00',
                b"\x09\x0f\x01\x02\x03o\x00\x00\x05\x01\x86\xa0\x00\x00",
            ],
            b"\x01\x04\x00\x00\x04o\x00\x00\x05\x01_\x90\x01\x01",
            "electrical_measurement",
            {
                "ac_current_overload": 90000,
                "over_current_trip": 1,
                "ac_alarms_mask": 0x02,
            },
        ),
        (
            [
                b'\x09\x0e\x01\x02\x03n\x00\x00\x08\x0b"\x00\x00\x01\xf4\x00\x00',
                b"\x09\x0f\x01\x02\x03o\x00\x00\x05\x01\x86\xa0\x00\x01",
            ],
            b"\x01\x01\x00\x00\x01o\x00\x00\x05\x01\x86\xa0\x00\x01",
            "electrical_measurement",
            {
                "ac_current_overload": 100000,
            },
        ),
        (
            [],
            b"\x01\x02\x00\x00\x02l\x00\x00\x03\x14\xb4\x01",
            "smartenergy_metering",
            {"cost_parameters": 5300, "cost_parameters_enabled": 1},
        ),
    ),
)
async def test_write_attr_rcbo(
    zigpy_device_from_quirk, frames_pre, frame, cluster, attributes
):
    """Test write cluster attributes for RCBO."""

    rcbo_dev = zigpy_device_from_quirk(zhaquirks.tuya.ts0601_rcbo.TuyaCircuitBreaker)
    tuya_cluster = rcbo_dev.endpoints[1].tuya_manufacturer
    target_cluster = rcbo_dev.endpoints[1].__getattr__(cluster)

    # preset some attributes in cache:
    for frame_pre in frames_pre:
        tuya_cluster.handle_message(*tuya_cluster.deserialize(frame_pre))

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await target_cluster.write_attributes(attributes)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=frame[1],
            data=frame,
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


async def test_power_factor(zigpy_device_from_quirk):
    """Test calculating apparent_power and power_factor attributes."""

    rcbo_dev = zigpy_device_from_quirk(zhaquirks.tuya.ts0601_rcbo.TuyaCircuitBreaker)
    tuya_cluster = rcbo_dev.endpoints[1].tuya_manufacturer
    electrical_measurement_cluster = rcbo_dev.endpoints[1].electrical_measurement
    tuya_listener = ClusterListener(electrical_measurement_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    hdr, args = tuya_cluster.deserialize(
        b"\x09\x05\x01\x02\x03e\x00\x00\x06\x08\xad\x00\x00\x00\x00"
    )
    tuya_cluster.handle_message(hdr, args)  # rms_voltage
    assert tuya_listener.attribute_updates == [(0x0505, 2221)]

    tuya_listener.attribute_updates = []
    hdr, args = tuya_cluster.deserialize(
        b"\x09\x06\x01\x02\x03f\x00\x00\x09\x00\x02\xdf\x00\x00\x00\x00\x00\x00"
    )
    tuya_cluster.handle_message(hdr, args)  # rms_current
    assert tuya_listener.attribute_updates == [(0x0508, 735), (0x050F, 1632)]

    tuya_listener.attribute_updates = []
    hdr, args = tuya_cluster.deserialize(
        b"\x09\x07\x01\x02\x03g\x00\x00\x0c\x00\x09\xbf\x00\x09\xbf\x00\x00\x00\x00\x00\x00"
    )
    tuya_cluster.handle_message(hdr, args)  # active_power
    assert tuya_listener.attribute_updates == [(0x050B, 2495), (0x0510, 100)]

    tuya_listener.attribute_updates = []
    hdr, args = tuya_cluster.deserialize(
        b"\x09\x08\x01\x02\x03g\x00\x00\x0c\x00\x06\x4b\x00\x06\x4b\x00\x00\x00\x00\x00\x00"
    )
    tuya_cluster.handle_message(hdr, args)  # active_power
    assert tuya_listener.attribute_updates == [(0x050B, 1611), (0x0510, 99)]
