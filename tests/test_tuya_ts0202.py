"""Tests for the Tuya TS0202 (``_TZ3000_bsvqrxru``) PIR motion quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.tuya.ts0202 import (
    ALARM_BITS,
    DEFAULT_MOTION_TIMEOUT_S,
    MAX_MOTION_TIMEOUT_S,
    MIN_MOTION_TIMEOUT_S,
    MOTION_TIMEOUT_ATTR_ID,
    TS0202MotionCluster,
)

zhaquirks.setup()


ZONE_STATUS_ATTR_ID = IasZone.AttributeDefs.zone_status.id
ZONE_TYPE_ATTR_ID = IasZone.AttributeDefs.zone_type.id
ZONE_STATUS_CHANGE_COMMAND_ID = IasZone.ClientCommandDefs.status_change_notification.id


def _ts0202_cluster(zigpy_device_from_v2_quirk):
    """Build one quirked TS0202 IAS Zone cluster ready for exercise.

    ``MotionWithReset.__init__`` captures the current event loop, so this has
    to run inside a running loop (i.e. an async test or async fixture).
    """
    device = zigpy_device_from_v2_quirk(
        manufacturer="_TZ3000_bsvqrxru",
        model="TS0202",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    assert isinstance(cluster, TS0202MotionCluster)
    return cluster


@pytest.fixture
async def ts0202_cluster(zigpy_device_from_v2_quirk):
    """Return the quirked TS0202 IAS Zone cluster on endpoint 1."""
    return _ts0202_cluster(zigpy_device_from_v2_quirk)


async def test_quirk_replaces_ias_zone_with_ts0202_cluster(ts0202_cluster):
    """Confirm the quirk swaps in the TS0202 IAS Zone cluster."""
    assert isinstance(ts0202_cluster, TS0202MotionCluster)
    assert ts0202_cluster.cluster_id == IasZone.cluster_id


async def test_zone_type_is_pinned_to_motion_sensor(ts0202_cluster):
    """Zone type must be forced to Motion_Sensor so HA picks device_class=motion."""
    assert (
        ts0202_cluster._CONSTANT_ATTRIBUTES[ZONE_TYPE_ATTR_ID]
        == IasZone.ZoneType.Motion_Sensor
    )


async def test_motion_timeout_attribute_is_declared(ts0202_cluster):
    """The writable motion_timeout attribute must be declared on the cluster."""
    attr = TS0202MotionCluster.AttributeDefs.motion_timeout
    assert attr.id == MOTION_TIMEOUT_ATTR_ID
    assert attr.name == "motion_timeout"
    # In the reserved range so we can't collide with real IAS Zone attrs.
    assert attr.id >= 0xFFF0
    assert not attr.is_manufacturer_specific


async def test_cluster_primes_synthetic_motion_timeout(ts0202_cluster):
    """motion_timeout must read as DEFAULT_MOTION_TIMEOUT_S on a fresh cluster."""
    assert ts0202_cluster.reset_s == DEFAULT_MOTION_TIMEOUT_S
    assert (
        ts0202_cluster._attr_cache[MOTION_TIMEOUT_ATTR_ID] == DEFAULT_MOTION_TIMEOUT_S
    )


async def test_attribute_report_with_alarm_1_schedules_auto_clear(ts0202_cluster):
    """An ``Alarm_1`` zone_status report must start the auto-clear timer."""
    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        timer = mock.MagicMock()
        mock_loop.call_later.return_value = timer
        ts0202_cluster._update_attribute(
            ZONE_STATUS_ATTR_ID, IasZone.ZoneStatus.Alarm_1
        )

    mock_loop.call_later.assert_called_once_with(
        DEFAULT_MOTION_TIMEOUT_S, ts0202_cluster._turn_off
    )


async def test_attribute_report_with_alarm_2_schedules_auto_clear(ts0202_cluster):
    """``Alarm_2`` is emitted by some TS0202 firmwares and must also reset."""
    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        mock_loop.call_later.return_value = mock.MagicMock()
        ts0202_cluster._update_attribute(
            ZONE_STATUS_ATTR_ID, IasZone.ZoneStatus.Alarm_2
        )

    mock_loop.call_later.assert_called_once_with(
        DEFAULT_MOTION_TIMEOUT_S, ts0202_cluster._turn_off
    )


async def test_attribute_report_with_zero_status_does_not_schedule(ts0202_cluster):
    """A cleared zone_status report must not (re)arm the auto-clear timer."""
    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        ts0202_cluster._update_attribute(ZONE_STATUS_ATTR_ID, 0)

    mock_loop.call_later.assert_not_called()


async def test_new_motion_cancels_pending_timer(ts0202_cluster):
    """A second motion report must cancel the previous timer before scheduling a new one."""
    old_timer = mock.MagicMock()
    ts0202_cluster._timer_handle = old_timer
    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        mock_loop.call_later.return_value = mock.MagicMock()
        ts0202_cluster._update_attribute(
            ZONE_STATUS_ATTR_ID, IasZone.ZoneStatus.Alarm_1
        )

    old_timer.cancel.assert_called_once()
    mock_loop.call_later.assert_called_once()


async def test_unrelated_attribute_update_is_not_intercepted(ts0202_cluster):
    """Updates for other attributes must pass through without arming the timer."""
    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        ts0202_cluster._update_attribute(ZONE_TYPE_ATTR_ID, 0xABCD)

    mock_loop.call_later.assert_not_called()
    assert ts0202_cluster._attr_cache[ZONE_TYPE_ATTR_ID] == 0xABCD


async def test_command_path_still_schedules_auto_clear(ts0202_cluster):
    """The inherited command path (``zone_status_change_notification``) must reset too.

    Firmware revisions of the TS0202 differ: some push ``Alarm_1`` as a
    ``zone_status_change_notification`` IAS command and never as an attribute
    report. The base ``MotionWithReset.handle_cluster_request`` already handles
    that; this test locks in the behavior for this fingerprint so the
    attribute-report override never regresses the command path.
    """
    hdr = foundation.ZCLHeader.cluster(
        tsn=0x01,
        command_id=ZONE_STATUS_CHANGE_COMMAND_ID,
    )
    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        mock_loop.call_later.return_value = mock.MagicMock()
        ts0202_cluster.handle_cluster_request(
            hdr, [IasZone.ZoneStatus.Alarm_1, 0, 0, 0]
        )

    mock_loop.call_later.assert_called_once_with(
        DEFAULT_MOTION_TIMEOUT_S, ts0202_cluster._turn_off
    )


async def test_turn_off_clears_timer_handle(ts0202_cluster):
    """After the auto-clear fires, the timer handle must be released.

    ``MotionWithReset._turn_off`` emits a synthetic cluster command listener
    event that ZHA picks up to clear its binary_sensor - we don't need to
    re-test that here, but we do need to make sure the timer bookkeeping is
    reset so the *next* motion event can schedule a fresh timer.
    """
    ts0202_cluster._timer_handle = mock.MagicMock()
    ts0202_cluster._turn_off()

    assert ts0202_cluster._timer_handle is None


async def test_write_motion_timeout_by_name_updates_cache_without_zigbee_io(
    ts0202_cluster,
):
    """Writing the synthetic attr by name must stay local (no ``request`` call)."""
    endpoint_request = mock.AsyncMock()
    ts0202_cluster._endpoint.request = endpoint_request

    status = await ts0202_cluster.write_attributes({"motion_timeout": 120})

    assert ts0202_cluster.reset_s == 120
    assert ts0202_cluster._attr_cache[MOTION_TIMEOUT_ATTR_ID] == 120
    endpoint_request.assert_not_awaited()
    assert status[0][0].status == foundation.Status.SUCCESS


async def test_write_motion_timeout_by_id_is_accepted(ts0202_cluster):
    """Writing by raw attribute id (e.g. from ZHA internals) must also be routed local."""
    endpoint_request = mock.AsyncMock()
    ts0202_cluster._endpoint.request = endpoint_request

    await ts0202_cluster.write_attributes({MOTION_TIMEOUT_ATTR_ID: 45})

    assert ts0202_cluster.reset_s == 45
    assert ts0202_cluster._attr_cache[MOTION_TIMEOUT_ATTR_ID] == 45
    endpoint_request.assert_not_awaited()


async def test_write_motion_timeout_clamps_above_maximum(ts0202_cluster):
    """Writing a value above ``MAX_MOTION_TIMEOUT_S`` is clamped, not rejected."""
    await ts0202_cluster.write_attributes({"motion_timeout": 99999})

    assert ts0202_cluster.reset_s == MAX_MOTION_TIMEOUT_S
    assert ts0202_cluster._attr_cache[MOTION_TIMEOUT_ATTR_ID] == MAX_MOTION_TIMEOUT_S


async def test_write_motion_timeout_clamps_below_minimum(ts0202_cluster):
    """Writing a value below ``MIN_MOTION_TIMEOUT_S`` is clamped, not rejected."""
    await ts0202_cluster.write_attributes({"motion_timeout": 0})

    assert ts0202_cluster.reset_s == MIN_MOTION_TIMEOUT_S
    assert ts0202_cluster._attr_cache[MOTION_TIMEOUT_ATTR_ID] == MIN_MOTION_TIMEOUT_S


async def test_updated_motion_timeout_is_used_on_next_event(ts0202_cluster):
    """After a write the auto-clear timer must use the new value, not the old default."""
    await ts0202_cluster.write_attributes({"motion_timeout": 30})

    with mock.patch.object(ts0202_cluster, "_loop") as mock_loop:
        mock_loop.call_later.return_value = mock.MagicMock()
        ts0202_cluster._update_attribute(
            ZONE_STATUS_ATTR_ID, IasZone.ZoneStatus.Alarm_1
        )

    mock_loop.call_later.assert_called_once_with(30, ts0202_cluster._turn_off)


def _captured_forwarded_attrs(mocked_super: mock.AsyncMock) -> dict:
    """Pull the ``attributes`` dict out of the patched ``super().write_attributes`` call."""
    mocked_super.assert_awaited_once()
    call = mocked_super.await_args
    if "attributes" in call.kwargs:
        return call.kwargs["attributes"]
    # The mock isn't bound so ``self`` doesn't show up in args; ``attributes`` is args[0].
    return call.args[0]


async def test_non_synthetic_writes_are_forwarded_to_device(ts0202_cluster):
    """Writes to *real* IAS Zone attrs must still be forwarded to the device."""
    with mock.patch.object(
        IasZone, "write_attributes", new=mock.AsyncMock(return_value=[[]])
    ) as mocked_super:
        await ts0202_cluster.write_attributes({IasZone.AttributeDefs.zone_id.id: 0x01})

    forwarded = _captured_forwarded_attrs(mocked_super)
    assert forwarded == {IasZone.AttributeDefs.zone_id.id: 0x01}


async def test_mixed_write_splits_local_and_remote(ts0202_cluster):
    """A write that mixes synthetic + real attrs must apply the synthetic locally and forward the rest."""
    with mock.patch.object(
        IasZone, "write_attributes", new=mock.AsyncMock(return_value=[[]])
    ) as mocked_super:
        await ts0202_cluster.write_attributes(
            {
                "motion_timeout": 75,
                IasZone.AttributeDefs.zone_id.id: 0x02,
            }
        )

    assert ts0202_cluster.reset_s == 75
    assert ts0202_cluster._attr_cache[MOTION_TIMEOUT_ATTR_ID] == 75
    forwarded = _captured_forwarded_attrs(mocked_super)
    assert "motion_timeout" not in forwarded
    assert MOTION_TIMEOUT_ATTR_ID not in forwarded
    assert forwarded == {IasZone.AttributeDefs.zone_id.id: 0x02}


async def test_is_motion_timeout_key_classifier(ts0202_cluster):
    """The key classifier must recognise the synthetic attr via name, id, and descriptor."""
    cls = TS0202MotionCluster

    assert cls._is_motion_timeout_key("motion_timeout") is True
    assert cls._is_motion_timeout_key(MOTION_TIMEOUT_ATTR_ID) is True
    assert cls._is_motion_timeout_key(cls.AttributeDefs.motion_timeout) is True
    assert cls._is_motion_timeout_key("zone_status") is False
    assert cls._is_motion_timeout_key(ZONE_STATUS_ATTR_ID) is False
    assert cls._is_motion_timeout_key((1, 2)) is False


async def test_alarm_bits_mask_matches_known_firmware_values():
    """``ALARM_BITS`` must cover the bitmask the quirk inspects at runtime."""
    assert (IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Alarm_2) == ALARM_BITS


async def test_quirk_removes_onoff_client_cluster(zigpy_device_from_v2_quirk):
    """The vestigial OnOff client cluster must be stripped by the quirk.

    Stock ZHA materialises that out-cluster as a permanently-off
    ``binary_sensor.<name>_opening`` entity which only serves to confuse users.
    """
    device = zigpy_device_from_v2_quirk(
        manufacturer="_TZ3000_bsvqrxru",
        model="TS0202",
        cluster_ids={
            1: {
                IasZone.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Client,
            }
        },
    )
    assert OnOff.cluster_id not in device.endpoints[1].out_clusters


async def test_quirk_swaps_power_cluster_for_aaa_variant(
    zigpy_device_from_v2_quirk,
):
    """The stock PowerConfiguration cluster must be replaced by the 2xAAA variant."""
    from zigpy.zcl.clusters.general import PowerConfiguration

    from zhaquirks.tuya import TuyaPowerConfigurationCluster2AAA

    device = zigpy_device_from_v2_quirk(
        manufacturer="_TZ3000_bsvqrxru",
        model="TS0202",
        cluster_ids={
            1: {
                IasZone.cluster_id: ClusterType.Server,
                PowerConfiguration.cluster_id: ClusterType.Server,
            }
        },
    )
    power_cluster = device.endpoints[1].in_clusters[PowerConfiguration.cluster_id]
    assert isinstance(power_cluster, TuyaPowerConfigurationCluster2AAA)
