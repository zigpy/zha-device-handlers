"""Test for Tuya rain sensor."""

from datetime import UTC, datetime

import pytest
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import DataTypeId
from zigpy.zcl.helpers import UNMIGRATED_MANUFACTURER_CODE

from tests.common import ClusterListener, attribute_cache_row, deleted_rows
import zhaquirks
from zhaquirks.tuya import TUYA_CLUSTER_ID
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


def _manufacturer_code(rain_dev):
    """Return the manufacturer code of the invented Tuya attribute rows."""
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer
    attr_def = tuya_cluster.find_attribute("cleaning_reminder")

    return tuya_cluster._get_effective_manufacturer_code(attr_def)


def _rain_rows(rain_dev, typed):
    """Attribute rows the TS0207 quirk wrote while it invented its attributes."""
    values = {
        0xEF66: 150,  # average_light_intensity_20mins
        0xEF67: 2000,  # todays_max_light_intensity
        0xEF69: 300,  # rain_intensity
    }

    return [
        attribute_cache_row(
            rain_dev,
            TUYA_CLUSTER_ID,
            attr_id,
            t.uint32_t(value).serialize() if typed else value,
            DataTypeId.uint32 if typed else None,
            manufacturer_code=_manufacturer_code(rain_dev),
        )
        for attr_id, value in values.items()
    ]


@pytest.mark.parametrize("typed", [True, False])
def test_rain_sensor_attributes_migrated(zigpy_device_from_v2_quirk, typed):
    """Values of the attributes that became device values move into the store."""
    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer

    rows = [
        *_rain_rows(rain_dev, typed),
        # Still an attribute
        attribute_cache_row(
            rain_dev,
            TUYA_CLUSTER_ID,
            0xEF68,
            b"\x01",
            DataTypeId.bool_,
            manufacturer_code=_manufacturer_code(rain_dev),
        ),
        # Not mapped to a device value
        attribute_cache_row(rain_dev, TUYA_CLUSTER_ID, 0xEF07, 5),
        attribute_cache_row(rain_dev, TUYA_CLUSTER_ID, 0x7777, 6),
    ]

    result = rain_dev.load_attribute_cache(rows, migrate=True)

    values = rain_dev.store.namespace(RAIN_INTENSITY.namespace)
    assert values["average_light_intensity_20mins"] == 150
    assert values["todays_max_light_intensity"] == 2000
    assert rain_dev.store[RAIN_INTENSITY] == 300

    assert {row.attr_id for row in deleted_rows(result)} == {0xEF66, 0xEF67, 0xEF69}

    assert tuya_cluster.get("cleaning_reminder") == t.Bool.true
    assert tuya_cluster._attr_cache.get(0xEF07) == 5
    assert tuya_cluster._attr_cache.get(0x7777) == 6
    assert tuya_cluster._attr_cache.get(0xEF69) is None


def test_rain_sensor_attributes_not_migrated_without_quirk_load(
    zigpy_device_from_v2_quirk,
):
    """Rows are only migrated when zigpy loads them for a quirked device."""
    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")

    result = rain_dev.load_attribute_cache(_rain_rows(rain_dev, typed=True))

    assert not deleted_rows(result)
    assert RAIN_INTENSITY not in rain_dev.store
    assert rain_dev.endpoints[1].tuya_manufacturer._attr_cache.get(0xEF69) == 300


def test_rain_sensor_stored_value_kept(zigpy_device_from_v2_quirk):
    """A stored value updated after the attribute, or of a newer version, is kept."""
    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    rain_dev.store[RAIN_INTENSITY] = 42

    # Even one written by a newer version, which this one cannot read
    values = rain_dev.store.namespace(RAIN_INTENSITY.namespace)
    values.set("todays_max_light_intensity", {"lux": 1}, version=99)

    result = rain_dev.load_attribute_cache(
        _rain_rows(rain_dev, typed=True), migrate=True
    )

    assert len(deleted_rows(result)) == 3
    assert rain_dev.store[RAIN_INTENSITY] == 42
    assert values.item("todays_max_light_intensity").version == 99
    assert values["average_light_intensity_20mins"] == 150


def test_rain_sensor_newer_attribute_wins(zigpy_device_from_v2_quirk):
    """The attribute replaces a stored value it is newer than, or that is stale."""
    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    values = rain_dev.store.namespace(RAIN_INTENSITY.namespace)
    stored_at = datetime(2026, 6, 1, tzinfo=UTC)

    # Stored before going back to a quirk version with the attribute, which was then
    # updated, and forward again
    rain_dev.store.set(RAIN_INTENSITY, 42, last_updated=stored_at)

    # An older version without a migration is dropped when read
    values.set(
        "average_light_intensity_20mins",
        7,
        version=RAIN_INTENSITY.version - 1,
        last_updated=datetime(2026, 12, 1, tzinfo=UTC),
    )

    rows = [
        row._replace(last_updated=stored_at.timestamp() + 60)
        for row in _rain_rows(rain_dev, typed=True)
    ]
    result = rain_dev.load_attribute_cache(rows, migrate=True)

    assert len(deleted_rows(result)) == 3
    assert rain_dev.store[RAIN_INTENSITY] == 300
    assert rain_dev.store.last_updated(RAIN_INTENSITY) == datetime.fromtimestamp(
        stored_at.timestamp() + 60, UTC
    )
    assert values.item("average_light_intensity_20mins").value == 150


@pytest.mark.parametrize("newest_first", [True, False])
def test_rain_sensor_duplicate_rows(zigpy_device_from_v2_quirk, newest_first):
    """Of several rows of one attribute, the newest wins, whatever their order."""
    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    rows = [
        attribute_cache_row(
            rain_dev,
            TUYA_CLUSTER_ID,
            0xEF69,
            value,
            manufacturer_code=code,
            last_updated=last_updated,
        )
        for value, code, last_updated in [
            (300, _manufacturer_code(rain_dev), 2000),
            (100, UNMIGRATED_MANUFACTURER_CODE, 1000),
        ]
    ]

    if not newest_first:
        rows.reverse()

    result = rain_dev.load_attribute_cache(rows, migrate=True)

    assert len(deleted_rows(result)) == 2
    assert rain_dev.store[RAIN_INTENSITY] == 300


def test_rain_sensor_unstorable_value_dropped(zigpy_device_from_v2_quirk, caplog):
    """A value JSON cannot hold is logged and its row is dropped all the same."""
    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    row = attribute_cache_row(
        rain_dev,
        TUYA_CLUSTER_ID,
        0xEF69,
        float("nan"),
        manufacturer_code=UNMIGRATED_MANUFACTURER_CODE,
    )

    result = rain_dev.load_attribute_cache([row], migrate=True)

    assert deleted_rows(result) == [row]
    assert RAIN_INTENSITY not in rain_dev.store
    assert "Cannot store nan of datapoint 105 as device value" in caplog.text
