"""Tests for Tuya Sensor quirks."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

import zhaquirks
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_sensor import TuyaTimeFormat

# Tuya datapoint type bytes (see zhaquirks.tuya.TuyaDPType)
_DP_VALUE = 0x02
_DP_ENUM = 0x04

# Temp DP 1, Humidity DP 2, Battery DP 3
TUYA_TEMP01_HUM02_BAT03 = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x03\x02\x00\x04\x00\x00\x00\x01"
# Temp DP 1, Humidity DP 2, Battery DP 4
TUYA_TEMP01_HUM02_BAT04 = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x01"
TUYA_USP = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\xff\x02\x00\x04\x00\x00\x00\x64"

ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6d\x82"

zhaquirks.setup()


def _tuya_dp(dp: int, dp_type: int, raw: bytes) -> bytes:
    """Serialize a single Tuya datapoint (dp, type, function=0, length, raw)."""
    return bytes([dp, dp_type, 0x00, len(raw)]) + raw


def _tuya_value(value: int) -> bytes:
    """Serialize a 4-byte big-endian signed VALUE datapoint payload."""
    return value.to_bytes(4, "big", signed=True)


def _tuya_frame(datapoints: list[tuple[int, int, bytes]]) -> bytes:
    """Build a Tuya get_data ZCL frame from (dp, dp_type, raw) datapoints."""
    # ZCL header (FC, TSN, command 0x02) + Tuya command status/tsn, matching
    # the hand-crafted frames above.
    frame = b"\x09\xe0\x02\x0b\x33"
    for dp, dp_type, raw in datapoints:
        frame += _tuya_dp(dp, dp_type, raw)
    return frame


@pytest.mark.parametrize(
    "model,manuf,rh_scale,temp_scale,test_neg",
    [
        ("_TZE200_bjawzodf", "TS0601", 10, 10, True),
        ("_TZE200_zl1kmjqx", "TS0601", 10, 10, True),
        ("_TZE200_a8sdabtg", "TS0601", 100, 10, False),  # Variant without screen, round
        ("_TZE200_qoy0ekbd", "TS0601", 100, 10, False),
        ("_TZE200_znbl8dj5", "TS0601", 100, 10, False),
        ("_TZE200_qyflbnbj", "TS0601", 100, 10, True),
        ("_TZE200_zppcgbdj", "TS0601", 100, 10, False),
        ("_TZE200_s1xgth2u", "TS0601", 100, 10, False),
        ("_TZE284_qyflbnbj", "TS0601", 100, 10, True),
        ("_TZE204_s139roas", "TS0601", 100, 10, False),
        ("_TZE200_bq5c8xfe", "TS0601", 100, 10, True),
        ("_TZE200_vs0skpuc", "TS0601", 100, 10, True),
        ("_TZE200_44af8vyi", "TS0601", 100, 10, True),
        ("_TZE200_lve3dvpy", "TS0601", 100, 10, False),  # TH01Z - Temp & humid w/ clock
        ("_TZE200_c7emyjom", "TS0601", 100, 10, False),
        ("_TZE200_locansqn", "TS0601", 100, 10, False),
        ("_TZE200_qrztc3ev", "TS0601", 100, 10, False),
        ("_TZE200_snloy4rw", "TS0601", 100, 10, False),
        ("_TZE200_eanjj2pa", "TS0601", 100, 10, False),
        ("_TZE200_ydrdfkim", "TS0601", 100, 10, False),
        ("_TZE284_locansqn", "TS0601", 100, 10, False),
        ("_TZE200_vvmbj46n", "TS0601", 100, 10, False),
        ("_TZE284_9ern5sfh", "TS0601", 10, 10, True),
    ],
)
async def test_handle_get_data(
    zigpy_device_from_v2_quirk, model, manuf, rh_scale, temp_scale, test_neg
):
    """Test handle_get_data for multiple attributes - normal battery."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.basic is not None
    assert isinstance(ep.basic, Basic)

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    message = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x64"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert (
        ep.temperature.get("measured_value")
        == data.data.datapoints[0].data.payload * temp_scale
    )

    assert (
        ep.humidity.get("measured_value")
        == data.data.datapoints[1].data.payload * rh_scale
    )

    assert (
        ep.power.get("battery_percentage_remaining")
        == data.data.datapoints[2].data.payload * 2
    )

    hdr, data = ep.tuya_manufacturer.deserialize(TUYA_USP)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.UNSUPPORTED_ATTRIBUTE

    if test_neg:
        message = b"\tH\x01\x00\xd8\x01\x02\x00\x04\x00\x00\xff\xe0"  # -3.1 deg c
        hdr, data = ep.tuya_manufacturer.deserialize(message)

        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

        assert ep.temperature.get("measured_value") == -310


