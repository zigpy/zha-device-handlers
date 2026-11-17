"""Tests for Tuya DIN power meters."""

import pytest
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.tuya.ts0601_din_power

zhaquirks.setup()

RMS_CURRENT = ElectricalMeasurement.AttributeDefs.rms_current.id
RMS_VOLTAGE = ElectricalMeasurement.AttributeDefs.rms_voltage.id


@pytest.mark.parametrize(
    "frame,current,voltage",
    (
        # Older firmware: 4-byte value, current (mA) << 16 | voltage (0.1 V)
        (
            bytes.fromhex("09 28 02 00 c8 06 02 00 04 07 fc 09 66"),
            2044,
            240.6,
        ),
        # Newer firmware: 15-byte raw block, captured from a _TZE200_bkkmqmyo meter
        # 583 W, 36 var, PF 0.801, 3.087 A, 235.6 V
        (
            bytes.fromhex(
                "09 28 02 00 c8 06 00 00 0f"
                " 00 00 02 47 00 00 00 24 03 21 00 0c 0f 09 34"
            ),
            3087,
            235.6,
        ),
        # 577 W, 39 var, PF 0.806, 3.036 A, 235.6 V
        (
            bytes.fromhex(
                "09 36 02 00 d5 06 00 00 0f"
                " 00 00 02 41 00 00 00 27 03 26 00 0b dc 09 34"
            ),
            3036,
            235.6,
        ),
        # 608 W, 37 var, PF 0.803, 3.213 A, 235.6 V
        (
            bytes.fromhex(
                "09 43 02 00 e2 06 00 00 0f"
                " 00 00 02 60 00 00 00 25 03 23 00 0c 8d 09 34"
            ),
            3213,
            235.6,
        ),
    ),
)
async def test_hiking_power_meter_voltage_current(
    zigpy_device_from_quirk, frame, current, voltage
):
    """Test that both datapoint 6 formats are decoded into current and voltage."""

    device = zigpy_device_from_quirk(zhaquirks.tuya.ts0601_din_power.HikingPowerMeter)
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    measurement_listener = ClusterListener(device.endpoints[1].electrical_measurement)

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert measurement_listener.attribute_updates == [
        (RMS_CURRENT, current),
        (RMS_VOLTAGE, voltage),
    ]


async def test_hiking_power_meter_unknown_voltage_current_length(
    zigpy_device_from_quirk,
):
    """Test that an unknown datapoint 6 length is ignored instead of raising."""

    device = zigpy_device_from_quirk(zhaquirks.tuya.ts0601_din_power.HikingPowerMeter)
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    measurement_listener = ClusterListener(device.endpoints[1].electrical_measurement)

    hdr, args = tuya_cluster.deserialize(
        bytes.fromhex("09 28 02 00 c8 06 00 00 03 00 0c 0f")
    )
    tuya_cluster.handle_message(hdr, args)

    assert measurement_listener.attribute_updates == []
