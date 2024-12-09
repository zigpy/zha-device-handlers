"""Tests for Tuya Smoke Detector."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,battery_test",
    [
        ("_TZE200_dq1mfjug", "TS0601", []),
        ("_TZE200_m9skfctm", "TS0601", []),
        ("_TZE200_ntcy3xu1", "TS0601", []),
        ("_TZE200_rccxox8p", "TS0601", []),
        ("_TZE200_vzekyi4c", "TS0601", []),
        ("_TZE204_vawy74yh", "TS0601", []),
        (
            "_TZE204_ntcy3xu1",
            "TS0601",
            (
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x02", 200),
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x01", 80),
                (b"\x09\x3a\x02\x00\x12\x0e\x04\x00\x01\x00", 10),
            ),
        ),
        ("_TZE284_0zaf1cr8", "TS0601", []),
        ("_TZ3210_up3pngle", "TS0205", []),
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, model, manuf, battery_test):
    """Test handle_get_data for multiple attributes."""

    zone_status_id = IasZone.AttributeDefs.zone_status.id

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    ias_listener = ClusterListener(ep.ias_zone)

    message = b"\x09\x39\x02\x00\x11\x01\x04\x00\x01\x00"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zone_status_id
    assert ias_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    assert ep.ias_zone.get(zone_status_id) == IasZone.ZoneStatus.Alarm_1

    message = b"\x09\x3b\x02\x00\x13\x01\x04\x00\x01\x01"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zone_status_id
    assert ias_listener.attribute_updates[1][1] == 0

    assert ep.ias_zone.get(zone_status_id) == 0

    for message, state in battery_test:
        power_listener = ClusterListener(ep.power)

        hdr, data = ep.tuya_manufacturer.deserialize(message)
        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

        assert len(power_listener.attribute_updates) == 1
        assert power_listener.attribute_updates[0][1] == state
