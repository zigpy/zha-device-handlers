"""Tests for Tuya Sensor quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from tests.common import wait_for_zigpy_tasks
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


@pytest.mark.parametrize(
    "manuf,model",
    [
        ("HOBEIAN", "ZG-303Z"),
        ("_TZE200_npj9bug3", "TS0601"),  # COOLO CS-201Z
    ],
)
async def test_hobeian_zg303z_soil_sensor(zigpy_device_from_v2_quirk, manuf, model):
    """Test HOBEIAN ZG-303Z soil moisture, temperature and humidity sensor."""

    quirked = zigpy_device_from_v2_quirk(manuf, model)
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    assert isinstance(tuya_cluster, TuyaMCUCluster)

    # standard humidity cluster is replaced by the DP 109 sensor
    assert not hasattr(ep, "humidity")

    report = TuyaCommand(
        status=0,
        tsn=2,
        datapoints=[
            TuyaDatapointData(3, TuyaData(45)),  # soil moisture 45 %
            TuyaDatapointData(5, TuyaData(215)),  # temperature 21.5 °C
            TuyaDatapointData(15, TuyaData(80)),  # battery 80 %
            TuyaDatapointData(106, TuyaData(0)),  # moisture: 0 = wet
            TuyaDatapointData(109, TuyaData(57)),  # air humidity 57 %
        ],
    )
    assert tuya_cluster.handle_get_data(report) == foundation.Status.SUCCESS

    assert ep.soil_moisture.get("measured_value") == 4500
    assert ep.temperature.get("measured_value") == 2150
    assert ep.power.get("battery_percentage_remaining") == 160
    assert tuya_cluster.get("moisture") is True
    assert tuya_cluster.get("humidity") == 57

    report = TuyaCommand(
        status=0,
        tsn=3,
        datapoints=[TuyaDatapointData(106, TuyaData(1))],  # 1 = dry
    )
    assert tuya_cluster.handle_get_data(report) == foundation.Status.SUCCESS
    assert tuya_cluster.get("moisture") is False


@pytest.mark.parametrize(
    "offset,raw",
    [
        (15, b"\x00\x00\x00\x0f"),  # +1.5 K, entity multiplier 0.1
        (-15, b"\xff\xff\xff\xf1"),  # -1.5 K
    ],
)
async def test_hobeian_zg303z_temperature_offset(
    zigpy_device_from_v2_quirk, offset, raw
):
    """Test that the temperature offset is written to DP 104 in 0.1 K steps."""

    quirked = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-303Z")
    tuya_cluster = quirked.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes({"temperature_offset": offset})
        await wait_for_zigpy_tasks()

    assert status == [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    # DP 104 (0x68), type VALUE (0x02), length 4
    assert m1.call_args.kwargs["data"].endswith(b"\x68\x02\x00\x04" + raw)
