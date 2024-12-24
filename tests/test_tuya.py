"""Tests for Tuya quirks."""

import base64
import datetime
import struct
from unittest import mock

import pytest
from zigpy.device import Device
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, get_device
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone, ZoneStatus

from tests.common import ClusterListener, MockDatetime, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import Data, TuyaManufClusterAttributes, TuyaNewManufCluster
import zhaquirks.tuya.sm0202_motion
import zhaquirks.tuya.ts0021
import zhaquirks.tuya.ts0041
import zhaquirks.tuya.ts0042
import zhaquirks.tuya.ts0043
import zhaquirks.tuya.ts011f_plug
import zhaquirks.tuya.ts0501_fan_switch
import zhaquirks.tuya.ts0601_electric_heating
import zhaquirks.tuya.ts0601_motion
import zhaquirks.tuya.ts0601_siren
import zhaquirks.tuya.ts0601_trv
import zhaquirks.tuya.ts0601_valve
import zhaquirks.tuya.ts601_door
import zhaquirks.tuya.ts1201

zhaquirks.setup()

ZCL_TUYA_SET_TIME_REQUEST = b"\tp\x24\x00\00"

ZCL_TUYA_BUTTON_1_SINGLE_PRESS = b"\tT\x06\x01$\x01\x04\x00\x01\x00"
ZCL_TUYA_BUTTON_1_DOUBLE_PRESS = b"\tU\x06\x01%\x01\x04\x00\x01\x01"
ZCL_TUYA_BUTTON_1_LONG_PRESS = b"\tk\x06\x03\x11\x01\x04\x00\x01\x02"
ZCL_TUYA_BUTTON_2_SINGLE_PRESS = b"\tN\x06\x01\x1f\x02\x04\x00\x01\x00"
ZCL_TUYA_BUTTON_2_DOUBLE_PRESS = b"\tj\x06\x03\x10\x02\x04\x00\x01\x01"
ZCL_TUYA_BUTTON_2_LONG_PRESS = b"\tl\x06\x03\x12\x02\x04\x00\x01\x02"
ZCL_TUYA_SWITCH_ON = b"\tQ\x02\x006\x01\x01\x00\x01\x01"
ZCL_TUYA_SWITCH_OFF = b"\tQ\x02\x006\x01\x01\x00\x01\x00"
ZCL_TUYA_ATTRIBUTE_617_TO_179 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_SIREN_TEMPERATURE = ZCL_TUYA_ATTRIBUTE_617_TO_179
ZCL_TUYA_SIREN_HUMIDITY = b"\tp\x02\x00\x02j\x02\x00\x04\x00\x00\x00U"
ZCL_TUYA_SIREN_ON = b"\t\t\x02\x00\x04h\x01\x00\x01\x01"
ZCL_TUYA_SIREN_OFF = b"\t\t\x02\x00\x04h\x01\x00\x01\x00"
ZCL_TUYA_VALVE_TEMPERATURE = b"\tp\x02\x00\x02\x03\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_VALVE_TARGET_TEMP = b"\t3\x01\x03\x05\x02\x02\x00\x04\x00\x00\x002"
ZCL_TUYA_VALVE_OFF = b"\t2\x01\x03\x04\x04\x04\x00\x01\x00"
ZCL_TUYA_VALVE_SCHEDULE = b"\t2\x01\x03\x04\x04\x04\x00\x01\x01"
ZCL_TUYA_VALVE_MANUAL = b"\t2\x01\x03\x04\x04\x04\x00\x01\x02"
ZCL_TUYA_VALVE_COMFORT = b"\t2\x01\x03\x04\x04\x04\x00\x01\x03"
ZCL_TUYA_VALVE_ECO = b"\t2\x01\x03\x04\x04\x04\x00\x01\x04"
ZCL_TUYA_VALVE_BOOST = b"\t2\x01\x03\x04\x04\x04\x00\x01\x05"
ZCL_TUYA_VALVE_COMPLEX = b"\t2\x01\x03\x04\x04\x04\x00\x01\x06"
ZCL_TUYA_VALVE_WINDOW_DETECTION = b"\tp\x02\x00\x02\x68\x00\x00\x03\x01\x10\x05"
ZCL_TUYA_VALVE_WORKDAY_SCHEDULE = b"\tp\x02\x00\x02\x70\x00\x00\x12\x06\x00\x14\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f"
ZCL_TUYA_VALVE_WEEKEND_SCHEDULE = b"\tp\x02\x00\x02\x71\x00\x00\x12\x06\x00\x14\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f"
ZCL_TUYA_VALVE_STATE_50 = b"\t2\x01\x03\x04\x6d\x02\x00\x04\x00\x00\x00\x32"
ZCL_TUYA_VALVE_CHILD_LOCK_ON = b"\t2\x01\x03\x04\x07\x01\x00\x01\x01"
ZCL_TUYA_VALVE_AUTO_LOCK_ON = b"\t2\x01\x03\x04\x74\x01\x00\x01\x01"
ZCL_TUYA_VALVE_BATTERY_LOW = b"\t2\x01\x03\x04\x6e\x01\x00\x01\x01"


ZCL_TUYA_VALVE_ZONNSMART_TEMPERATURE = (
    b"\tp\x01\x00\x02\x18\x02\x00\x04\x00\x00\x00\xd3"
)
ZCL_TUYA_VALVE_ZONNSMART_TARGET_TEMP = (
    b"\t3\x01\x03\x05\x10\x02\x00\x04\x00\x00\x00\xcd"
)
ZCL_TUYA_VALVE_ZONNSMART_HOLIDAY_TEMP = (
    b"\t3\x01\x03\x05\x20\x02\x00\x04\x00\x00\x00\xaa"
)
ZCL_TUYA_VALVE_ZONNSMART_TEMP_OFFSET = (
    b"\t3\x01\x03\x05\x1b\x02\x00\x04\x00\x00\x00\x0b"
)
ZCL_TUYA_VALVE_ZONNSMART_MODE_MANUAL = b"\t2\x01\x03\x04\x02\x04\x00\x01\x01"
ZCL_TUYA_VALVE_ZONNSMART_MODE_SCHEDULE = b"\t2\x01\x03\x04\x02\x04\x00\x01\x00"
ZCL_TUYA_VALVE_ZONNSMART_HEAT_STOP = b"\t2\x01\x03\x04\x6b\x01\x00\x01\x00"

