"""Test for Tuya water leak sensor."""

import pytest

from tests.common import ClusterListener
import zhaquirks

zhaquirks.setup()

ZCL_TUYA_WATER_PRESENCE = bytes.fromhex("09 e0 02 01 e9 01 04 00 01 01")
ZCL_TUYA_WATER_ABSENCE = bytes.fromhex("09 e0 02 01 e9 01 04 00 01 00")
ZCL_TUYA_WATER_LEAK_TRUE = bytes.fromhex("09 e1 02 01 ea 66 04 00 01 01")
ZCL_TUYA_WATER_LEAK_FALSE = bytes.fromhex("09 e1 02 01 ea 66 04 00 01 00")
ZCL_TUYA_BATTERY_37 = bytes.fromhex("09 da 02 01 e5 04 02 00 04 00 00 00 25")
ZCL_TUYA_BATTERY_100 = bytes.fromhex("09 da 02 01 e5 04 02 00 04 00 00 00 64")
ZCL_TUYA_ALARM_MODE_0 = bytes.fromhex("09 f0 02 01 f9 65 04 00 01 00")
ZCL_TUYA_ALARM_MODE_1 = bytes.fromhex("09 f0 02 01 f9 65 04 00 01 01")
ZCL_TUYA_RINGTONE_0 = bytes.fromhex("09 db 02 01 e6 67 04 00 01 00")
ZCL_TUYA_RINGTONE_2 = bytes.fromhex("09 db 02 01 e6 67 04 00 01 02")


@pytest.mark.parametrize(
    "frame, expected_value",
    [
        (ZCL_TUYA_WATER_PRESENCE, True),
        (ZCL_TUYA_WATER_ABSENCE, False),
        (ZCL_TUYA_WATER_LEAK_TRUE, True),
        (ZCL_TUYA_WATER_LEAK_FALSE, False),
    ],
)
async def test_water_sensors_state_report(
    zigpy_device_from_v2_quirk, frame, expected_value
):
    """Test water presence and leak sensors."""

    dev = zigpy_device_from_v2_quirk("_TZE284_1di7ujzp", "TS0601")
    tuya_cluster = dev.endpoints[1].tuya_manufacturer

    tuya_listener = ClusterListener(tuya_cluster)
    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(tuya_listener.attribute_updates) == 1
    assert tuya_listener.attribute_updates[0][1] == expected_value


@pytest.mark.parametrize(
    "frame, expected_value",
    [
        (ZCL_TUYA_ALARM_MODE_0, 0),
        (ZCL_TUYA_ALARM_MODE_1, 1),
        (ZCL_TUYA_RINGTONE_0, 0),
        (ZCL_TUYA_RINGTONE_2, 2),
    ],
)
async def test_sensor_and_enum_state_report(
    zigpy_device_from_v2_quirk, frame, expected_value
):
    """Test battery sensor and enum attributes."""

    dev = zigpy_device_from_v2_quirk("_TZE284_1di7ujzp", "TS0601")
    tuya_cluster = dev.endpoints[1].tuya_manufacturer

    tuya_listener = ClusterListener(tuya_cluster)
    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(tuya_listener.attribute_updates) == 1
    assert tuya_listener.attribute_updates[0][1] == expected_value


@pytest.mark.parametrize(
    "frame, expected_value",
    [
        (ZCL_TUYA_BATTERY_37, 37),
        (ZCL_TUYA_BATTERY_100, 100),
    ],
)
async def test_battery_via_tuya_cluster(
    zigpy_device_from_v2_quirk, frame, expected_value
):
    """Test battery level via Tuya cluster."""

    dev = zigpy_device_from_v2_quirk("_TZE284_1di7ujzp", "TS0601")

    tuya_cluster = dev.endpoints[1].tuya_manufacturer
    power_cluster = dev.endpoints[1].power

    listener = ClusterListener(power_cluster)
    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(listener.attribute_updates) == 1
    # Due to half-percent precision
    assert listener.attribute_updates[0][1] == expected_value * 2
