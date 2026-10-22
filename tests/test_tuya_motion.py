"""Tests for Tuya quirks."""

import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder import (
    PERCENTAGE,
    NumberDeviceClass,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
import zhaquirks.tuya
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.mcu import TuyaMCUCluster

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x01\x01\x00\x01\x01"  # DP 1
ZCL_TUYA_MOTION_V2 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x01"  # DP 101
ZCL_TUYA_MOTION_V3 = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"  # DP 3, enum
ZCL_TUYA_MOTION_V4 = b"\tL\x01\x00\x05\x69\x01\x00\x01\x01"  # DP 105
ZCL_TUYA_MOTION_V5 = b"\tL\x01\x00\x05\x01\x01\x00\x01\x04"  # DP 1, motion is 0x04
ZCL_TUYA_MOTION_V6 = b"\tL\x01\x00\x05\x01\x04\x00\x01\x02"  # DP 1, enum
ZCL_TUYA_MOTION_V7 = b"\tL\x01\x00\x05\x01\x01\x00\x01\x00"  # DP 1, Inv
ZCL_TUYA_MOTION_V8 = b"\tL\x01\x00\x05\x65\x01\x00\x01\x00"  # DP 101, Inv


zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,occ_msg",
    [
        ("_TZE200_ya4ft0w4", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ya4ft0w4", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_7hfcudw5", "TS0601", ZCL_TUYA_MOTION_V2),
        ("_TZE200_ppuj1vem", "TS0601", ZCL_TUYA_MOTION_V2),
        ("_TZE200_ar0slwnd", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_mrf6vtua", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_sfiy5tfs", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_sooucan5", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_wukb7rhc", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_qasjif9e", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_ztc6ggyl", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ztc6ggyl", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ztqnh5cg", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_sbyx0lm6", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_clrdrnya", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_dtzziy1e", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_iaeejhvf", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_mtoaryre", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_mp902om5", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_pfayrzcw", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE284_4qznlkbu", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_sbyx0lm6", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_muvkrjr5", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_kyhbrfyl", "TS0601", ZCL_TUYA_MOTION),
        ("_TZ6210_duv6fhwt", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_1youk3hj", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_3towulqd", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE200_1ibpyhdc", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE200_bh3n6gk8", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE200_ttcovulf", "TS0601", ZCL_TUYA_MOTION_V7),
        ("_TZE204_sxm7l9xa", "TS0601", ZCL_TUYA_MOTION_V4),
        ("_TZE204_e5m9c5hl", "TS0601", ZCL_TUYA_MOTION_V4),
        ("_TZE204_dapwryy7", "TS0601", ZCL_TUYA_MOTION_V6),
        ("_TZE204_uxllnywp", "TS0601", ZCL_TUYA_MOTION_V5),
        ("_TZE200_gjldowol", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_2aaelwxk", "TS0225", ZCL_TUYA_MOTION),
        ("_TZE200_crq3r3la", "CK-BL702-MWS-01(7016)", ZCL_TUYA_MOTION),
        ("HOBEIAN", "CK-BL702-MWS-01(7016)", ZCL_TUYA_MOTION),
        ("_TZE200_2aaelwxk", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE200_kb5noeto", "TS0601", ZCL_TUYA_MOTION),
        ("_TZE204_ex3rcdha", "TS0601", ZCL_TUYA_MOTION_V8),
    ],
)
async def test_tuya_motion_quirk_occ(zigpy_device_from_v2_quirk, model, manuf, occ_msg):
    """Test Tuya Motion Quirks using Occupancy cluster."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.occupancy is not None
    assert isinstance(ep.occupancy, OccupancySensing)

    occupancy_listener = ClusterListener(ep.occupancy)

    hdr, data = ep.tuya_manufacturer.deserialize(occ_msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    zcl_occupancy_id = OccupancySensing.AttributeDefs.occupancy.id

    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == zcl_occupancy_id
    assert (
        occupancy_listener.attribute_updates[0][1]
        == OccupancySensing.Occupancy.Occupied
    )


@pytest.mark.parametrize(
    "model,manuf,occ_msg",
    [
        ("_TYST11_i5j6ifxj", "5j6ifxj", ZCL_TUYA_MOTION_V3),
        ("_TYST11_7hfcudw5", "hfcudw5", ZCL_TUYA_MOTION_V3),
    ],
)
@pytest.mark.asyncio
async def test_tuya_motion_quirk_ias(zigpy_device_from_v2_quirk, model, manuf, occ_msg):
    """Test Tuya Motion Quirks using IasZone cluster."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.ias_zone is not None
    assert isinstance(ep.ias_zone, IasZone)

    # lower reset_s of IasZone cluster
    ep.ias_zone.reset_s = 0

    ias_zone_listener = ClusterListener(ep.ias_zone)

    hdr, data = ep.tuya_manufacturer.deserialize(occ_msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    zcl_zone_status_id = IasZone.AttributeDefs.zone_status.id

    # check that the zone status is set to alarm_1
    assert len(ias_zone_listener.attribute_updates) == 1
    assert ias_zone_listener.attribute_updates[0][0] == zcl_zone_status_id
    assert ias_zone_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    await asyncio.sleep(0.01)

    # check that the zone status is reset automatically
    assert len(ias_zone_listener.attribute_updates) == 2
    assert ias_zone_listener.attribute_updates[1][0] == zcl_zone_status_id
    assert ias_zone_listener.attribute_updates[1][1] == 0


@pytest.mark.parametrize(
    "model,manuf,illum_msg,exp_value",
    [
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x00", 10),
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x01", 20),
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x02", 50),
        ("_TZE204_1youk3hj", "TS0601", b"\tL\x01\x00\x05\x66\x04\x00\x01\x03", 100),
    ],
)
async def test_tuya_motion_quirk_enum_illum(
    zigpy_device_from_v2_quirk, model, manuf, illum_msg, exp_value
):
    """Test Tuya Motion Quirks using enum illumination."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.illuminance is not None
    assert isinstance(ep.illuminance, IlluminanceMeasurement)

    illum_listener = ClusterListener(ep.illuminance)

    hdr, data = ep.tuya_manufacturer.deserialize(illum_msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    zcl_illum_id = IlluminanceMeasurement.AttributeDefs.measured_value.id

    assert len(illum_listener.attribute_updates) == 1
    assert illum_listener.attribute_updates[0][0] == zcl_illum_id
    assert illum_listener.attribute_updates[0][1] == exp_value


@pytest.mark.parametrize(
    "msg,attr_name,exp_value",
    [
        # frames captured from a HOBEIAN ZG-204ZX
        (
            b"\x19\x4b\x02\x00\x4b\x04\x02\x00\x04\x00\x00\x01\xb5",
            "detection_distance",
            437,
        ),
        (
            b"\x19\x61\x02\x00\x61\x69\x02\x00\x04\xff\xff\xff\xec",
            "temperature_offset",
            -20,
        ),
    ],
)
async def test_hobeian_zg204zx_settings(
    zigpy_device_from_v2_quirk, msg, attr_name, exp_value
):
    """Test the ZG-204ZX maps its setting datapoints."""
    quirked_device = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-204ZX")
    tuya_cluster = quirked_device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)

    hdr, data = tuya_cluster.deserialize(msg)
    status = tuya_cluster.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS
    assert tuya_listener.attribute_updates == [
        (tuya_cluster.attributes_by_name[attr_name].id, exp_value)
    ]


async def test_hobeian_zg204zx_zcl_measurements(zigpy_device_from_v2_quirk):
    """Test the ZG-204ZX keeps its ZCL measurement clusters."""
    quirked_device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-204ZX",
        cluster_ids={
            1: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                IlluminanceMeasurement.cluster_id: ClusterType.Server,
                TemperatureMeasurement.cluster_id: ClusterType.Server,
                RelativeHumidity.cluster_id: ClusterType.Server,
                OccupancySensing.cluster_id: ClusterType.Server,
            }
        },
    )
    ep = quirked_device.endpoints[1]

    for cluster in (
        ep.power,
        ep.illuminance,
        ep.temperature,
        ep.humidity,
        ep.occupancy,
    ):
        assert not isinstance(cluster, TuyaLocalCluster)

    # the datapoint copy of the temperature follows the unit setting: 70.5 °F
    temperature_listener = ClusterListener(ep.temperature)
    hdr, data = ep.tuya_manufacturer.deserialize(
        b"\x19\x07\x02\x00\x07\x6f\x02\x00\x04\x00\x00\x02\xc1"
    )
    ep.tuya_manufacturer.handle_get_data(data.data)

    assert temperature_listener.attribute_updates == []


def test_hobeian_zg204zx_entities(zigpy_device_from_v2_quirk):
    """Test the ZG-204ZX setting entities and the hidden default entities."""
    quirked_device = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-204ZX")
    quirk = DEVICE_REGISTRY.match_entry(quirked_device).zha_device_factory
    definition = quirk.quirk_definition

    numbers = {
        metadata.resolved_unique_id_suffix: (
            metadata.device_class,
            metadata.unit,
            metadata.min,
            metadata.max,
            metadata.step,
            metadata.multiplier,
        )
        for metadata in definition.entity_metadata
        if hasattr(metadata, "multiplier")
    }
    assert numbers == {
        "static_detection_sensitivity": (None, None, 0, 10, 1, None),
        "detection_distance": (
            NumberDeviceClass.DISTANCE,
            UnitOfLength.CENTIMETERS,
            0,
            500,
            1,
            None,
        ),
        "presence_timeout": (
            NumberDeviceClass.DURATION,
            UnitOfTime.SECONDS,
            0,
            28800,
            1,
            None,
        ),
        "humidity_offset": (NumberDeviceClass.HUMIDITY, PERCENTAGE, -30, 30, 1, None),
        "temperature_offset": (
            NumberDeviceClass.TEMPERATURE_DELTA,
            UnitOfTemperature.CELSIUS,
            -2,
            2,
            0.1,
            0.1,
        ),
        "illuminance_interval": (
            NumberDeviceClass.DURATION,
            UnitOfTime.MINUTES,
            1,
            720,
            1,
            None,
        ),
        "motion_detection_sensitivity": (None, None, 0, 10, 1, None),
    }

    ias_rule, pir_rule = definition.disabled_default_entities
    assert ias_rule.cluster_id == IasZone.cluster_id
    assert ias_rule.function(type("IASZone", (), {})())
    assert pir_rule.cluster_id == OccupancySensing.cluster_id
    assert pir_rule.function(SimpleNamespace(translation_key="pir_o_to_u_delay"))
    assert pir_rule.function(SimpleNamespace(translation_key="pir_u_to_o_delay"))
    assert not pir_rule.function(SimpleNamespace(translation_key=None))


@pytest.mark.parametrize(
    "attr_name,value,dp_data",
    [
        ("temperature_offset", -15, b"\x69\x02\x00\x04\xff\xff\xff\xf1"),
        ("detection_distance", 437, b"\x04\x02\x00\x04\x00\x00\x01\xb5"),
        ("led_indicator", True, b"\x6c\x01\x00\x01\x01"),
    ],
)
async def test_hobeian_zg204zx_write(
    zigpy_device_from_v2_quirk, attr_name, value, dp_data
):
    """Test the ZG-204ZX writes its settings as datapoints."""
    quirked_device = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-204ZX")
    tuya_cluster = quirked_device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        (status,) = await tuya_cluster.write_attributes({attr_name: value})
        await wait_for_zigpy_tasks()

    assert status == [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    assert request_mock.call_args.kwargs["data"].endswith(dp_data)
