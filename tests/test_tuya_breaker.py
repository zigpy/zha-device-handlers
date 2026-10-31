"""Tests for TS011F smart circuit breaker quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.device import CustomZigpyDevice
import zhaquirks.tuya.ts011f_breaker as breaker_mod
from zhaquirks.tuya.ts011f_breaker import (
    CMD_OPTIONS_2,
    CMD_OPTIONS_3,
    SETTINGS_BY_NAME,
    TongouProtectionCluster,
    TongouThresholdCluster,
    decode_records,
    encode_record,
)

zhaquirks.setup()

CLUSTER_IDS = {
    1: {
        Basic.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        Groups.cluster_id: ClusterType.Server,
        Scenes.cluster_id: ClusterType.Server,
        OnOff.cluster_id: ClusterType.Server,
        Metering.cluster_id: ClusterType.Server,
        ElectricalMeasurement.cluster_id: ClusterType.Server,
        TemperatureMeasurement.cluster_id: ClusterType.Server,
        0xE000: ClusterType.Server,
        0xE001: ClusterType.Server,
        Ota.cluster_id: ClusterType.Client,
        Time.cluster_id: ClusterType.Client,
    }
}

# Sample group reports:
# 0xE7: over_current (1) = ON, 32A; over_voltage (3) = ON, 250V; under_voltage (4) = OFF, 180V
SAMPLE_E7_REPORT = (
    bytes([1, 1, 0x00, 32]) + bytes([3, 1, 0x00, 250]) + bytes([4, 0, 0x00, 180])
)
# 0xE6: temperature (5) = ON, 80C; power (7) = OFF, 10kW
SAMPLE_E6_REPORT = bytes([5, 1, 0x00, 80]) + bytes([7, 0, 0x00, 10])


def _make_report_hdr(command_id: int, tsn: int = 1) -> foundation.ZCLHeader:
    """Create a Server_to_Client ZCL cluster command header."""
    return foundation.ZCLHeader.cluster(
        tsn=tsn,
        command_id=command_id,
        direction=foundation.Direction.Server_to_Client,
    )


@pytest.fixture
def breaker_device(zigpy_device_from_v2_quirk):
    """Return a quirked TS011F breaker device."""
    return zigpy_device_from_v2_quirk(
        "_TZ3000_cayepv1a",
        "TS011F",
        cluster_ids=CLUSTER_IDS,
    )


@pytest.mark.parametrize(
    "manufacturer",
    [
        "_TZ3000_cayepv1a",
        "_TZ3000_zrm3oxsh",
    ],
)
def test_ts011f_breaker_signature_match(zigpy_device_from_v2_quirk, manufacturer):
    """Verify both Tongou and EARU variants match the v2 quirk and replace clusters."""
    device = zigpy_device_from_v2_quirk(
        manufacturer,
        "TS011F",
        cluster_ids=CLUSTER_IDS,
    )
    assert isinstance(device, CustomZigpyDevice)

    ep = device.endpoints[1]
    assert isinstance(ep.tuya_external_switch_type, TongouThresholdCluster)
    assert isinstance(ep.tongou_protection, TongouProtectionCluster)
    assert TemperatureMeasurement.cluster_id in ep.in_clusters


def test_encode_decode_records():
    """Test 4-byte record encoding and decoding, including unknown IDs and trailing bytes."""
    setting = SETTINGS_BY_NAME["over_voltage"]
    encoded = encode_record(setting, True, 260)
    assert encoded == bytes([3, 1, 0x01, 0x04])

    # Append an unknown setting ID (99) and 2 trailing partial bytes
    raw = encoded + bytes([99, 0, 0x00, 0x10, 0xFF, 0xFF])
    decoded = list(decode_records(raw))
    assert decoded == [(3, True, 260), (99, False, 16)]


def test_inbound_reports_update_attributes(breaker_device):
    """Test that incoming 0xE6 and 0xE7 cluster reports fire attribute updates on 0xFC70."""
    ep = breaker_device.endpoints[1]
    threshold_cluster = ep.tuya_external_switch_type
    protection_cluster = ep.tongou_protection
    listener = ClusterListener(protection_cluster)

    assert protection_cluster.get("over_current_threshold") is None
    assert protection_cluster.get("over_current_enabled") is None

    # Deliver 0xE7 report (plus an unknown sid=99 to test skipping)
    args_e7 = threshold_cluster.client_commands[CMD_OPTIONS_3].schema(
        data=SAMPLE_E7_REPORT + bytes([99, 1, 0, 50])
    )
    threshold_cluster.handle_cluster_request(_make_report_hdr(CMD_OPTIONS_3), args_e7)

    attr_defs = TongouProtectionCluster.AttributeDefs
    assert (attr_defs.over_current_enabled.id, True) in listener.attribute_updates
    assert (attr_defs.over_current_threshold.id, 32) in listener.attribute_updates
    assert (attr_defs.over_voltage_enabled.id, True) in listener.attribute_updates
    assert (attr_defs.over_voltage_threshold.id, 250) in listener.attribute_updates
    assert (attr_defs.under_voltage_enabled.id, False) in listener.attribute_updates
    assert (attr_defs.under_voltage_threshold.id, 180) in listener.attribute_updates

    # Deliver 0xE6 report
    args_e6 = threshold_cluster.client_commands[CMD_OPTIONS_2].schema(
        data=SAMPLE_E6_REPORT
    )
    threshold_cluster.handle_cluster_request(_make_report_hdr(CMD_OPTIONS_2), args_e6)

    assert (attr_defs.temperature_enabled.id, True) in listener.attribute_updates
    assert (attr_defs.temperature_threshold.id, 80) in listener.attribute_updates
    assert (attr_defs.power_enabled.id, False) in listener.attribute_updates
    assert (attr_defs.power_threshold.id, 10) in listener.attribute_updates


async def test_write_attribute_when_cached(breaker_device):
    """Test writing a threshold when current settings are already cached."""
    ep = breaker_device.endpoints[1]
    threshold_cluster = ep.tuya_external_switch_type
    protection_cluster = ep.tongou_protection

    # Seed initial state via report: over_current enabled=True, threshold=32A
    protection_cluster.report_received(CMD_OPTIONS_3, SAMPLE_E7_REPORT)

    async def fake_command(command_id: int, payload: bytes):
        assert command_id == CMD_OPTIONS_3
        assert payload == bytes([1, 1, 0x00, 40])
        protection_cluster.report_received(CMD_OPTIONS_3, bytes([1, 1, 0x00, 40]))
        return foundation.Status.SUCCESS

    with mock.patch.object(
        threshold_cluster, "command", side_effect=fake_command
    ) as cmd_mock:
        res = await protection_cluster.write_attributes({"over_current_threshold": 40})

    assert cmd_mock.call_count == 1
    assert res == [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.SUCCESS,
                protection_cluster.AttributeDefs.over_current_threshold.id,
            )
        ]
    ]
    assert protection_cluster.get("over_current_threshold") == 40


async def test_write_attribute_fetches_when_unknown(breaker_device):
    """Test that writing an attribute first queries the group if state is unknown."""
    ep = breaker_device.endpoints[1]
    threshold_cluster = ep.tuya_external_switch_type
    protection_cluster = ep.tongou_protection

    calls = []

    async def fake_command(command_id: int, payload: bytes):
        calls.append((command_id, payload))
        if payload == b"":
            protection_cluster.report_received(CMD_OPTIONS_2, SAMPLE_E6_REPORT)
        else:
            protection_cluster.report_received(CMD_OPTIONS_2, bytes([5, 0, 0x00, 80]))
        return foundation.Status.SUCCESS

    with mock.patch.object(threshold_cluster, "command", side_effect=fake_command):
        res = await protection_cluster.write_attributes({"temperature_enabled": False})

    assert calls == [
        (CMD_OPTIONS_2, b""),
        (CMD_OPTIONS_2, bytes([5, 0, 0x00, 80])),
    ]
    assert res[0][0].status == foundation.Status.SUCCESS
    assert protection_cluster.get("temperature_enabled") is False
    assert protection_cluster.get("temperature_threshold") == 80


async def test_write_validation_and_rejection(breaker_device):
    """Test out-of-range values and hardware write rejection return Status.FAILURE."""
    ep = breaker_device.endpoints[1]
    threshold_cluster = ep.tuya_external_switch_type
    protection_cluster = ep.tongou_protection

    protection_cluster.report_received(CMD_OPTIONS_3, SAMPLE_E7_REPORT)

    # 1. Out-of-bounds threshold (under_voltage max is 220V)
    with mock.patch.object(threshold_cluster, "command") as cmd_mock:
        res = await protection_cluster.write_attributes(
            {"under_voltage_threshold": 230}
        )
    assert cmd_mock.call_count == 0
    assert res[0][0].status == foundation.Status.FAILURE

    # 2. Breaker refuses the new value and reports back the old value (180V instead of 190V)
    async def fake_refuse(command_id: int, payload: bytes):
        protection_cluster.report_received(CMD_OPTIONS_3, SAMPLE_E7_REPORT)
        return foundation.Status.SUCCESS

    with mock.patch.object(threshold_cluster, "command", side_effect=fake_refuse):
        res = await protection_cluster.write_attributes(
            {"under_voltage_threshold": 190}
        )
    assert res[0][0].status == foundation.Status.FAILURE


async def test_read_attributes_triggers_background_refresh(breaker_device):
    """Test that read_attributes refreshes stale settings in the background."""
    ep = breaker_device.endpoints[1]
    threshold_cluster = ep.tuya_external_switch_type
    protection_cluster = ep.tongou_protection

    async def fake_query(command_id: int, payload: bytes):
        if command_id == CMD_OPTIONS_3:
            return threshold_cluster.client_commands[CMD_OPTIONS_3].schema(
                data=SAMPLE_E7_REPORT
            )
        return threshold_cluster.client_commands[CMD_OPTIONS_2].schema(
            data=SAMPLE_E6_REPORT
        )

    with mock.patch.object(
        threshold_cluster, "command", side_effect=fake_query
    ) as cmd_mock:
        await protection_cluster.read_attributes(["over_current_threshold"])
        assert protection_cluster._refresh_task is not None
        await protection_cluster._refresh_task

        assert cmd_mock.call_count == 2
        assert protection_cluster.get("over_current_threshold") == 32
        assert protection_cluster.get("temperature_threshold") == 80

        # Subsequent read within REFRESH_COOLDOWN should not spawn another refresh
        await protection_cluster.read_attributes(["over_current_threshold"])
        assert cmd_mock.call_count == 2


async def test_timeout_and_missing_setting_errors(breaker_device, monkeypatch):
    """Test timeout handling in _exchange/_refresh and missing setting in _write."""
    monkeypatch.setattr(breaker_mod, "REPORT_TIMEOUT", 0.01)
    ep = breaker_device.endpoints[1]
    threshold_cluster = ep.tuya_external_switch_type
    protection_cluster = ep.tongou_protection

    async def silent_command(command_id: int, payload: bytes):
        return foundation.Status.SUCCESS

    with mock.patch.object(threshold_cluster, "command", side_effect=silent_command):
        res = await protection_cluster.write_attributes({"over_current_threshold": 30})
        assert res[0][0].status == foundation.Status.FAILURE

        await protection_cluster._refresh()
        assert protection_cluster._last_refresh == float("-inf")

    async def empty_report_command(command_id: int, payload: bytes):
        protection_cluster.report_received(command_id, b"")
        return foundation.Status.SUCCESS

    with mock.patch.object(
        threshold_cluster, "command", side_effect=empty_report_command
    ):
        res = await protection_cluster.write_attributes({"over_current_threshold": 30})
        assert res[0][0].status == foundation.Status.FAILURE
