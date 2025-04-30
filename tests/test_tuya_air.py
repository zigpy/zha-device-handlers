"""Test Tuya Air quality sensor."""

from unittest import mock
from unittest.mock import MagicMock

import pytest
import zigpy.profiles.zha
import zigpy.types as t
from zigpy.zcl.clusters.measurement import PM25

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya import TuyaNewManufCluster

zhaquirks.setup()


@pytest.fixture
def air_quality_device(zigpy_device_from_v2_quirk):
    """Tuya Air Quality Sensor."""
    dev = zigpy_device_from_v2_quirk("_TZE200_8ygsuhe1", "TS0601")
    dev._packet_debouncer.filter = MagicMock(return_value=False)
    cluster = dev.endpoints[1].in_clusters[TuyaNewManufCluster.cluster_id]
    with mock.patch.object(cluster, "send_default_rsp"):
        yield dev


@pytest.mark.parametrize(
    "data, ep_attr, expected_value",
    (
        (
            b"\t2\x01\x00\x02\x02\x02\x00\x04\x00\x00\x01r",
            "carbon_dioxide_concentration",
            370 * 1e-6,
        ),
        (
            b"\t$\x01\x00\x00\x13\x02\x00\x04\x00\x00\x02\xd6",
            "humidity",
            7260,
        ),
        (
            b"\t\x03\x01\x00\x01\x15\x02\x00\x04\x00\x00\x00\x01",
            "voc_level",
            1 * 1e-6,
        ),
        (
            b"\t\x02\x01\x00\x01\x16\x02\x00\x04\x00\x00\x00\x02",
            "formaldehyde_concentration",
            2 * 1e-8,
        ),
        (
            b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\x01 ",
            "temperature",
            2880,
        ),
        (
            b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xfb",
            "temperature",
            -50,
        ),
        (
            b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xef",
            "temperature",
            -170,
        ),
    ),
)
def test_co2_sensor(air_quality_device, data, ep_attr, expected_value):
    """Test Tuya Air Quality Sensor."""

    air_quality_device.packet_received(
        t.ZigbeePacket(
            profile_id=zigpy.profiles.zha.PROFILE_ID,
            cluster_id=TuyaNewManufCluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(data),
        )
    )
    cluster = getattr(air_quality_device.endpoints[1], ep_attr)
    assert cluster.get("measured_value") == expected_value


# XXX: variant 00 is not used, PM2.5 is untested for sensors
TUYA_AIR_TEST_VAR00 = (
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\x01 ",
        "temperature",
        2880,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xfb",
        "temperature",
        -50,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xef",
        "temperature",
        -170,
    ),
    (
        b"\t$\x01\x00\x00\x13\x02\x00\x04\x00\x00\x02\xd6",
        "humidity",
        7260,
    ),
    (
        b"\t2\x01\x00\x02\x02\x02\x00\x04\x00\x00\x01r",
        "carbon_dioxide_concentration",
        370 * 1e-6,
    ),
    (
        b"\t\xa5\x02\x00\x01\x14\x02\x00\x04\x00\x00\x00\x01",
        "pm25",
        1,
    ),
    (
        b"\t\x03\x01\x00\x01\x15\x02\x00\x04\x00\x00\x00\x01",
        "voc_level",
        1 * 1e-6,
    ),
    (
        b"\t\x02\x01\x00\x01\x16\x02\x00\x04\x00\x00\x00\x02",
        "formaldehyde_concentration",
        2 * 1e-8,
    ),
)

TUYA_AIR_TEST_VAR01 = (
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\x01 ",
        "temperature",
        2880,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xfb",
        "temperature",
        -50,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xef",
        "temperature",
        -170,
    ),
    (
        b"\t$\x01\x00\x00\x13\x02\x00\x04\x00\x00\x02\xd6",
        "humidity",
        7260,
    ),
    (
        b"\t2\x01\x00\x02\x16\x02\x00\x04\x00\x00\x01r",
        "carbon_dioxide_concentration",
        370 * 1e-6,
    ),
    (
        b"\t\x03\x01\x00\x01\x15\x02\x00\x04\x00\x00\x00\x01",
        "voc_level",
        1 * 1e-6,
    ),
    (
        b"\t\x02\x01\x00\x01\x02\x02\x00\x04\x00\x00\x00\x02",
        "formaldehyde_concentration",
        2 * 1e-8,
    ),
)