ZCL_TUYA_EHEAT_TEMPERATURE = b"\tp\x02\x00\x02\x18\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_EHEAT_TARGET_TEMP = b"\t3\x01\x03\x05\x10\x02\x00\x04\x00\x00\x00\x15"


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_switch.TuyaSingleSwitchTI,))
async def test_singleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya single switch."""

    switch_dev = zigpy_device_from_quirk(quirk)

    switch_cluster = switch_dev.endpoints[1].on_off
    switch_listener = ClusterListener(switch_cluster)

    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_ON)
    tuya_cluster.handle_message(hdr, args)
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_OFF)
    tuya_cluster.handle_message(hdr, args)

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == OFF


@pytest.mark.parametrize(
    "quirk,raw_event,expected_attr_name,expected_attr_value",
    (
        (
            zhaquirks.tuya.ts0021.TS0021,
            ZCL_TUYA_BUTTON_1_SINGLE_PRESS,
            "btn_1_pressed",
            0x00,
        ),
        (
            zhaquirks.tuya.ts0021.TS0021,
            ZCL_TUYA_BUTTON_1_DOUBLE_PRESS,
            "btn_1_pressed",
            0x01,
        ),
        (
            zhaquirks.tuya.ts0021.TS0021,
            ZCL_TUYA_BUTTON_1_LONG_PRESS,
            "btn_1_pressed",
            0x02,
        ),
        (
            zhaquirks.tuya.ts0021.TS0021,
            ZCL_TUYA_BUTTON_2_SINGLE_PRESS,
            "btn_2_pressed",
            0x00,
        ),
        (
            zhaquirks.tuya.ts0021.TS0021,
            ZCL_TUYA_BUTTON_2_DOUBLE_PRESS,
            "btn_2_pressed",
            0x01,
        ),
        (
            zhaquirks.tuya.ts0021.TS0021,
            ZCL_TUYA_BUTTON_2_LONG_PRESS,
            "btn_2_pressed",
            0x02,
        ),
    ),
)
async def test_ts0021_switch(
    zigpy_device_from_quirk, quirk, raw_event, expected_attr_name, expected_attr_value
):
    """Test tuya TS0021 2-gang switch."""

    device = zigpy_device_from_quirk(quirk)

    tuya_cluster = device.endpoints[1].tuya_manufacturer
    switch_listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(raw_event)
    tuya_cluster.handle_message(hdr, args)

    assert len(switch_listener.cluster_commands) == 1
    assert len(switch_listener.attribute_updates) == 1

    assert switch_listener.attribute_updates[0][0] == expected_attr_name
    assert switch_listener.attribute_updates[0][1] == expected_attr_value


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_switch.TuyaDoubleSwitchTO,))
async def test_doubleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya double switch."""

    ZCL_TUYA_SWITCH_COMMAND_03 = b"\tQ\x03\x006\x01\x01\x00\x01\x01"
    ZCL_TUYA_SWITCH_EP2_ON = b"\tQ\x02\x006\x02\x01\x00\x01\x01"
    ZCL_TUYA_SWITCH_EP2_OFF = b"\tQ\x02\x006\x02\x01\x00\x01\x00"

    switch_dev = zigpy_device_from_quirk(quirk)

    switch1_cluster = switch_dev.endpoints[1].on_off
    switch1_listener = ClusterListener(switch1_cluster)

    switch2_cluster = switch_dev.endpoints[2].on_off
    switch2_listener = ClusterListener(switch2_cluster)

    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch1_listener.attribute_updates) == 0
    assert len(switch2_listener.cluster_commands) == 0
    assert len(switch2_listener.attribute_updates) == 0

    # events from channel 1 updates only EP 1
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_ON)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 1
    assert len(switch2_listener.attribute_updates) == 0
    assert switch1_listener.attribute_updates[0][0] == 0x0000
    assert switch1_listener.attribute_updates[0][1] == ON

    # events from channel 2 updates only EP 2
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_EP2_ON)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 1
    assert len(switch2_listener.attribute_updates) == 1
    assert switch2_listener.attribute_updates[0][0] == 0x0000
    assert switch2_listener.attribute_updates[0][1] == ON

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_OFF)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 1
    assert switch1_listener.attribute_updates[1][0] == 0x0000
    assert switch1_listener.attribute_updates[1][1] == OFF

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_EP2_OFF)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 2
    assert switch2_listener.attribute_updates[1][0] == 0x0000
    assert switch2_listener.attribute_updates[1][1] == OFF

    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch2_listener.cluster_commands) == 0

    # command_id = 0x0003
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_COMMAND_03)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch2_listener.cluster_commands) == 0
    # no switch attribute updated (Unsupported command)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 2

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SET_TIME_REQUEST)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch2_listener.cluster_commands) == 0
    # no switch attribute updated (TUYA_SET_TIME command)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 2


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_switch.TuyaSingleSwitchTI,))
async def test_singleswitch_requests(zigpy_device_from_quirk, quirk):
    """Test tuya single switch."""

    switch_dev = zigpy_device_from_quirk(quirk)

    switch_cluster = switch_dev.endpoints[1].on_off
    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await switch_cluster.command(0x0000)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x01\x01\x00\x01\x00",
            command_id=0x00,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp.status == 0

        rsp = await switch_cluster.command(0x0001)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02\x01\x01\x00\x01\x01",
            command_id=0x00,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp.status == 0

    rsp = await switch_cluster.command(0x0002)
    await wait_for_zigpy_tasks()
    assert rsp.status == foundation.Status.UNSUP_CLUSTER_COMMAND


