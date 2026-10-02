"""Tests for the AVATTO N-TRV16 TRV (_TZE204_vjpaih9f)."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()

MANUF = "_TZE204_vjpaih9f"
MODEL = "TS0601"

ATTR_PRESET_MODE = (0xEF << 8) | 2  # dp 2, exposed on the tuya manufacturer cluster
ATTR_LOCAL_TEMP_CALIBRATION = (0xEF << 8) | 47  # dp 47


@pytest.mark.parametrize(
    "msg, attr, value",
    [
        (
            b"\t\x01\x02\x00\x01\x02\x04\x00\x01\x00",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # dp 2, preset Manual (0x00) -> system_mode Heat
        (
            b"\t\x01\x02\x00\x01\x02\x04\x00\x01\x06",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Off,
        ),  # dp 2, preset Off (0x06) -> system_mode Off
        (
            b"\t\x01\x02\x00\x01\x03\x01\x00\x01\x01",
            Thermostat.AttributeDefs.running_state,
            Thermostat.RunningState.Heat_State_On,
        ),  # dp 3, valve open
        (
            b"\t\x01\x02\x00\x01\x04\x02\x00\x04\x00\x00\x00\xd2",
            Thermostat.AttributeDefs.occupied_heating_setpoint,
            2100,
        ),  # dp 4, setpoint 21.0C
        (
            b"\t\x01\x02\x00\x01\x05\x02\x00\x04\x00\x00\x00\xd7",
            Thermostat.AttributeDefs.local_temperature,
            2150,
        ),  # dp 5, current temp 21.5C
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, msg, attr, value):
    """Test incoming Tuya datapoints are mapped onto the thermostat cluster."""

    quirked = zigpy_device_from_v2_quirk(MANUF, MODEL)
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


async def test_handle_get_data_preset_mode_raw(zigpy_device_from_v2_quirk):
    """Dp 2 must also update the raw preset_mode attribute (select entity)."""

    quirked = zigpy_device_from_v2_quirk(MANUF, MODEL)
    ep = quirked.endpoints[1]

    tmcu_listener = ClusterListener(ep.tuya_manufacturer)

    # dp 2, preset Eco (0x02)
    msg = b"\t\x01\x02\x00\x01\x02\x04\x00\x01\x02"
    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert (ATTR_PRESET_MODE, 2) in tmcu_listener.attribute_updates
    assert ep.tuya_manufacturer.get(ATTR_PRESET_MODE) == 2


async def test_handle_get_data_local_temperature_calibration(
    zigpy_device_from_v2_quirk,
):
    """Dp 47 (local temperature calibration) is exposed on the tuya cluster."""

    quirked = zigpy_device_from_v2_quirk(MANUF, MODEL)
    ep = quirked.endpoints[1]

    tmcu_listener = ClusterListener(ep.tuya_manufacturer)

    # dp 47, calibration -1.5C
    msg = b"\t\x01\x02\x00\x01/\x02\x00\x04\xff\xff\xff\xf1"
    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert (ATTR_LOCAL_TEMP_CALIBRATION, -15) in tmcu_listener.attribute_updates
    assert ep.tuya_manufacturer.get(ATTR_LOCAL_TEMP_CALIBRATION) == -15


@pytest.mark.parametrize(
    "system_mode, dp_msg",
    [
        (
            Thermostat.SystemMode.Off,
            b"\x01\x01\x00\x00\x01\x02\x04\x00\x01\x06",
        ),  # -> preset Off (0x06)
        (
            Thermostat.SystemMode.Auto,
            b"\x01\x01\x00\x00\x01\x02\x04\x00\x01\x01",
        ),  # -> preset Schedule (0x01)
        (
            Thermostat.SystemMode.Heat,
            b"\x01\x01\x00\x00\x01\x02\x04\x00\x01\x00",
        ),  # -> preset Manual (0x00)
    ],
)
async def test_write_system_mode(zigpy_device_from_v2_quirk, system_mode, dp_msg):
    """Writing system_mode (climate on/off) must reach the device via dp 2.

    Regression test: dp 2 is shared between the ZCL `system_mode` attribute
    and the raw `preset_mode` attribute (tuya_dp_multi with two mappings), so
    the dp_converter is invoked with one positional value per mapping. A
    dp_converter that only accepts a single argument raises a TypeError on
    every write here.
    """

    quirked = zigpy_device_from_v2_quirk(MANUF, MODEL)
    ep = quirked.endpoints[1]

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await ep.thermostat.write_attributes({"system_mode": system_mode})
        await wait_for_zigpy_tasks()

        m1.assert_called_once_with(
            cluster=0xEF00,
            sequence=1,
            data=dp_msg,
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


async def test_write_preset_mode_does_not_raise(zigpy_device_from_v2_quirk):
    """Writing preset_mode directly (HA select entity) must not raise.

    Same dp_converter as test_write_system_mode is invoked here, since dp 2
    is shared by both attributes.
    """

    quirked = zigpy_device_from_v2_quirk(MANUF, MODEL)
    ep = quirked.endpoints[1]

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
    ):
        (status,) = await ep.tuya_manufacturer.write_attributes(
            {"preset_mode": 2}  # Eco
        )
        await wait_for_zigpy_tasks()

        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]
