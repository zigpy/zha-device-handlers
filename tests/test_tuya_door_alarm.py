"""Tests for the Tuya door/window sensor with siren alarm."""

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

ZCL_TUYA_DOOR_ALARM_CONTACT = b"\tL\x01\x00\x05\x01\x01\x00\x01\x01"  # DP 1, open
ZCL_TUYA_DOOR_ALARM_CLOSED = b"\tL\x01\x00\x05\x01\x01\x00\x01\x00"  # DP 1, closed
ZCL_TUYA_DOOR_ALARM_BATTERY = b"\tL\x01\x00\x05\x02\x02\x00\x04\x00\x00\x00\x5a"  # DP 2
ZCL_TUYA_DOOR_ALARM_SIREN = b"\tL\x01\x00\x05\x65\x01\x00\x01\x01"  # DP 101
ZCL_TUYA_DOOR_ALARM_STROBE = b"\tL\x01\x00\x05\x66\x01\x00\x01\x01"  # DP 102
ZCL_TUYA_DOOR_ALARM_VOLUME = (
    b"\tL\x01\x00\x05\x67\x02\x00\x04\x00\x00\x00\x1e"  # DP 103
)
ZCL_TUYA_DOOR_ALARM_DURATION = (
    b"\tL\x01\x00\x05\x68\x02\x00\x04\x00\x00\x00\x0a"  # DP 104
)

zhaquirks.setup()


async def _report(quirked, msg):
    """Feed a tuya datapoint report into the device and return the status."""
    ep = quirked.endpoints[1]
    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    return ep.tuya_manufacturer.handle_get_data(data.data)


@pytest.mark.asyncio
async def test_tuya_door_alarm_quirk(zigpy_device_from_v2_quirk):
    """Test the Tuya door/window sensor with siren alarm."""
    quirked = zigpy_device_from_v2_quirk("_TZE284_u8ouaqsz", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    # DP 1: contact. The device reports a non-zero value for an open contact.
    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_CONTACT) is foundation.Status.SUCCESS
    )
    assert ep.ias_zone.get("zone_status") == IasZone.ZoneStatus.Alarm_1

    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_CLOSED) is foundation.Status.SUCCESS
    )
    assert ep.ias_zone.get("zone_status") == 0

    # DP 2: battery percentage. The datapoint holds percent, the ZCL attribute
    # is scaled by two (ZHA divides it by two again when formatting).
    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_BATTERY) is foundation.Status.SUCCESS
    )
    assert ep.power.get("battery_percentage_remaining") == 180

    # DP 101: siren
    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_SIREN) is foundation.Status.SUCCESS
    )
    assert ep.tuya_manufacturer.get("alarm") == t.Bool.true

    # DP 102: blinking light
    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_STROBE) is foundation.Status.SUCCESS
    )
    assert ep.tuya_manufacturer.get("strobe") == t.Bool.true

    # DP 103: volume in percent
    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_VOLUME) is foundation.Status.SUCCESS
    )
    assert ep.tuya_manufacturer.get("volume") == 30

    # DP 104: duration in seconds
    assert (
        await _report(quirked, ZCL_TUYA_DOOR_ALARM_DURATION)
        is foundation.Status.SUCCESS
    )
    assert ep.tuya_manufacturer.get("duration") == 10


def test_tuya_door_alarm_does_not_skip_configuration(zigpy_device_from_v2_quirk):
    """The quirk must not skip the configuration.

    The device only accepts the arming datapoint (DP 101) after the Tuya
    "spell" has been cast, which happens during the normal configuration.
    Skipping it makes the device refuse every arming attempt.
    """
    raw = zigpy_device_from_v2_quirk("_TZE284_u8ouaqsz", "TS0601")
    assert not raw.skip_configuration