def test_ts0121_signature(assert_signature_matches_quirk):
    """Test TS0121 remote signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0051",
                "in_clusters": [
                    "0x0000",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0702",
                    "0x0b04",
                ],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZ3000_g5xawfcq",
        "model": "TS0121",
        "class": "zhaquirks.tuya.ts0121_plug.Plug",
    }
    assert_signature_matches_quirk(zhaquirks.tuya.ts0121_plug.Plug, signature)


async def test_tuya_data_conversion():
    """Test tuya conversion from Data to ztype and reverse."""
    assert t.uint32_t(Data([4, 0, 0, 1, 39])) == 295
    assert t.uint32_t(Data([4, 0, 0, 0, 220])) == 220
    assert t.int32s(Data([4, 255, 255, 255, 236])) == -20
    assert Data(t.uint32_t(295)) == [4, 0, 0, 1, 39]
    assert Data(t.uint32_t(220)) == [4, 0, 0, 0, 220]
    assert Data(t.int32s(-20)) == [4, 255, 255, 255, 236]


class TuyaTestManufCluster(TuyaManufClusterAttributes):
    """Cluster for synthetic tests."""

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes[617] = ("test_attribute", t.uint32_t, True)


class TuyaTestDevice(CustomDevice):
    """Device for synthetic tests."""

    signature = {
        MODELS_INFO: [("_test_manuf", "_test_device")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [TuyaTestManufCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [TuyaTestManufCluster],
                OUTPUT_CLUSTERS: [],
            }
        },
    }


@pytest.mark.parametrize("quirk", (TuyaTestDevice,))
async def test_tuya_receive_attribute(zigpy_device_from_quirk, quirk):
    """Test conversion of tuya commands to attributes."""

    test_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = test_dev.endpoints[1].tuya_manufacturer
    listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_ATTRIBUTE_617_TO_179)
    tuya_cluster.handle_message(hdr, args)

    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][0] == 617
    assert listener.attribute_updates[0][1] == 179


@pytest.mark.parametrize("quirk", (TuyaTestDevice,))
async def test_tuya_send_attribute(zigpy_device_from_quirk, quirk):
    """Test conversion of attributes to tuya commands."""

    test_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = test_dev.endpoints[1].tuya_manufacturer

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await tuya_cluster.write_attributes({617: 179})
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01i\x02\x00\x04\x00\x00\x00\xb3",
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


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_siren.TuyaSiren,))
async def test_siren_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya siren standard state reporting from incoming commands."""

    siren_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = siren_dev.endpoints[1].tuya_manufacturer

    temp_listener = ClusterListener(siren_dev.endpoints[1].temperature)
    humid_listener = ClusterListener(siren_dev.endpoints[1].humidity)
    switch_listener = ClusterListener(siren_dev.endpoints[1].on_off)

    frames = (
        ZCL_TUYA_SIREN_TEMPERATURE,
        ZCL_TUYA_SIREN_HUMIDITY,
        ZCL_TUYA_SIREN_ON,
        ZCL_TUYA_SIREN_OFF,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(temp_listener.cluster_commands) == 0
    assert len(temp_listener.attribute_updates) == 1
    assert temp_listener.attribute_updates[0][0] == 0x0000
    assert temp_listener.attribute_updates[0][1] == 1790

    assert len(humid_listener.cluster_commands) == 0
    assert len(humid_listener.attribute_updates) == 1
    assert humid_listener.attribute_updates[0][0] == 0x0000
    assert humid_listener.attribute_updates[0][1] == 8500

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_siren.TuyaSiren,))
async def test_siren_send_attribute(zigpy_device_from_quirk, quirk):
    """Test tuya siren outgoing commands."""

    siren_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = siren_dev.endpoints[1].tuya_manufacturer
    switch_cluster = siren_dev.endpoints[1].on_off

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:
        _, status = await switch_cluster.command(0x0000)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01h\x01\x00\x01\x00",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await switch_cluster.command(0x0001)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02h\x01\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await switch_cluster.command(0x0003)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.ZonnsmartTV01_ZG,))
async def test_zonnsmart_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)

    frames = (
        ZCL_TUYA_VALVE_ZONNSMART_TEMPERATURE,
        ZCL_TUYA_VALVE_ZONNSMART_TARGET_TEMP,
        ZCL_TUYA_VALVE_ZONNSMART_HOLIDAY_TEMP,
        ZCL_TUYA_VALVE_ZONNSMART_TEMP_OFFSET,
        ZCL_TUYA_VALVE_ZONNSMART_MODE_MANUAL,
        ZCL_TUYA_VALVE_ZONNSMART_MODE_SCHEDULE,
        ZCL_TUYA_VALVE_ZONNSMART_HEAT_STOP,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 11
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 2110
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 2050
    assert thermostat_listener.attribute_updates[4][0] == 0x0014  # HOLIDAY
    assert thermostat_listener.attribute_updates[4][1] == 1700
    assert thermostat_listener.attribute_updates[5][0] == 0x0010  # OFFSET
    assert thermostat_listener.attribute_updates[5][1] == 110
    assert thermostat_listener.attribute_updates[6][0] == 0x0025  # MANUAL
    assert thermostat_listener.attribute_updates[6][1] == 0
    assert thermostat_listener.attribute_updates[7][0] == 0x4002
    assert thermostat_listener.attribute_updates[7][1] == 1
    assert thermostat_listener.attribute_updates[8][0] == 0x0025  # SCHEDULE
    assert thermostat_listener.attribute_updates[8][1] == 1
    assert thermostat_listener.attribute_updates[9][0] == 0x4002
    assert thermostat_listener.attribute_updates[9][1] == 0
    assert thermostat_listener.attribute_updates[10][0] == 0x001C  # HEAT ON
    assert thermostat_listener.attribute_updates[10][1] == 4


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.ZonnsmartTV01_ZG,))
async def test_zonnsmart_send_attribute(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x10\x02\x00\x04\x00\x00\x00\xfa",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 1,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02\x02\x04\x00\x01\x01",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 4,  # frost protection wrapped as operation_preset
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=3,
            data=b"\x01\x03\x00\x00\x03\x0a\x01\x00\x01\x01",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0,  # SystemMode.Off
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=4,
            data=b"\x01\x04\x00\x00\x04\x6b\x01\x00\x01\x01",
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


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.SiterwellGS361_Type1,))
async def test_valve_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)

    frames = (
        ZCL_TUYA_VALVE_TEMPERATURE,
        ZCL_TUYA_VALVE_TARGET_TEMP,
        ZCL_TUYA_VALVE_OFF,
        ZCL_TUYA_VALVE_SCHEDULE,
        ZCL_TUYA_VALVE_MANUAL,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 13
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 500
    assert thermostat_listener.attribute_updates[2][0] == 0x001C  # OFF
    assert thermostat_listener.attribute_updates[2][1] == 0x00
    assert thermostat_listener.attribute_updates[3][0] == 0x001E
    assert thermostat_listener.attribute_updates[3][1] == 0x00
    assert thermostat_listener.attribute_updates[4][0] == 0x0029
    assert thermostat_listener.attribute_updates[4][1] == 0x00
    assert thermostat_listener.attribute_updates[5][0] == 0x001C  # SCHEDULE
    assert thermostat_listener.attribute_updates[5][1] == 0x04
    assert thermostat_listener.attribute_updates[6][0] == 0x0025
    assert thermostat_listener.attribute_updates[6][1] == 0x01
    assert thermostat_listener.attribute_updates[7][0] == 0x001E
    assert thermostat_listener.attribute_updates[7][1] == 0x04
    assert thermostat_listener.attribute_updates[8][0] == 0x0029
    assert thermostat_listener.attribute_updates[8][1] == 0x01
    assert thermostat_listener.attribute_updates[9][0] == 0x001C  # MANUAL
    assert thermostat_listener.attribute_updates[9][1] == 0x04
    assert thermostat_listener.attribute_updates[10][0] == 0x0025
    assert thermostat_listener.attribute_updates[10][1] == 0x00
    assert thermostat_listener.attribute_updates[11][0] == 0x001E
    assert thermostat_listener.attribute_updates[11][1] == 0x04
    assert thermostat_listener.attribute_updates[12][0] == 0x0029
    assert thermostat_listener.attribute_updates[12][1] == 0x01


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.SiterwellGS361_Type1,))
async def test_valve_send_attribute(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\xfa",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x00,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02\x04\x04\x00\x01\x00",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x04,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=3,
            data=b"\x01\x03\x00\x00\x03\x04\x04\x00\x01\x02",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x01,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=4,
            data=b"\x01\x04\x00\x00\x04\x04\x04\x00\x01\x01",
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

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VALVE_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        _, status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=5,
            data=b"\x01\x05\x00\x00\x05\x02\x02\x00\x04\x00\x00\x00F",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.MoesHY368_Type1,))