@pytest.mark.parametrize(
    "model,manuf,rh_scale,temp_scale,state_rpt",
    [
        ("_TZE200_yjjdcqsq", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_yjjdcqsq", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_9yapgbuv", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_9yapgbuv", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE284_9yapgbuv", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_utkemkbs", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_utkemkbs", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_ksz749x8", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_upagmta9", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_upagmta9", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE200_cirvgep4", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_cirvgep4", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_jygvp6fk", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE284_upagmta9", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE204_1wnh8bqp", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
        ("_TZE284_1wnh8bqp", "TS0601", 100, 10, TUYA_TEMP01_HUM02_BAT03),
    ],
)
async def test_handle_get_data_enum_batt(
    zigpy_device_from_v2_quirk, model, manuf, rh_scale, temp_scale, state_rpt
):
    """Test handle_get_data for multiple attributes - enum battery."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    assert ep.basic is not None
    assert isinstance(ep.basic, Basic)

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    hdr, data = ep.tuya_manufacturer.deserialize(state_rpt)

    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    assert (
        ep.temperature.get("measured_value")
        == data.data.datapoints[0].data.payload * temp_scale
    )

    assert (
        ep.humidity.get("measured_value")
        == data.data.datapoints[1].data.payload * rh_scale
    )

    assert ep.power.get("battery_percentage_remaining") == 100

    hdr, data = ep.tuya_manufacturer.deserialize(TUYA_USP)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.UNSUPPORTED_ATTRIBUTE


def test_valid_attributes(zigpy_device_from_v2_quirk):
    """Test that valid attributes on virtual clusters are populated by Tuya datapoints mappings."""
    quirked = zigpy_device_from_v2_quirk("_TZE200_bjawzodf", "TS0601")
    ep = quirked.endpoints[1]

    temperature_attr_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    humidity_attr_id = RelativeHumidity.AttributeDefs.measured_value.id
    power_attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    temperature_cluster = ep.temperature
    humidity_cluster = ep.humidity
    power_config_cluster = ep.power

    assert isinstance(temperature_cluster, TuyaLocalCluster)
    assert isinstance(humidity_cluster, TuyaLocalCluster)
    assert isinstance(power_config_cluster, TuyaLocalCluster)

    # check that the virtual clusters have expected valid attributes
    assert {temperature_attr_id} == temperature_cluster._VALID_ATTRIBUTES
    assert {humidity_attr_id} == humidity_cluster._VALID_ATTRIBUTES
    assert {power_attr_id} == power_config_cluster._VALID_ATTRIBUTES


async def test_handle_get_data_hodyryli(zigpy_device_from_v2_quirk):
    """Test _TZE284_hodyryli: internal/external temp, humidity, battery, time format."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_hodyryli", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.basic is not None
    assert isinstance(ep.basic, Basic)
    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    # Positive values across every datapoint the quirk maps.
    message = _tuya_frame(
        [
            (1, _DP_VALUE, _tuya_value(210)),  # internal temperature 21.0 C
            (2, _DP_VALUE, _tuya_value(55)),  # humidity 55 %
            (3, _DP_VALUE, _tuya_value(1)),  # battery state 1 -> 100 (0-200 scale)
            (17, _DP_ENUM, bytes([TuyaTimeFormat.Time_12h])),  # time format 12h
            (38, _DP_VALUE, _tuya_value(250)),  # external probe 25.0 C
        ]
    )
    hdr, data = ep.tuya_manufacturer.deserialize(message)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert ep.temperature.get("measured_value") == 2100
    assert ep.humidity.get("measured_value") == 5500
    assert ep.power.get("battery_percentage_remaining") == 100
    assert ep.tuya_manufacturer.get("time_format") == TuyaTimeFormat.Time_12h
    assert ep.tuya_manufacturer.get("temperature_external") == 25.0

    # Negative values: sub-zero internal reading and a freezer probe reading.
    message = _tuya_frame(
        [
            (1, _DP_VALUE, _tuya_value(-55)),  # internal temperature -5.5 C
            (38, _DP_VALUE, _tuya_value(-180)),  # external probe -18.0 C
        ]
    )
    hdr, data = ep.tuya_manufacturer.deserialize(message)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert ep.temperature.get("measured_value") == -550
    assert ep.tuya_manufacturer.get("temperature_external") == -18.0

    # Unsupported datapoint is reported as such.
    hdr, data = ep.tuya_manufacturer.deserialize(TUYA_USP)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.UNSUPPORTED_ATTRIBUTE


@pytest.mark.parametrize(
    "battery_state,expected",
    [
        (0, 20),  # 10 % on the 0-200 battery_percentage_remaining scale
        (1, 100),  # 50 %
        (2, 200),  # 100 %
        (5, 0),  # unexpected state falls back to 0 instead of raising
    ],
)
async def test_hodyryli_battery_mapping(
    zigpy_device_from_v2_quirk, battery_state, expected
):
    """Test _TZE284_hodyryli DP 3 battery state -> percentage mapping."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_hodyryli", "TS0601")
    ep = quirked.endpoints[1]

    message = _tuya_frame([(3, _DP_VALUE, _tuya_value(battery_state))])
    hdr, data = ep.tuya_manufacturer.deserialize(message)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert ep.power.get("battery_percentage_remaining") == expected
