"""Test Tuya Air quality sensor."""

from unittest import mock
from unittest.mock import MagicMock

import pytest
import zigpy.profiles.zha

import zhaquirks
from zhaquirks.tuya import TuyaNewManufCluster
from zhaquirks.tuya.air.ts0601_air_quality import TuyaCO2Sensor
from zhaquirks.tuya.air.ts0601_smart_air import TuyaSmartAirSensor

zhaquirks.setup()


@pytest.fixture
def air_quality_device(zigpy_device_from_quirk):
    """Tuya Air Quality Sensor."""
    dev = zigpy_device_from_quirk(TuyaCO2Sensor)
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
            2 * 1e-6,
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

    air_quality_device.handle_message(
        zigpy.profiles.zha.PROFILE_ID, TuyaNewManufCluster.cluster_id, 1, 1, data
    )
    cluster = getattr(air_quality_device.endpoints[1], ep_attr)
    assert cluster.get("measured_value") == expected_value


@pytest.fixture
def smart_air_quality_device(zigpy_device_from_quirk):
    """Tuya Smart Air Quality Sensor."""
    dev = zigpy_device_from_quirk(TuyaSmartAirSensor)
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
            2 * 1e-6,
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
        (
            b"\t\xa5\x02\x00\x01\x14\x02\x00\x04\x00\x00\x00\x01",
            "pm25",
            1,
        ),
    ),
)
def test_smart_air_sensor(smart_air_quality_device, data, ep_attr, expected_value):
    """Test Tuya Smart Air Sensor."""

    smart_air_quality_device.handle_message(
        zigpy.profiles.zha.PROFILE_ID, TuyaNewManufCluster.cluster_id, 1, 1, data
    )
    cluster = getattr(smart_air_quality_device.endpoints[1], ep_attr)
    assert cluster.get("measured_value") == expected_value