async def test_moes(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat
    onoff_cluster = valve_dev.endpoints[1].on_off
    thermostat_ui_cluster = valve_dev.endpoints[1].thermostat_ui

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)
    onoff_listener = ClusterListener(valve_dev.endpoints[1].on_off)

    frames = (
        ZCL_TUYA_VALVE_TEMPERATURE,
        ZCL_TUYA_VALVE_WINDOW_DETECTION,
        ZCL_TUYA_VALVE_WORKDAY_SCHEDULE,
        ZCL_TUYA_VALVE_WEEKEND_SCHEDULE,
        ZCL_TUYA_VALVE_OFF,
        ZCL_TUYA_VALVE_SCHEDULE,
        ZCL_TUYA_VALVE_MANUAL,
        ZCL_TUYA_VALVE_COMFORT,
        ZCL_TUYA_VALVE_ECO,
        ZCL_TUYA_VALVE_BOOST,
        ZCL_TUYA_VALVE_COMPLEX,
        ZCL_TUYA_VALVE_STATE_50,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 61
    assert thermostat_listener.attribute_updates[0][0] == 0x0000
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x4110
    assert thermostat_listener.attribute_updates[1][1] == 6
    assert thermostat_listener.attribute_updates[2][0] == 0x4111
    assert thermostat_listener.attribute_updates[2][1] == 0
    assert thermostat_listener.attribute_updates[3][0] == 0x4112
    assert thermostat_listener.attribute_updates[3][1] == 2000
    assert thermostat_listener.attribute_updates[4][0] == 0x4120
    assert thermostat_listener.attribute_updates[4][1] == 8
    assert thermostat_listener.attribute_updates[5][0] == 0x4121
    assert thermostat_listener.attribute_updates[5][1] == 0
    assert thermostat_listener.attribute_updates[6][0] == 0x4122
    assert thermostat_listener.attribute_updates[6][1] == 1500
    assert thermostat_listener.attribute_updates[7][0] == 0x4130
    assert thermostat_listener.attribute_updates[7][1] == 11
    assert thermostat_listener.attribute_updates[8][0] == 0x4131
    assert thermostat_listener.attribute_updates[8][1] == 30
    assert thermostat_listener.attribute_updates[9][0] == 0x4132
    assert thermostat_listener.attribute_updates[9][1] == 1500
    assert thermostat_listener.attribute_updates[10][0] == 0x4140
    assert thermostat_listener.attribute_updates[10][1] == 12
    assert thermostat_listener.attribute_updates[11][0] == 0x4141
    assert thermostat_listener.attribute_updates[11][1] == 30
    assert thermostat_listener.attribute_updates[12][0] == 0x4142
    assert thermostat_listener.attribute_updates[12][1] == 1500
    assert thermostat_listener.attribute_updates[13][0] == 0x4150
    assert thermostat_listener.attribute_updates[13][1] == 17
    assert thermostat_listener.attribute_updates[14][0] == 0x4151
    assert thermostat_listener.attribute_updates[14][1] == 30
    assert thermostat_listener.attribute_updates[15][0] == 0x4152
    assert thermostat_listener.attribute_updates[15][1] == 2000
    assert thermostat_listener.attribute_updates[16][0] == 0x4160
    assert thermostat_listener.attribute_updates[16][1] == 22
    assert thermostat_listener.attribute_updates[17][0] == 0x4161
    assert thermostat_listener.attribute_updates[17][1] == 0
    assert thermostat_listener.attribute_updates[18][0] == 0x4162
    assert thermostat_listener.attribute_updates[18][1] == 1500
    assert thermostat_listener.attribute_updates[19][0] == 0x4210
    assert thermostat_listener.attribute_updates[19][1] == 6
    assert thermostat_listener.attribute_updates[20][0] == 0x4211
    assert thermostat_listener.attribute_updates[20][1] == 0
    assert thermostat_listener.attribute_updates[21][0] == 0x4212
    assert thermostat_listener.attribute_updates[21][1] == 2000
    assert thermostat_listener.attribute_updates[22][0] == 0x4220
    assert thermostat_listener.attribute_updates[22][1] == 8
    assert thermostat_listener.attribute_updates[23][0] == 0x4221
    assert thermostat_listener.attribute_updates[23][1] == 0
    assert thermostat_listener.attribute_updates[24][0] == 0x4222
    assert thermostat_listener.attribute_updates[24][1] == 1500
    assert thermostat_listener.attribute_updates[25][0] == 0x4230
    assert thermostat_listener.attribute_updates[25][1] == 11
    assert thermostat_listener.attribute_updates[26][0] == 0x4231
    assert thermostat_listener.attribute_updates[26][1] == 30
    assert thermostat_listener.attribute_updates[27][0] == 0x4232
    assert thermostat_listener.attribute_updates[27][1] == 1500
    assert thermostat_listener.attribute_updates[28][0] == 0x4240
    assert thermostat_listener.attribute_updates[28][1] == 12
    assert thermostat_listener.attribute_updates[29][0] == 0x4241
    assert thermostat_listener.attribute_updates[29][1] == 30
    assert thermostat_listener.attribute_updates[30][0] == 0x4242
    assert thermostat_listener.attribute_updates[30][1] == 1500
    assert thermostat_listener.attribute_updates[31][0] == 0x4250
    assert thermostat_listener.attribute_updates[31][1] == 17
    assert thermostat_listener.attribute_updates[32][0] == 0x4251
    assert thermostat_listener.attribute_updates[32][1] == 30
    assert thermostat_listener.attribute_updates[33][0] == 0x4252
    assert thermostat_listener.attribute_updates[33][1] == 2000
    assert thermostat_listener.attribute_updates[34][0] == 0x4260
    assert thermostat_listener.attribute_updates[34][1] == 22
    assert thermostat_listener.attribute_updates[35][0] == 0x4261
    assert thermostat_listener.attribute_updates[35][1] == 0
    assert thermostat_listener.attribute_updates[36][0] == 0x4262
    assert thermostat_listener.attribute_updates[36][1] == 1500
    assert thermostat_listener.attribute_updates[37][0] == 0x4002
    assert thermostat_listener.attribute_updates[37][1] == 0
    assert thermostat_listener.attribute_updates[38][0] == 0x0025
    assert thermostat_listener.attribute_updates[38][1] == 0
    assert thermostat_listener.attribute_updates[39][0] == 0x0002
    assert thermostat_listener.attribute_updates[39][1] == 0
    assert thermostat_listener.attribute_updates[40][0] == 0x4002
    assert thermostat_listener.attribute_updates[40][1] == 1
    assert thermostat_listener.attribute_updates[41][0] == 0x0025
    assert thermostat_listener.attribute_updates[41][1] == 1
    assert thermostat_listener.attribute_updates[42][0] == 0x0002
    assert thermostat_listener.attribute_updates[42][1] == 1
    assert thermostat_listener.attribute_updates[43][0] == 0x4002
    assert thermostat_listener.attribute_updates[43][1] == 2
    assert thermostat_listener.attribute_updates[44][0] == 0x0025
    assert thermostat_listener.attribute_updates[44][1] == 0
    assert thermostat_listener.attribute_updates[45][0] == 0x0002
    assert thermostat_listener.attribute_updates[45][1] == 1
    assert thermostat_listener.attribute_updates[46][0] == 0x4002
    assert thermostat_listener.attribute_updates[46][1] == 3
    assert thermostat_listener.attribute_updates[47][0] == 0x0025
    assert thermostat_listener.attribute_updates[47][1] == 0
    assert thermostat_listener.attribute_updates[48][0] == 0x0002
    assert thermostat_listener.attribute_updates[48][1] == 1
    assert thermostat_listener.attribute_updates[49][0] == 0x4002
    assert thermostat_listener.attribute_updates[49][1] == 4
    assert thermostat_listener.attribute_updates[50][0] == 0x0025
    assert thermostat_listener.attribute_updates[50][1] == 4
    assert thermostat_listener.attribute_updates[51][0] == 0x0002
    assert thermostat_listener.attribute_updates[51][1] == 1
    assert thermostat_listener.attribute_updates[52][0] == 0x4002
    assert thermostat_listener.attribute_updates[52][1] == 5
    assert thermostat_listener.attribute_updates[53][0] == 0x0025
    assert thermostat_listener.attribute_updates[53][1] == 0
    assert thermostat_listener.attribute_updates[54][0] == 0x0002
    assert thermostat_listener.attribute_updates[54][1] == 1
    assert thermostat_listener.attribute_updates[55][0] == 0x4002
    assert thermostat_listener.attribute_updates[55][1] == 6
    assert thermostat_listener.attribute_updates[56][0] == 0x0025
    assert thermostat_listener.attribute_updates[56][1] == 0
    assert thermostat_listener.attribute_updates[57][0] == 0x0002
    assert thermostat_listener.attribute_updates[57][1] == 1
    assert thermostat_listener.attribute_updates[58][0] == 0x4004
    assert thermostat_listener.attribute_updates[58][1] == 50
    assert thermostat_listener.attribute_updates[59][0] == 0x001E
    assert thermostat_listener.attribute_updates[59][1] == 4
    assert thermostat_listener.attribute_updates[60][0] == 0x0029
    assert thermostat_listener.attribute_updates[60][1] == 1

    assert len(onoff_listener.cluster_commands) == 0
    assert len(onoff_listener.attribute_updates) == 3
    assert onoff_listener.attribute_updates[0][0] == 0x6001
    assert onoff_listener.attribute_updates[0][1] == 5
    assert onoff_listener.attribute_updates[1][0] == 0x6000
    assert onoff_listener.attribute_updates[1][1] == 1600
    assert onoff_listener.attribute_updates[2][0] == 0x0000  # TARGET
    assert onoff_listener.attribute_updates[2][1] == 1

    thermostat_ui_listener = ClusterListener(valve_dev.endpoints[1].thermostat_ui)
    power_listener = ClusterListener(valve_dev.endpoints[1].power)

    frames = (
        ZCL_TUYA_VALVE_CHILD_LOCK_ON,
        ZCL_TUYA_VALVE_AUTO_LOCK_ON,
        ZCL_TUYA_VALVE_BATTERY_LOW,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_ui_listener.cluster_commands) == 0
    assert len(thermostat_ui_listener.attribute_updates) == 2
    assert thermostat_ui_listener.attribute_updates[0][0] == 0x0001
    assert thermostat_ui_listener.attribute_updates[0][1] == 1
    assert thermostat_ui_listener.attribute_updates[1][0] == 0x5000
    assert thermostat_ui_listener.attribute_updates[1][1] == 1

    assert len(power_listener.cluster_commands) == 0
    assert len(power_listener.attribute_updates) == 1
    assert power_listener.attribute_updates[0][0] == 0x0021
    assert power_listener.attribute_updates[0][1] == 10

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\xfa",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 0x00,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02\x04\x04\x00\x01\x00",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 0x02,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=3,
            data=b"\x01\x03\x00\x00\x03\x04\x04\x00\x01\x02",
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

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VALVE_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        _, status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=4,
            data=b"\x01\x04\x00\x00\x04\x02\x02\x00\x04\x00\x00\x00F",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        (status,) = await onoff_cluster.write_attributes(
            {
                "on_off": 0x00,
                "window_detection_timeout_minutes": 0x02,
                "window_detection_temperature": 2000,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=5,
            data=b"\x01\x05\x00\x00\x05\x68\x00\x00\x03\x00\x14\x02",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupancy": 0x00,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=6,
            data=b"\x01\x06\x00\x00\x06\x04\x04\x00\x01\x00",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupancy": 0x01,
                "programing_oper_mode": 0x00,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=7,
            data=b"\x01\x07\x00\x00\x07\x04\x04\x00\x01\x02",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x01,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=8,
            data=b"\x01\x08\x00\x00\x08\x04\x04\x00\x01\x01",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x04,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=9,
            data=b"\x01\x09\x00\x00\x09\x04\x04\x00\x01\x04",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "workday_schedule_1_temperature": 1700,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=10,
            data=b"\x01\x0a\x00\x00\x0a\x70\x00\x00\x12\x06\x00\x11\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "workday_schedule_1_minute": 45,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=11,
            data=b"\x01\x0b\x00\x00\x0b\x70\x00\x00\x12\x06\x2d\x14\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "workday_schedule_1_hour": 5,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=12,
            data=b"\x01\x0c\x00\x00\x0c\x70\x00\x00\x12\x05\x00\x14\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "weekend_schedule_1_temperature": 1700,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=13,
            data=b"\x01\x0d\x00\x00\x0d\x71\x00\x00\x12\x06\x00\x11\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "weekend_schedule_1_minute": 45,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=14,
            data=b"\x01\x0e\x00\x00\x0e\x71\x00\x00\x12\x06\x2d\x14\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "weekend_schedule_1_hour": 5,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=15,
            data=b"\x01\x0f\x00\x00\x0f\x71\x00\x00\x12\x05\x00\x14\x08\x00\x0f\x0b\x1e\x0f\x0c\x1e\x0f\x11\x1e\x14\x16\x00\x0f",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x01,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=16,
            data=b"\x01\x10\x00\x00\x10\x04\x04\x00\x01\x06",
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

        (status,) = await thermostat_ui_cluster.write_attributes(
            {
                "auto_lock": 0x00,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=17,
            data=b"\x01\x11\x00\x00\x11\x74\x01\x00\x01\x00",
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

        _, status = await onoff_cluster.command(0x0000)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=18,
            data=b"\x01\x12\x00\x00\x12\x68\x00\x00\x03\x00\x10\x05",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await onoff_cluster.command(0x0001)

        m1.assert_called_with(
            cluster=0xEF00,
            sequence=19,
            data=b"\x01\x13\x00\x00\x13\x68\x00\x00\x03\x01\x10\x05",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await onoff_cluster.command(0x0002)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=20,
            data=b"\x01\x14\x00\x00\x14\x68\x00\x00\x03\x00\x10\x05",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        (status,) = await onoff_cluster.write_attributes({})
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        _, status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND

        _, status = await onoff_cluster.command(0x0009)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND

        origdatetime = datetime.datetime
        datetime.datetime = MockDatetime

        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SET_TIME_REQUEST)
        tuya_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x24\x00\x08\x00\x00\x1c\x20\x00\x00\x0e\x10",
            command_id=0x24,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        datetime.datetime = origdatetime


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_electric_heating.MoesBHT,))
async def test_eheating_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    electric_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = electric_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(electric_dev.endpoints[1].thermostat)

    frames = (ZCL_TUYA_EHEAT_TEMPERATURE, ZCL_TUYA_EHEAT_TARGET_TEMP)
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 2
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 2100


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_electric_heating.MoesBHT,))
async def test_eheat_send_attribute(zigpy_device_from_quirk, quirk):
    """Test electric thermostat outgoing commands."""

    eheat_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = eheat_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = eheat_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\x10\x02\x00\x04\x00\x00\x00\x19",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x00,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=2,
            data=b"\x01\x02\x00\x00\x02\x01\x01\x00\x01\x00",
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

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x04,
            }
        )
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=3,
            data=b"\x01\x03\x00\x00\x03\x01\x01\x00\x01\x01",
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

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_EHEAT_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        _, status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=4,
            data=b"\x01\x04\x00\x00\x04\x10\x02\x00\x04\x00\x00\x00\x17",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize(
    "quirk, manufacturer",
    (
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TI, "_TZ3000_awgcnkrh"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TI, "_TZ3400_deyjhapk"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TI, "_some_random_manuf"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TO, "_TZ3000_pwgcnkrh"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TO, "_TZ3400_leyjhapk"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TO, "_some_random_manuf"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TI, "_TZ3000_owgcnkrh"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TI, "_TZ3400_keyjhapk"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TI, "_some_random_manuf"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TO, "_TZ3000_adkvzooy"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TO, "_TZ3400_keyjhapk"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TO, "another random manufacturer"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042NO, "_TZ3000_adkvzooy"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042NO, "_TYZB02_keyjhapk"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042NO, "another random manufacturer"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TI, "_TZ3000_bi6lpsew"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TI, "_TZ3000_a7ouggvs"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TI, "another random manufacturer"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TO, "_TZ3000_qzjcsmar"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TO, "_TZ3000_qzjcsmhd"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TO, "another random manufacturer"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043NO, "_TZ3000_qzjcsmar"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043NO, "_TYZB02_key8kk7r"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043NO, "another random manufacturer"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TI, "_TZ3000_hjgcnkgs"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TI, "_TZ3000_ojgcnkkl"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TI, "_some_random_manuf"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TO, "_TZ3400_cdyjhasw"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TO, "_TZ3400_pdyjhapl"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TO, "_some_random_manuf"),
    ),
)
async def test_tuya_wildcard_manufacturer(zigpy_device_from_quirk, quirk, manufacturer):
    """Test thermostatic valve outgoing commands."""

    zigpy_dev = zigpy_device_from_quirk(quirk, apply_quirk=False)
    zigpy_dev.manufacturer = manufacturer

    quirked_dev = get_device(zigpy_dev)
    assert isinstance(quirked_dev, quirk)


