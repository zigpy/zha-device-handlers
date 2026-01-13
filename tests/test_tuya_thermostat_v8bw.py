"""Tests for Tuya TS0601 thermostat v9bw (_TZE204_wc2w9t1s)."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final
from unittest.mock import AsyncMock, patch

import pytest
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks

# Import quirk module so TuyaQuirkBuilder(...).add_to_registry() executes.
from zhaquirks.tuya import tuya_thermostat_v9bw  # noqa: F401

# Ensure all quirks are registered.
zhaquirks.setup()

MANUFACTURER: Final[str] = "_TZE204_wc2w9t1s"
MODEL: Final[str] = "TS0601"
TUYA_CLUSTER_ID: Final[int] = 0xEF00


@dataclass(frozen=True, slots=True)
class DpCase:
    """One datapoint test case."""

    dp: int
    name: str
    # Build a Tuya DP payload for this DP (seq is injected by runner).
    build_payload: Callable[[int], bytes]
    # Cluster to observe: "thermostat", "tuya", or "power"
    target: str
    # Attribute name expected to be updated
    attr_name: str
    # Expected value
    expected: object


def _tuya_dp_report(seq: int, dp: int, dp_type: int, data: bytes) -> bytes:
    """Build a Tuya 'DP report' ZCL payload matching zhaquirks format.

    Format based on actual Tuya messages from test_tuya.py:
    - 0x09: command prefix
    - seq: sequence number
    - 0x01: status (always 0x01 for reports)
    - 0x03: unknown (always 0x03)
    - total_len: length of remaining data
    - dp: datapoint ID
    - dp_type: datapoint type
    - data_len: length of data (big endian, 2 bytes)
    - data: actual payload
    """
    dlen = len(data)
    # Total length = dp(1) + type(1) + len(2) + data
    total_len = 1 + 1 + 2 + dlen

    return (
        bytes(
            [
                0x09,  # Command prefix
                seq & 0xFF,  # Sequence number
                0x01,  # Status (0x01 for reports)
                0x03,  # Unknown constant
                total_len & 0xFF,  # Total length of DP data
                dp & 0xFF,  # DP ID
                dp_type & 0xFF,  # Data type
                (dlen >> 8) & 0xFF,  # Data length high byte
                dlen & 0xFF,  # Data length low byte
            ]
        )
        + data
    )


def _dp_bool(seq: int, dp: int, value: bool) -> bytes:
    """Build bool DP report."""
    return _tuya_dp_report(seq, dp, 0x01, bytes([0x01 if value else 0x00]))


def _dp_u32(seq: int, dp: int, value_u32: int) -> bytes:
    """Build uint32 DP report."""
    return _tuya_dp_report(
        seq,
        dp,
        0x02,
        bytes(
            [
                (value_u32 >> 24) & 0xFF,
                (value_u32 >> 16) & 0xFF,
                (value_u32 >> 8) & 0xFF,
                value_u32 & 0xFF,
            ]
        ),
    )

def _dp_raw(seq: int, dp: int, raw_data: bytes) -> bytes:
    """Build raw bytes DP report (LVBytes type)."""
    return _tuya_dp_report(seq, dp, 0x00, raw_data)


def _feed_tuya_payload(tuya_cluster, payload: bytes) -> None:
    """Deserialize and handle Tuya payload."""
    hdr, args = tuya_cluster.deserialize(payload)
    tuya_cluster.handle_message(hdr, args)


def _cases() -> Iterable[DpCase]:
    """All DP cases to validate for this quirk."""

    # DP 1: system_mode heat/off (bool -> Thermostat.system_mode)
    yield DpCase(
        dp=1,
        name="DP1 system_mode heat",
        build_payload=lambda seq: _dp_bool(seq, 1, True),
        target="thermostat",
        attr_name="system_mode",
        expected=Thermostat.SystemMode.Heat,
    )

    yield DpCase(
        dp=1,
        name="DP1 system_mode off",
        build_payload=lambda seq: _dp_bool(seq, 1, False),
        target="thermostat",
        attr_name="system_mode",
        expected=Thermostat.SystemMode.Off,
    )

    # DP 24: local temp (device sends 0.1°C, converter *10 -> 0.01°C)
    yield DpCase(
        dp=24,
        name="DP24 local_temperature 24.0C",
        build_payload=lambda seq: _dp_u32(seq, 24, 240),  # 24.0°C in 0.1°C units
        target="thermostat",
        attr_name="local_temperature",
        expected=2400,  # 240 * 10 = 2400 (0.01°C units)
    )

    # DP 16: setpoint (device sends 0.1°C, converter *10 -> 0.01°C)
    yield DpCase(
        dp=16,
        name="DP16 setpoint 25.0C",
        build_payload=lambda seq: _dp_u32(seq, 16, 250),  # 25.0°C in 0.1°C units
        target="thermostat",
        attr_name="occupied_heating_setpoint",
        expected=2500,  # 250 * 10 = 2500 (0.01°C units)
    )

    # DP 36: running_state (open/close)
    yield DpCase(
        dp=36,
        name="DP36 running_state heat",
        build_payload=lambda seq: _dp_bool(seq, 36, True),
        target="thermostat",
        attr_name="running_state",
        expected=Thermostat.RunningState.Heat_State_On,
    )

    yield DpCase(
        dp=36,
        name="DP36 running_state idle",
        build_payload=lambda seq: _dp_bool(seq, 36, False),
        target="thermostat",
        attr_name="running_state",
        expected=Thermostat.RunningState.Idle,
    )

    # DP 10: frost (bool) -> attribute on Tuya cluster
    yield DpCase(
        dp=10,
        name="DP10 frost on",
        build_payload=lambda seq: _dp_bool(seq, 10, True),
        target="tuya",
        attr_name="frost",
        expected=True,
    )

    yield DpCase(
        dp=10,
        name="DP10 frost off",
        build_payload=lambda seq: _dp_bool(seq, 10, False),
        target="tuya",
        attr_name="frost",
        expected=False,
    )

    # DP 18: min_temperature_limit
    # IMPORTANT: multiplier is applied in Home Assistant, not in the cluster!
    # Cluster stores raw value 70, HA displays 70 * 0.1 = 7.0°C
    yield DpCase(
        dp=18,
        name="DP18 min_temperature_limit 7.0C",
        build_payload=lambda seq: _dp_u32(seq, 18, 70),  # 7.0°C in 0.1°C units
        target="tuya",
        attr_name="min_temperature_limit",
        expected=70,  # Raw value BEFORE multiplier is applied!
    )

    # DP 40: child lock
    yield DpCase(
        dp=40,
        name="DP40 child_lock on",
        build_payload=lambda seq: _dp_bool(seq, 40, True),
        target="tuya",
        attr_name="child_lock",
        expected=True,
    )

    # DP 107: battery
    yield DpCase(
        dp=107,
        name="DP107 battery 85%",
        build_payload=lambda seq: _dp_u32(seq, 107, 85),
        target="power",
        attr_name="battery_percentage_remaining",
        expected=170,  # 85 * 2 = 170 (battery in 0.5% units)
    )

    # DP 65: schedule_monday (raw bytes converted to hex string)
    # Example: 06:30 @ 20.0°C, 08:00 @ 22.0°C (2 segments, 8 bytes total)
    # Segment 1: 06:30 = 390 minutes = 0x0186, 20.0°C = 200 (0.1°C) = 0x00C8
    # Segment 2: 08:00 = 480 minutes = 0x01E0, 22.0°C = 220 (0.1°C) = 0x00DC
    yield DpCase(
        dp=65,
        name="DP65 schedule_monday",
        build_payload=lambda seq: _dp_raw(
            seq, 65, bytes([0x01, 0x86, 0x00, 0xC8, 0x01, 0xE0, 0x00, 0xDC])
        ),
        target="tuya",
        attr_name="schedule_monday",
        expected="018600c801e000dc",  # Hex string representation
    )


@pytest.mark.parametrize("case", list(_cases()), ids=lambda c: c.name)
async def test_wc2w9t1s_datapoints_apply(
    zigpy_device_from_v2_quirk,
    case: DpCase,
):
    """Validate DP->attribute mappings for the v9bw quirk."""
    device = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep1 = device.endpoints[1]

    tuya = ep1.in_clusters[TUYA_CLUSTER_ID]
    thermostat = ep1.in_clusters[Thermostat.cluster_id]
    from zigpy.zcl.clusters.general import PowerConfiguration

    power = ep1.in_clusters[PowerConfiguration.cluster_id]

    # Mock the async reply method to avoid RuntimeError
    with patch.object(tuya, "reply", new_callable=AsyncMock):
        # Select target cluster
        if case.target == "thermostat":
            target_cluster = thermostat
        elif case.target == "power":
            target_cluster = power
        else:
            target_cluster = tuya

        listener = ClusterListener(target_cluster)

        # Generate and send payload
        payload = case.build_payload(0x30 + case.dp)
        _feed_tuya_payload(tuya, payload)

        # ClusterListener.attribute_updates contains tuples (attr_id, value)
        # Need to get attr_id from attribute name
        attr_def = target_cluster.attributes_by_name.get(case.attr_name)
        assert attr_def is not None, (
            f"Attribute {case.attr_name} not found in {target_cluster}"
        )

        expected_attr_id = attr_def.id

        # Find updates by attr_id
        matching_updates = [
            evt
            for evt in listener.attribute_updates
            if len(evt) >= 2 and evt[0] == expected_attr_id
        ]

        # Verify that update occurred
        assert matching_updates, (
            f"{case.name}: no updates for {case.attr_name} (id={expected_attr_id}), "
            f"got {listener.attribute_updates}"
        )

        # Verify the value of the last update
        actual_value = matching_updates[-1][1]
        assert actual_value == case.expected, (
            f"{case.name}: expected {case.attr_name}={case.expected}, "
            f"got {actual_value}"
        )
