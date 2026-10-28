"""Test Tuya Air quality sensor."""

from unittest import mock
from unittest.mock import MagicMock

import pytest
import zigpy.profiles.zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.measurement import PM25

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya import TUYA_CLUSTER_ID, TUYA_QUERY_DATA, TuyaNewManufCluster
from zhaquirks.tuya.tuya_co import TuyaCO2Basic

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


# Frames captured from a real _TZE204_pkpfn9hc, cross-checked against its LCD.
PKPFN9HC_REPORTS = (
    (
        b"\x09\x3b\x02\x00\x31\x02\x02\x00\x04\x00\x00\x02\x68",
        "carbon_dioxide_concentration",
        616 * 1e-6,
    ),
    (b"\x09\x39\x02\x00\x2f\x12\x02\x00\x04\x00\x00\x01\x2e", "temperature", 3020),
    (b"\x09\x3a\x02\x00\x30\x13\x02\x00\x04\x00\x00\x00\x2a", "humidity", 4200),
)

# The unsolicited Basic report this device emits periodically and after a reboot.
PKPFN9HC_BASIC_REPORT = b"\x08\x63\x0a\x01\x00\x20\x4a\xe2\xff\x20\x38\xe4\xff\x20\x00"

# Its reply to one of the reads in the Tuya read attributes spell.
PKPFN9HC_READ_ATTRS_RSP = b"\x18\x02\x01\xfe\xff\x00\x30\x00"


@pytest.fixture
def pkpfn9hc_device(zigpy_device_from_v2_quirk):
    """Tuya TS0601 CO2 monitor built around a Winsen MH-Z19D."""
    dev = zigpy_device_from_v2_quirk("_TZE204_pkpfn9hc", "TS0601")
    dev._packet_debouncer.filter = MagicMock(return_value=False)
    cluster = dev.endpoints[1].in_clusters[TuyaNewManufCluster.cluster_id]
    with mock.patch.object(cluster, "send_default_rsp"):
        yield dev


def _receive(dev, cluster_id, data):
    """Feed a raw ZCL frame to the device."""
    dev.packet_received(
        t.ZigbeePacket(
            profile_id=zigpy.profiles.zha.PROFILE_ID,
            cluster_id=cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(data),
        )
    )


@pytest.mark.parametrize("data, ep_attr, expected_value", PKPFN9HC_REPORTS)
def test_pkpfn9hc_datapoints(pkpfn9hc_device, data, ep_attr, expected_value):
    """Test _TZE204_pkpfn9hc CO2, temperature and humidity datapoints."""
    _receive(pkpfn9hc_device, TuyaNewManufCluster.cluster_id, data)

    cluster = getattr(pkpfn9hc_device.endpoints[1], ep_attr)
    assert cluster.get("measured_value") == expected_value


async def test_pkpfn9hc_requeries_silent_mcu(pkpfn9hc_device):
    """A Basic report with no datapoints since the last one re-queries the MCU."""
    tuya_cluster = pkpfn9hc_device.endpoints[1].in_clusters[TUYA_CLUSTER_ID]
    assert not tuya_cluster.reported_since_last_check

    created = []
    with (
        mock.patch.object(TuyaCO2Basic, "QUERY_DELAY", 0),
        mock.patch.object(
            pkpfn9hc_device,
            "create_task",
            side_effect=lambda coro, name=None: created.append(coro),
        ),
        mock.patch.object(tuya_cluster, "command", new=mock.AsyncMock()) as command,
    ):
        _receive(pkpfn9hc_device, Basic.cluster_id, PKPFN9HC_BASIC_REPORT)
        assert len(created) == 1
        await created[0]

    command.assert_awaited_once_with(TUYA_QUERY_DATA)


async def test_pkpfn9hc_does_not_requery_reporting_mcu(pkpfn9hc_device):
    """A Basic report is ignored while the MCU is still sending datapoints."""
    # A datapoint report marks the MCU as alive.
    _receive(pkpfn9hc_device, TuyaNewManufCluster.cluster_id, PKPFN9HC_REPORTS[0][0])
    tuya_cluster = pkpfn9hc_device.endpoints[1].in_clusters[TUYA_CLUSTER_ID]
    assert tuya_cluster.reported_since_last_check

    created = []
    with mock.patch.object(
        pkpfn9hc_device,
        "create_task",
        side_effect=lambda coro, name=None: created.append(coro),
    ):
        _receive(pkpfn9hc_device, Basic.cluster_id, PKPFN9HC_BASIC_REPORT)

    assert created == []
    # The flag is cleared, so a second silent interval does trigger a query.
    assert not tuya_cluster.reported_since_last_check


async def test_pkpfn9hc_ignores_non_attribute_reports(pkpfn9hc_device):
    """Other Basic general commands do not re-query the MCU.

    The MCU is silent here, so a Report_Attributes would trigger a query. Only
    that command may do so, otherwise the read attributes spell would make the
    device query itself in a loop.
    """
    tuya_cluster = pkpfn9hc_device.endpoints[1].in_clusters[TUYA_CLUSTER_ID]
    assert not tuya_cluster.reported_since_last_check

    created = []
    with mock.patch.object(
        pkpfn9hc_device,
        "create_task",
        side_effect=lambda coro, name=None: created.append(coro),
    ):
        _receive(pkpfn9hc_device, Basic.cluster_id, PKPFN9HC_READ_ATTRS_RSP)

    assert created == []