def test_ts0601_valve_signature(assert_signature_matches_quirk):
    """Test TS0601 valve remote signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZE200_81isopgh",
        "model": "TS0601",
        "class": "ts0601_valve.TuyaValve",
    }
    assert_signature_matches_quirk(zhaquirks.tuya.ts0601_valve.TuyaValve, signature)


def test_multiple_attributes_report():
    """Test a multi attribute report from Tuya device."""

    ep = mock.Mock()  # fake endpoint object

    message = (
        b"\x09\x7b\x02\x01\x0f\x01\x01\x00\x01\x01\x05\x02\x00\x04\x00\x00\x00\x07"
    )
    hdr, data = TuyaNewManufCluster(ep).deserialize(message)

    assert data
    assert data.data
    assert data.data.datapoints
    assert len(data.data.datapoints) == 2
    assert data.data.datapoints[0].dp == 1
    assert data.data.datapoints[1].dp == 5

    message = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x64\x0a\x02\x00\x04\x00\x00\x01\x68\x0b\x02\x00\x04\x00\x00\x00\xc8"
    hdr, data = TuyaNewManufCluster(ep).deserialize(message)

    assert data
    assert data.data
    assert data.data.datapoints
    assert len(data.data.datapoints) == 5
    assert data.data.datapoints[0].dp == 1
    assert data.data.datapoints[1].dp == 2
    assert data.data.datapoints[2].dp == 4
    assert data.data.datapoints[3].dp == 10
    assert data.data.datapoints[4].dp == 11

    message = b"\x09\xe1\x02\x0b\x34\x0c\x02\x00\x04\x00\x00\x00\x46\x0d\x02\x00\x04\x00\x00\x00\x14\x11\x02\x00\x04\x00\x00\x00\x1e\x09\x04\x00\x01\x01"
    hdr, data = TuyaNewManufCluster(ep).deserialize(message)

    assert data
    assert data.data
    assert data.data.datapoints
    assert len(data.data.datapoints) == 4
    assert data.data.datapoints[0].dp == 12
    assert data.data.datapoints[1].dp == 13
    assert data.data.datapoints[2].dp == 17
    assert data.data.datapoints[3].dp == 9


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
@pytest.mark.parametrize(
    "quirk",
    (zhaquirks.tuya.ts0501_fan_switch.TS0501FanSwitch,),
)
async def test_fan_switch_writes_attributes(zigpy_device_from_quirk, quirk):
    """Test that fan mode sequence attribute is written to the device when binding."""

    device = zigpy_device_from_quirk(quirk)
    fan_cluster = device.endpoints[1].fan

    with mock.patch.object(fan_cluster.endpoint, "request", mock.AsyncMock()) as m1:
        m1.return_value = (foundation.Status.SUCCESS, "done")

        await fan_cluster.bind()

        assert len(m1.mock_calls) == 1
        assert m1.mock_calls[0].kwargs["cluster"] == 514
        assert m1.mock_calls[0].kwargs["sequence"] == 1
        assert m1.mock_calls[0].kwargs["data"] == b"\x00\x01\x02\x01\x000\x00"


async def test_sm0202_motion_sensor_signature(assert_signature_matches_quirk):
    """Test LH992ZB motion sensor remote signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0402",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0500", "0xeeff"],
                "out_clusters": ["0x0019"],
            }
        },
        "manufacturer": "_TYZB01_z2umiwvq",
        "model": "SM0202",
        "class": "zhaquirks.tuya.lh992zb.TuyaMotionSM0202",
    }
    assert_signature_matches_quirk(zhaquirks.tuya.sm0202_motion.SM0202Motion, signature)


