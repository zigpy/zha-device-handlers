"""Test for Tuya ZG-223Z rain sensor."""

import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks

zhaquirks.setup()


# DP 1: Rain detection (0 = no rain, 1 = raining)
ZCL_TUYA_RAIN_NONE = b"\t\x00\x02\x00\x00\x01\x04\x00\x01\x00"  # DP 1, value 0
ZCL_TUYA_RAIN_DETECTED = b"\t\x00\x02\x00\x00\x01\x04\x00\x01\x01"  # DP 1, value 1


@pytest.mark.parametrize(
    "frame, rain_detected",
    [
        (ZCL_TUYA_RAIN_NONE, False),
        (ZCL_TUYA_RAIN_DETECTED, True),
    ],
)
async def test_zg223z_rain_sensor_state_report(
    zigpy_device_from_v2_quirk, frame, rain_detected
):
    """Test HOBEIAN ZG-223Z rain sensor state reporting."""

    rain_dev = zigpy_device_from_v2_quirk("_TZE200_jsaqgakf", "TS0601")
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer
    ias_listener = ClusterListener(rain_dev.endpoints[1].ias_zone)

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(ias_listener.cluster_commands) == 0
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == IasZone.AttributeDefs.zone_status.id
    assert ias_listener.attribute_updates[0][1] == (
        IasZone.ZoneStatus.Alarm_1 if rain_detected else 0
    )