TUYA_AIR_TEST_VAR02 = (
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\x01 ",
        "temperature",
        2880,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xfb",
        "temperature",
        -50,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xef",
        "temperature",
        -170,
    ),
    (
        b"\t$\x01\x00\x00\x13\x02\x00\x04\x00\x00\x02\xd6",
        "humidity",
        7260,
    ),
    (
        b"\t\x02\x01\x00\x01\x14\x02\x00\x04\x00\x00\x00\x02",
        "formaldehyde_concentration",
        2 * 1e-8,
    ),
    (
        b"\t\x03\x01\x00\x01\x15\x02\x00\x04\x00\x00\x00\x01",
        "voc_level",
        1 * 1e-6,
    ),
    (
        b"\t2\x01\x00\x02\x16\x02\x00\x04\x00\x00\x01r",
        "carbon_dioxide_concentration",
        370 * 1e-6,
    ),
)
TUYA_AIR_TEST_VAR03 = (
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\x01 ",
        "temperature",
        2880,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xfb",
        "temperature",
        -50,
    ),
    (
        b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xef",
        "temperature",
        -170,
    ),
    (
        b"\t$\x01\x00\x00\x13\x02\x00\x04\x00\x00\x02\xd6",
        "humidity",
        7260,
    ),
    (
        b"\t\x02\x01\x00\x01\x02\x02\x00\x04\x00\x00\x00\x02",
        "formaldehyde_concentration",
        2 * 1e-10,
    ),
    (
        b"\t\x03\x01\x00\x01\x15\x02\x00\x04\x00\x00\x00\x01",
        "voc_level",
        1 * 1e-7,
    ),
    (
        b"\t2\x01\x00\x02\x16\x02\x00\x04\x00\x00\x01r",
        "carbon_dioxide_concentration",
        370 * 1e-6,
    ),
)
TUYA_AIR_TEST_VAR04 = (  # Good
    (
        (
            b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\x01 ",
            "temperature",
            2880,
        ),
        (
            b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xfb",
            "temperature",
            -50,
        ),
        (
            b"\t\x02\x01\x00\x00\x12\x02\x00\x04\x00\x00\xff\xef",
            "temperature",
            -170,
        ),
        (
            b"\t$\x01\x00\x00\x13\x02\x00\x04\x00\x00\x02\xd6",
            "humidity",
            7260,
        ),
        (
            b"\t\x02\x01\x00\x01\x16\x02\x00\x04\x00\x00\x00\x02",
            "formaldehyde_concentration",
            2 * 1e-8,
        ),
        (
            b"\t\x03\x01\x00\x01\x15\x02\x00\x04\x00\x00\x00\x01",
            "voc_level",
            1 * 1e-6,
        ),
        (
            b"\t2\x01\x00\x02\x02\x02\x00\x04\x00\x00\x01r",
            "carbon_dioxide_concentration",
            370 * 1e-6,
        ),
    )
)


@pytest.mark.parametrize(
    "model, manuf, test_plan",
    (
        ("_TZE200_dwcarsat", "TS0601", TUYA_AIR_TEST_VAR02),
        ("_TZE204_dwcarsat", "TS0601", TUYA_AIR_TEST_VAR02),
        ("_TZE200_ryfmq5rl", "TS0601", TUYA_AIR_TEST_VAR03),
        ("_TZE200_mja3fuja", "TS0601", TUYA_AIR_TEST_VAR01),
        ("_TZE200_7bztmfm1", "TS0601", TUYA_AIR_TEST_VAR04),
        ("_TZE200_8ygsuhe1", "TS0601", TUYA_AIR_TEST_VAR04),
        ("_TZE200_yvx5lh6k", "TS0601", TUYA_AIR_TEST_VAR04),
        ("_TZE204_yvx5lh6k", "TS0601", TUYA_AIR_TEST_VAR04),
        ("_TZE200_c2fmom5z", "TS0601", TUYA_AIR_TEST_VAR04),
        ("_TZE204_c2fmom5z", "TS0601", TUYA_AIR_TEST_VAR04),
    ),
)
def test_smart_air_sensor(zigpy_device_from_v2_quirk, model, manuf, test_plan):
    """Test Tuya Smart Air Sensor."""

    dev = zigpy_device_from_v2_quirk(model, manuf)

    for data, ep_attr, expected_value in test_plan:
        dev._packet_debouncer.filter = MagicMock(return_value=False)
        cluster = dev.endpoints[1].in_clusters[TuyaNewManufCluster.cluster_id]
        with mock.patch.object(cluster, "send_default_rsp"):
            dev.packet_received(
                t.ZigbeePacket(
                    profile_id=zigpy.profiles.zha.PROFILE_ID,
                    cluster_id=TuyaNewManufCluster.cluster_id,
                    src_ep=1,
                    dst_ep=1,
                    data=t.SerializableBytes(data),
                )
            )
            cluster = getattr(dev.endpoints[1], ep_attr)
            assert cluster.get("measured_value") == expected_value


async def test_smart_air_pm25_dropping_high_values(zigpy_device_from_v2_quirk):
    """Test Tuya Smart Air Sensor _TZE200_dwcarsat dropping high PM2.5 values."""

    dev = zigpy_device_from_v2_quirk("_TZE200_dwcarsat", "TS0601")
    pm25_cluster = dev.endpoints[1].pm25
    pm25_listener = ClusterListener(pm25_cluster)

    # check that valid value updates the attribute
    # We call the Tuya TuyaLocalCluster update_attribute method which accepts a string,
    # it'll call the underlying _update_attribute method with the id then.
    pm25_cluster.update_attribute(PM25.AttributeDefs.measured_value.name, 1000)
    assert len(pm25_listener.attribute_updates) == 1
    assert pm25_listener.attribute_updates[0][1] == 1000

    # check that invalid value is ignored
    pm25_cluster.update_attribute(PM25.AttributeDefs.measured_value.name, 1001)
    assert len(pm25_listener.attribute_updates) == 1