@pytest.mark.parametrize(
    "quirk",
    (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TOPlusA,),
)
async def test_power_config_no_bind(zigpy_device_from_quirk, quirk):
    """Test that the power configuration cluster is not bound and no attribute reporting is set up."""

    device = zigpy_device_from_quirk(quirk)
    power_cluster = device.endpoints[1].power

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    bind_patch = mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())

    with request_patch as request_mock, bind_patch as bind_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await power_cluster.bind()
        await power_cluster.configure_reporting(
            PowerConfiguration.attributes_by_name["battery_percentage_remaining"].id,
            3600,
            10800,
            1,
        )

        assert len(request_mock.mock_calls) == 0
        assert len(bind_mock.mock_calls) == 0


def test_ts1201_signature(assert_signature_matches_quirk):
    """Test TS1201 remote signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0xf000",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0xe004",
                    "0xed00",
                ],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZ3290_ot6ewjvmejq5ekhl",
        "model": "TS1201",
        "class": "zhaquirks.tuya.ts1201.ZosungIRBlaster",
    }
    assert_signature_matches_quirk(zhaquirks.tuya.ts1201.ZosungIRBlaster, signature)


@pytest.mark.parametrize("test_bytes", (b"\x00\x01\x02\x03\x04",))
def test_ts1201_ir_blaster_bytes(test_bytes):
    """Test quirk Byte helper class."""
    a, b = zhaquirks.tuya.ts1201.Bytes.deserialize(data=test_bytes)
    assert a == test_bytes
    assert b == b""


async def test_ts1201_ir_blaster(zigpy_device_from_quirk):
    """Test Tuya TS1201 IR blaster."""
    quirk = zhaquirks.tuya.ts1201.ZosungIRBlaster

    part_max_length = 0x38

    ir_code_to_learn = "A/AESQFAAwUIAvAErwHgAQNADwXwBK8BrwFABcADAXYfwAkBrwHACeABBwXwBK8BrwFABcAD4GgvAgRJAQ=="
    ir_code_to_learn_bytes = base64.b64decode(ir_code_to_learn)
    ir_code_to_learn_part1 = ir_code_to_learn_bytes[: part_max_length - 1]
    crc1 = 0
    for x in ir_code_to_learn_part1:
        crc1 = (crc1 + x) % 0x100
    ir_code_to_learn_part2 = ir_code_to_learn_bytes[part_max_length - 1 :]
    crc2 = 0
    for x in ir_code_to_learn_part2:
        crc2 = (crc2 + x) % 0x100

    # TV power off/on code
    ir_code_to_send = "B3wPfA/5AcoH4AUDAeUDgAPAC+AHB+AHA+ADN+ALBw=="  # codespell:ignore
    ir_msg = (
        f'{{"key_num":1,"delay":300,"key1":{{'
        f'"num":1,"freq":38000,"type":1,"key_code":"{ir_code_to_send}"}}}}'
    )
    ir_msg_length = len(ir_msg)
    position = 0
    control_cluster_id = 57348
    transmit_cluster_id = 60672

    ts1201_dev = zigpy_device_from_quirk(quirk)
    ts1201_control_cluster = ts1201_dev.endpoints[1].zosung_ircontrol
    ts1201_transmit_cluster = ts1201_dev.endpoints[1].zosung_irtransmit
    ts1201_transmit_listener = ClusterListener(ts1201_transmit_cluster)

    with mock.patch.object(
        ts1201_control_cluster.endpoint,
        "request",
        return_value=foundation.Status.SUCCESS,
    ) as m1:
        # study mode on
        rsp = await ts1201_control_cluster.command(0x0001, on_off=True)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=control_cluster_id,
            sequence=1,
            data=b"\x01\x01\x00" + b'{"study":0}',
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp == foundation.Status.SUCCESS

        # simulate receive_ir_frame_00 (first frame when device sends a learned code)
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x01k\x00\x01\x00=\x00\x00\x00\x00\x00\x00\x00\x04\xe0\x01\x04\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=3,
            data=(
                b"\x01\x03\x02\x01\x00"
                + struct.pack("<L", position)
                + struct.pack("<B", part_max_length)
            ),
            command_id=2,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[0][2].command.name
            == "receive_ir_frame_00"
        )
        assert ts1201_transmit_listener.cluster_commands[0][2].length == 61
        assert (
            ts1201_transmit_listener.cluster_commands[0][2].clusterid
            == control_cluster_id
        )
        assert ts1201_transmit_listener.cluster_commands[0][2].cmd == 0x04

        # simulate receive_ir_frame_01
        position += part_max_length - 1
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\tl\x03\x00\x01\x00\x00\x00\x00\x007\x03\xf0\x04I\x01@\x03\x05\x08\x02"
            b"\xf0\x04\xaf\x01\xe0\x01\x03@\x0f\x05\xf0\x04\xaf\x01\xaf\x01@\x05\xc0"
            b"\x03\x01v\x1f\xc0\t\x01\xaf\x01\xc0\t\xe0\x01\x07\x05\xf0\x04\xaf\x01"
            b"\xaf\x01@\x05\xc0\x03\xe0\xcd"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=4,
            data=(
                b"\x01\x04\x02\x01\x00"
                + struct.pack("<L", position)
                + struct.pack("<B", part_max_length)
            ),
            command_id=2,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[1][2].command.name
            == "resp_ir_frame_03"
        )
        assert ts1201_transmit_listener.cluster_commands[1][2].position == 0
        assert (
            ts1201_transmit_listener.cluster_commands[1][2].msgpart
            == ir_code_to_learn_part1
        )
        assert ts1201_transmit_listener.cluster_commands[1][2].msgpartcrc == crc1

        # simulate second receive_ir_frame_01
        position += part_max_length - 1
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\tm\x03\x00\x01\x007\x00\x00\x00\x06h/\x02\x04I\x01\xe7"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=5,
            data=b"\x01\x05\x04\x00\x01\x00\x00\x00",
            command_id=4,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[2][2].command.name
            == "resp_ir_frame_03"
        )
        assert (
            ts1201_transmit_listener.cluster_commands[2][2].position
            == position - part_max_length + 1
        )
        assert (
            ts1201_transmit_listener.cluster_commands[2][2].msgpart
            == ir_code_to_learn_part2
        )
        assert ts1201_transmit_listener.cluster_commands[2][2].msgpartcrc == crc2

        # simulate last receive_ir_frame_01
        hdr, args = ts1201_transmit_cluster.deserialize(b"\tn\x05\x01\x00\x00\x00")
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=control_cluster_id,
            sequence=6,
            data=b'\x01\x06\x00{"study":1}',
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[3][2].command.name
            == "resp_ir_frame_05"
        )

        # should return learned IR code
        succ, fail = await ts1201_control_cluster.read_attributes(
            ("last_learned_ir_code",)
        )
        assert succ[0] == ir_code_to_learn

        # test unknown attribute
        succ, fail = await ts1201_control_cluster.read_attributes(
            ("another_attribute",)
        )
        assert fail[0] == foundation.Status.UNSUPPORTED_ATTRIBUTE

        # IR send tests
        await ts1201_control_cluster.command(0x0002, code=ir_code_to_send)
        await wait_for_zigpy_tasks()
        # IR send must call ir transmit command id 0x00
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=7,
            data=(
                b"\x01\x07\x00\x01\x00"
                + struct.pack("<I", ir_msg_length)
                + b"\x00\x00\x00\x00"
                + struct.pack("<H", control_cluster_id)
                + b"\x01\x02\x00\x00"
            ),
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )

        # simulate receive_ir_frame_00
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x05\x02\x10\x01\x00\x01\x00z\x00\x00\x00\x00\x00\x00\x00\x04\xe0\x01\x02\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=9,
            data=(
                b"\x01\x09\x02\x01\x00\x00\x00\x00\x00"
                + struct.pack("<B", part_max_length)
            ),
            command_id=2,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[4][2].command.name
            == "receive_ir_frame_00"
        )
        assert ts1201_transmit_listener.cluster_commands[4][2].length == ir_msg_length
        assert (
            ts1201_transmit_listener.cluster_commands[4][2].clusterid
            == control_cluster_id
        )
        assert ts1201_transmit_listener.cluster_commands[4][2].cmd == 2

        # simulate receive_ir_frame_01
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x01f\x01\x00\x01\x00z\x00\x00\x00\x00\x00\x00\x00\x04\xe0\x01\x02\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        assert (
            ts1201_transmit_listener.cluster_commands[5][2].command.name
            == "receive_ir_frame_01"
        )
        assert ts1201_transmit_listener.cluster_commands[5][2].length == ir_msg_length
        assert (
            ts1201_transmit_listener.cluster_commands[5][2].clusterid
            == control_cluster_id
        )
        assert ts1201_transmit_listener.cluster_commands[5][2].cmd == 2

        # simulate receive_ir_frame_02
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x11g\x02\x01\x00\x00\x00\x00\x00@"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        assert (
            ts1201_transmit_listener.cluster_commands[6][2].command.name
            == "receive_ir_frame_02"
        )
        assert ts1201_transmit_listener.cluster_commands[6][2].position == 0
        assert ts1201_transmit_listener.cluster_commands[6][2].maxlen == 64

        # simulate receive_ir_frame_04
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x01i\x04\x00\x01\x00\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=11,
            data=b"\x01\x0b\x05\x01\x00\x00\x00",
            command_id=5,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[7][2].command.name
            == "receive_ir_frame_04"
        )

        # test raw data command
        rsp = await ts1201_control_cluster.command(
            0x0000, zhaquirks.tuya.ts1201.Bytes(b"\x00\x01\x02\x03\x04")
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=control_cluster_id,
            sequence=12,
            data=b"\x01\x0c\x00\x00\x01\x02\x03\x04",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert rsp == foundation.Status.SUCCESS

        # test unknown request from device
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x110\x06\x01\x00\x00\x00\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        assert (
            ts1201_transmit_listener.cluster_commands[8][2]
            == b"\x01\x00\x00\x00\x00\x00"
        )


def test_ts601_door_sensor_signature(assert_signature_matches_quirk):
    """Test TS601 Vibration Door Sensor signature against quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZE200_kzm5w4iz",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(zhaquirks.tuya.ts601_door.TS0601Door, signature)


