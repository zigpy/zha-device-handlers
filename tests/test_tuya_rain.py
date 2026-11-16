"""Test for Tuya rain sensor."""

import pytest
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.tuya_rain import RAIN_INTENSITY

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

    # The rain intensity is a device value, not an attribute of the Tuya cluster
    assert len(rain_listener.cluster_commands) == 1
    assert len(rain_listener.attribute_updates) == 0
    assert rain_dev.store[RAIN_INTENSITY] == value


@pytest.mark.parametrize(
    "dp_id,key",
    [(102, "average_light_intensity_20mins"), (103, "todays_max_light_intensity")],
)
async def test_rain_sensor_light_intensity(zigpy_device_from_v2_quirk, dp_id, key):
    """Test that the light intensity datapoints are kept as device values."""

    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer
    rain_listener = ClusterListener(tuya_cluster)

    frame = b"\tp\x02\x00\x02" + bytes([dp_id]) + b"\x02\x00\x04\x00\x00\x03\xe8"
    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(rain_listener.attribute_updates) == 0
    assert key not in tuya_cluster.attributes_by_name
    assert rain_dev.store.namespace(RAIN_INTENSITY.namespace)[key] == 1000
