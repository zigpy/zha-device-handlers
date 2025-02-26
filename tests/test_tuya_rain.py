"""Test for Tuya rain sensor."""

import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks

zhaquirks.setup()


ZCL_TUYA_RAIN_MV_01 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x00\x20"  # 32mv
ZCL_TUYA_RAIN_MV_02 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x01\xf4"  # 500mv


@pytest.mark.parametrize(
    "frame,value,rain_detected",
    [(ZCL_TUYA_RAIN_MV_01, 32, False), (ZCL_TUYA_RAIN_MV_02, 500, True)],
)
async def test_rain_sensor_state_report(
    zigpy_device_from_v2_quirk, frame, value, rain_detected
):
    """Test tuya rain sensor standard state reporting."""

    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer

    ias_listener = ClusterListener(rain_dev.endpoints[1].ias_zone)
    rain_listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(ias_listener.cluster_commands) == 0
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == IasZone.AttributeDefs.zone_status.id
    assert ias_listener.attribute_updates[0][1] == (
        IasZone.ZoneStatus.Alarm_1 if rain_detected else 0
    )

    assert len(rain_listener.cluster_commands) == 1
    assert len(rain_listener.attribute_updates) == 1
    assert rain_listener.attribute_updates[0][0] == 0xEF69
    assert rain_listener.attribute_updates[0][1] == value