@pytest.mark.parametrize(
    ("data", "endpoint_id", "ep_attr", "attribute", "expected_value"),
    [
        (
            b"\t\xfc\x02\x007\x01\x01\x00\x01\x01",
            zhaquirks.tuya.ts601_door.DOOR_HANDLE_EP_ID,
            IasZone.ep_attribute,
            IasZone.AttributeDefs.zone_status.id,
            ZoneStatus.Alarm_1,
        ),
        (
            b"\t\xfc\x02\x007\x01\x01\x00\x01\x00",
            zhaquirks.tuya.ts601_door.DOOR_HANDLE_EP_ID,
            IasZone.ep_attribute,
            IasZone.AttributeDefs.zone_status.id,
            0x0000,
        ),
        (
            b"\t\xfc\x02\x007\n\x04\x00\x01\x01",
            zhaquirks.tuya.ts601_door.VIBRATION_EP_ID,
            IasZone.ep_attribute,
            IasZone.AttributeDefs.zone_status.id,
            ZoneStatus.Alarm_1,
        ),
        (
            b"\t\xfc\x02\x007\n\x04\x00\x01\x00",
            zhaquirks.tuya.ts601_door.VIBRATION_EP_ID,
            IasZone.ep_attribute,
            IasZone.AttributeDefs.zone_status.id,
            0x0000,
        ),
        (
            b"\to\x02\x00P\x03\x02\x00\x04\x00\x00\x00T",
            zhaquirks.tuya.ts601_door.DP_HANDLER_EP_ID,
            PowerConfiguration.ep_attribute,
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
            84 * 2,
        ),
    ],
)
async def test_ts601_door_sensor(
    zigpy_device_from_quirk, data, endpoint_id, ep_attr, attribute, expected_value
):
    """Test TS601 Vibration Door Sensor quirk.

    The quirk is tested for:
        - Open/Closed door
        - Vibration On/Off
        - Remaining battery percentage
    """
    device: Device = zigpy_device_from_quirk(zhaquirks.tuya.ts601_door.TS0601Door)
    device._packet_debouncer.filter = mock.MagicMock(return_value=False)

    dp_processor_ep = zhaquirks.tuya.ts601_door.DP_HANDLER_EP_ID
    cluster = device.endpoints[dp_processor_ep].in_clusters[
        TuyaNewManufCluster.cluster_id
    ]

    with mock.patch.object(cluster, "send_default_rsp"):
        device.packet_received(
            t.ZigbeePacket(
                profile_id=zha.PROFILE_ID,
                src_ep=dp_processor_ep,
                cluster_id=TuyaNewManufCluster.cluster_id,
                data=t.SerializableBytes(data),
            )
        )

    cluster = getattr(device.endpoints[endpoint_id], ep_attr)
    attrs = await cluster.read_attributes(attributes=[attribute])

    assert attrs[0].get(attribute) == expected_value
