"""Tests for the Zemismart SPM01V2 quirk."""

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener
from zhaquirks.tuya.mcu import TuyaMCUCluster

MANUFACTURER = "_TZE200_qhlxve78"
MODEL = "TS0601"


@pytest.fixture
def spm01v2(zigpy_device_from_v2_quirk):
    """Return a quirked SPM01V2 device."""
    return zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)


def get_tuya_cluster(device):
    """Return the Tuya MCU cluster."""
    cluster = device.endpoints[1].tuya_manufacturer
    assert cluster is not None
    assert isinstance(cluster, TuyaMCUCluster)
    return cluster


def send_dp(cluster: TuyaMCUCluster, tsn: int, dp_payload: bytes) -> foundation.Status:
    """Send a Tuya DP report to the cluster."""
    frame = bytes([0x09, tsn, 0x01]) + dp_payload
    _, data = cluster.deserialize(frame)
    return cluster.handle_get_data(data.data)


def test_spm01v2_cluster(spm01v2):
    """The device exposes the Tuya MCU cluster."""
    get_tuya_cluster(spm01v2)


@pytest.mark.parametrize(
    ("payload", "attribute", "expected"),
    [
        # DP1: 169348 / 100 = 1693.48 kWh
        (bytes.fromhex("00390102000400029584"), "energy", 169348),
        # DP2: 12345 / 100 = 123.45 kWh
        (bytes.fromhex("003A0202000400003039"), "produced_energy", 12345),
        # DP15: 100 %
        (bytes.fromhex("003C0F02000400000064"), "power_factor", 100),
        # DP101: 5000 / 100 = 50 Hz
        (bytes.fromhex("003D6502000400001388"), "ac_frequency", 5000),
        # DP102: 2341 / 10 = 234.1 V
        (bytes.fromhex("00476602000400000925"), "voltage", 2341),
        # DP103: 0 / 1000 = 0 A
        (bytes.fromhex("00486702000400000000"), "current", 0),
        # DP104: 0 W
        (bytes.fromhex("00496802000400000000"), "power", 0),
    ],
)
def test_spm01v2_datapoints(spm01v2, payload, attribute, expected):
    """Test Tuya datapoint decoding."""
    cluster = get_tuya_cluster(spm01v2)

    assert send_dp(cluster, 0x5A, payload) == foundation.Status.SUCCESS
    assert cluster.get(attribute) == expected


def test_spm01v2_unknown_dp(spm01v2):
    """Unknown datapoints must not break report processing."""
    cluster = get_tuya_cluster(spm01v2)
    listener = ClusterListener(cluster)

    # DP6: unknown RAW datapoint (8 bytes).
    payload = bytes.fromhex("003B060000080924000000000000")

    status = send_dp(cluster, 0x5B, payload)

    assert status == foundation.Status.SUCCESS
    assert listener.attribute_updates == []


def test_spm01v2_multiple_datapoints(spm01v2):
    """Several datapoints can be processed in one report."""
    cluster = get_tuya_cluster(spm01v2)

    # DP102, DP103 and DP104.
    payload = bytes.fromhex("0001660200040000092567020004000000006802000400000000")

    assert send_dp(cluster, 0x5C, payload) == foundation.Status.SUCCESS
    assert cluster.get("voltage") == 2341
    assert cluster.get("current") == 0
    assert cluster.get("power") == 0
