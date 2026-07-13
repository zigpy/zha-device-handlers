"""Tests for Tuya Sensor quirks."""

import math

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

import zhaquirks
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData, TuyaLocalCluster
from zhaquirks.tuya.mcu import TuyaMCUCluster

# Temp DP 1, Humidity DP 2, Battery DP 3
TUYA_TEMP01_HUM02_BAT03 = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x03\x02\x00\x04\x00\x00\x00\x01"
# Temp DP 1, Humidity DP 2, Battery DP 4
TUYA_TEMP01_HUM02_BAT04 = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x01"
TUYA_USP = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\xff\x02\x00\x04\x00\x00\x00\x64"

ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6d\x82"

zhaquirks.setup()


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


@pytest.mark.parametrize(
    "raw_battery_state,expected_percent",
    [
        (0, 40),  # Low
        (1, 120),  # Middle
        (2, 200),  # High
        (99, 0),  # unmapped/unexpected raw value -> defaults to 0 rather than raising
    ],
)
async def test_soil_sensor_0ints6wl(
    zigpy_device_from_v2_quirk, raw_battery_state, expected_percent
):
    """Test _TZE284_0ints6wl: enum battery (dp=14) and illuminance (dp=102).

    This variant differs from the _TZE284_aao3yzhs group: battery is a 3-tier
    enum on dp=14 (not a 0-100 percentage on dp=15), and it also reports
    illuminance on dp=102, which no known upstream quirk maps.
    """

    quirked = zigpy_device_from_v2_quirk("_TZE284_0ints6wl", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    tuya_cluster = ep.tuya_manufacturer

    tuya_cluster.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[
                TuyaDatapointData(5, TuyaData(215)),  # temperature, scale 10
                TuyaDatapointData(3, TuyaData(42)),  # soil moisture, default scale 100
                TuyaDatapointData(102, TuyaData(6377)),  # illuminance, raw lux
                TuyaDatapointData(14, TuyaData(raw_battery_state)),  # battery enum
            ],
        )
    )

    assert ep.temperature.get("measured_value") == 2150
    assert ep.soil_moisture.get("measured_value") == 4200
    assert ep.illuminance.get("measured_value") == 10000 * math.log10(6377) + 1
    assert ep.power.get("battery_percentage_remaining") == expected_percent


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
