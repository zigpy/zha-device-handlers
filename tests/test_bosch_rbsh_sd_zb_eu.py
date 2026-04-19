"""Tests for the Bosch RBSH-SD-ZB-EU / BSD-2 smoke detector quirk."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import WriteAttributesStatusRecord

import zhaquirks
from zhaquirks.bosch.rbsh_sd_zb_eu import (
    ALARM_TIMEOUT_SECONDS,
    BOSCH_MANUFACTURER_CODE,
    BROADCAST_BURGLAR_ALARM_ATTR_ID,
    BROADCAST_DST_ENDPOINT,
    BROADCAST_SMOKE_ALARM_ATTR_ID,
    HA_PROFILE_ID,
    INTER_BROADCAST_DELAY_S,
    MANUAL_BURGLAR_ALARM_ATTR_ID,
    MANUAL_SMOKE_ALARM_ATTR_ID,
    BoschAlarmMode,
    BoschIasZoneCluster,
)

zhaquirks.setup()


def _bsd2_cluster(zigpy_device_from_v2_quirk):
    """Build one quirked Bosch IAS Zone cluster ready for exercise."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Bosch",
        model="RBSH-SD-ZB-EU",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    assert isinstance(cluster, BoschIasZoneCluster)
    return cluster


@pytest.fixture
def bosch_bsd2_cluster(zigpy_device_from_v2_quirk):
    """Return the quirked Bosch IAS Zone cluster on endpoint 1."""
    return _bsd2_cluster(zigpy_device_from_v2_quirk)


@pytest.fixture
def _mocked_app_broadcast(bosch_bsd2_cluster):
    """Patch ``application.get_sequence`` and ``application.broadcast`` on a cluster's device."""
    app = bosch_bsd2_cluster.endpoint.device.application
    app.get_sequence = mock.MagicMock(return_value=0x42)
    app.broadcast = mock.AsyncMock()
    return app


async def test_quirk_replaces_ias_zone_with_bosch_cluster(bosch_bsd2_cluster):
    """Confirm the quirk swaps in the Bosch IAS Zone cluster."""
    assert isinstance(bosch_bsd2_cluster, BoschIasZoneCluster)
    assert bosch_bsd2_cluster.cluster_id == IasZone.cluster_id


async def test_cluster_primes_synthetic_attribute_cache(bosch_bsd2_cluster):
    """All four synthetic switches must start in the off state on a fresh cluster."""
    assert bosch_bsd2_cluster._attr_cache[MANUAL_SMOKE_ALARM_ATTR_ID] == 0
    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 0
    assert bosch_bsd2_cluster._attr_cache[BROADCAST_SMOKE_ALARM_ATTR_ID] == 0
    assert bosch_bsd2_cluster._attr_cache[BROADCAST_BURGLAR_ALARM_ATTR_ID] == 0


async def test_control_alarm_command_is_manufacturer_specific(bosch_bsd2_cluster):
    """The control_alarm command is Bosch-specific and must carry the Bosch code."""
    cmd = BoschIasZoneCluster.ServerCommandDefs.control_alarm
    assert cmd.id == 0x80
    assert cmd.is_manufacturer_specific is True
    # Schema verifies the wire payload shape: ENUM8 mode + UINT8 timeout.
    field_names = [field.name for field in cmd.schema.fields]
    field_types = [field.type for field in cmd.schema.fields]
    assert field_names == ["alarm_mode", "alarm_timeout"]
    assert field_types[0] is BoschAlarmMode
    assert field_types[1].__name__ == "uint8_t"


async def test_synthetic_attributes_carry_bosch_manufacturer_code(bosch_bsd2_cluster):
    """All four synthetic attributes advertise the Bosch manufacturer code."""
    for attr in (
        BoschIasZoneCluster.AttributeDefs.manual_smoke_alarm,
        BoschIasZoneCluster.AttributeDefs.manual_burglar_alarm,
        BoschIasZoneCluster.AttributeDefs.broadcast_smoke_alarm,
        BoschIasZoneCluster.AttributeDefs.broadcast_burglar_alarm,
    ):
        assert attr.manufacturer_code == BOSCH_MANUFACTURER_CODE


async def test_synthetic_attributes_use_expected_ids(bosch_bsd2_cluster):
    """The synthetic attribute ids are stable so the on-wire frame layout is predictable."""
    assert BoschIasZoneCluster.AttributeDefs.manual_smoke_alarm.id == 0xF000
    assert BoschIasZoneCluster.AttributeDefs.manual_burglar_alarm.id == 0xF001
    assert BoschIasZoneCluster.AttributeDefs.broadcast_smoke_alarm.id == 0xF002
    assert BoschIasZoneCluster.AttributeDefs.broadcast_burglar_alarm.id == 0xF003


@pytest.mark.parametrize(
    ("attr_name", "expected_mode", "attr_id"),
    [
        ("manual_burglar_alarm", BoschAlarmMode.Burglar, MANUAL_BURGLAR_ALARM_ATTR_ID),
        ("manual_smoke_alarm", BoschAlarmMode.Smoke, MANUAL_SMOKE_ALARM_ATTR_ID),
    ],
)
async def test_write_true_sends_arm_control_alarm_and_caches_on(
    bosch_bsd2_cluster, attr_name, expected_mode, attr_id
):
    """Writing True to a manual_*_alarm attr arms the siren for 240s and updates the cache."""
    with mock.patch.object(
        bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()
    ) as mock_cmd:
        await bosch_bsd2_cluster.write_attributes({attr_name: True})

    mock_cmd.assert_awaited_once_with(expected_mode, ALARM_TIMEOUT_SECONDS)
    assert bosch_bsd2_cluster._attr_cache[attr_id] == 1


@pytest.mark.parametrize(
    ("attr_name", "expected_mode", "attr_id"),
    [
        ("manual_burglar_alarm", BoschAlarmMode.Burglar, MANUAL_BURGLAR_ALARM_ATTR_ID),
        ("manual_smoke_alarm", BoschAlarmMode.Smoke, MANUAL_SMOKE_ALARM_ATTR_ID),
    ],
)
async def test_write_false_sends_stop_control_alarm_and_caches_off(
    bosch_bsd2_cluster, attr_name, expected_mode, attr_id
):
    """Writing False to a manual_*_alarm attr stops the siren and caches off."""
    # Pretend the siren was already armed so we're genuinely toggling off.
    bosch_bsd2_cluster._update_attribute(attr_id, 1)

    with mock.patch.object(
        bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()
    ) as mock_cmd:
        await bosch_bsd2_cluster.write_attributes({attr_name: False})

    mock_cmd.assert_awaited_once_with(expected_mode, 0)
    assert bosch_bsd2_cluster._attr_cache[attr_id] == 0


async def test_arming_burglar_mirrors_smoke_off_in_cache(bosch_bsd2_cluster):
    """The BSD-2 can only run one alarm mode at a time; mirror that in the cache."""
    bosch_bsd2_cluster._update_attribute(MANUAL_SMOKE_ALARM_ATTR_ID, 1)

    with mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()):
        await bosch_bsd2_cluster.write_attributes({"manual_burglar_alarm": True})

    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 1
    assert bosch_bsd2_cluster._attr_cache[MANUAL_SMOKE_ALARM_ATTR_ID] == 0


async def test_arming_smoke_mirrors_burglar_off_in_cache(bosch_bsd2_cluster):
    """Same mirror logic, flipped: arming smoke disarms burglar in the cache."""
    bosch_bsd2_cluster._update_attribute(MANUAL_BURGLAR_ALARM_ATTR_ID, 1)

    with mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()):
        await bosch_bsd2_cluster.write_attributes({"manual_smoke_alarm": True})

    assert bosch_bsd2_cluster._attr_cache[MANUAL_SMOKE_ALARM_ATTR_ID] == 1
    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 0


async def test_disarming_does_not_touch_the_sibling_cache(bosch_bsd2_cluster):
    """Turning a siren OFF leaves the other type's cached value alone."""
    bosch_bsd2_cluster._update_attribute(MANUAL_BURGLAR_ALARM_ATTR_ID, 1)
    bosch_bsd2_cluster._update_attribute(MANUAL_SMOKE_ALARM_ATTR_ID, 1)

    with mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()):
        await bosch_bsd2_cluster.write_attributes({"manual_burglar_alarm": False})

    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 0
    # Smoke stays 1 - disarming burglar over-the-air does not stop a smoke siren.
    assert bosch_bsd2_cluster._attr_cache[MANUAL_SMOKE_ALARM_ATTR_ID] == 1


async def test_write_accepts_synthetic_attributes_by_id(bosch_bsd2_cluster):
    """Writing the attributes by raw id (not name) still triggers the translation."""
    with mock.patch.object(
        bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()
    ) as mock_cmd:
        await bosch_bsd2_cluster.write_attributes({MANUAL_BURGLAR_ALARM_ATTR_ID: True})

    mock_cmd.assert_awaited_once_with(BoschAlarmMode.Burglar, ALARM_TIMEOUT_SECONDS)
    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 1


async def test_non_synthetic_attribute_writes_are_passed_through(bosch_bsd2_cluster):
    """Writes of real IAS Zone attributes fall through to the base cluster unchanged."""

    def _mock_write(attributes, manufacturer=None):
        return [
            [
                WriteAttributesStatusRecord(foundation.Status.SUCCESS)
                for _ in attributes
            ],
            [],
        ]

    patch_low_level = mock.patch.object(
        bosch_bsd2_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=_mock_write),
    )
    patch_command = mock.patch.object(
        bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()
    )

    real_attr = IasZone.AttributeDefs.current_zone_sensitivity_level

    with patch_low_level as mock_ll, patch_command as mock_cmd:
        await bosch_bsd2_cluster.write_attributes({real_attr.name: 1})

    mock_cmd.assert_not_called()
    mock_ll.assert_awaited()


async def test_mixed_synthetic_and_real_write_splits_correctly(bosch_bsd2_cluster):
    """A single write touching both a synthetic attr and a real one must dispatch both paths."""

    def _mock_write(attributes, manufacturer=None):
        return [
            [
                WriteAttributesStatusRecord(foundation.Status.SUCCESS)
                for _ in attributes
            ],
            [],
        ]

    patch_low_level = mock.patch.object(
        bosch_bsd2_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=_mock_write),
    )
    patch_command = mock.patch.object(
        bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()
    )

    real_attr = IasZone.AttributeDefs.current_zone_sensitivity_level

    with patch_low_level as mock_ll, patch_command as mock_cmd:
        await bosch_bsd2_cluster.write_attributes(
            {
                "manual_burglar_alarm": True,
                real_attr.name: 2,
            }
        )

    mock_cmd.assert_awaited_once_with(BoschAlarmMode.Burglar, ALARM_TIMEOUT_SECONDS)
    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 1
    mock_ll.assert_awaited()
    # _write_attributes must see only the real attr, never the synthetic one.
    real_write_call = mock_ll.await_args_list[-1]
    written_attrs = real_write_call.args[0]
    written_ids = {
        (entry.attrid if hasattr(entry, "attrid") else entry) for entry in written_attrs
    }
    assert MANUAL_BURGLAR_ALARM_ATTR_ID not in written_ids


# --- broadcast path -------------------------------------------------------


@pytest.mark.parametrize(
    ("attr_name", "expected_mode", "expected_tail"),
    [
        ("broadcast_burglar_alarm", BoschAlarmMode.Burglar, "01f0"),
        ("broadcast_smoke_alarm", BoschAlarmMode.Smoke, "00f0"),
    ],
)
async def test_broadcast_true_emits_two_zigbee_broadcasts_with_arm_payload(
    bosch_bsd2_cluster, _mocked_app_broadcast, attr_name, expected_mode, expected_tail
):
    """Writing True to broadcast_*_alarm sends (mode, 240) twice to every BSD-2 on the mesh."""
    with (
        mock.patch.object(
            bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()
        ) as mock_unicast,
        mock.patch(
            "zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()
        ) as mock_sleep,
    ):
        await bosch_bsd2_cluster.write_attributes({attr_name: True})

    # Unicast control_alarm must NOT be used for broadcast writes.
    mock_unicast.assert_not_called()

    # Bosch firmware / z2m send the broadcast twice, 4 s apart, to cover
    # sleepy BSD-2s that miss the first one.
    assert _mocked_app_broadcast.broadcast.await_count == 2
    mock_sleep.assert_awaited_once_with(INTER_BROADCAST_DELAY_S)

    for call in _mocked_app_broadcast.broadcast.await_args_list:
        kwargs = call.kwargs
        assert kwargs["cluster"] == IasZone.cluster_id
        assert kwargs["profile"] == HA_PROFILE_ID
        assert kwargs["src_ep"] == 1
        assert kwargs["dst_ep"] == BROADCAST_DST_ENDPOINT
        assert kwargs["broadcast_address"] == t.BroadcastAddress.ALL_DEVICES
        # Frame tail: mode + timeout (arm payload ends with "...<mode><F0>").
        assert kwargs["data"].hex().endswith(expected_tail)


async def test_broadcast_false_emits_stop_broadcasts(
    bosch_bsd2_cluster, _mocked_app_broadcast
):
    """Writing False to broadcast_burglar_alarm sends (burglar, 0) twice (stop command)."""
    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_burglar_alarm": False})

    assert _mocked_app_broadcast.broadcast.await_count == 2
    for call in _mocked_app_broadcast.broadcast.await_args_list:
        assert call.kwargs["data"].hex().endswith("0100")


async def test_broadcast_frame_matches_herdsman_wire_format(
    bosch_bsd2_cluster, _mocked_app_broadcast
):
    """The serialized frame must byte-exactly match herdsman's boschSmokeAlarmExtend.

    Expected layout: ``15 09 12 <tsn> 80 <mode> <timeout>``
        15    = cluster-specific + manufacturer-specific + client->server + dis-def-resp
        09 12 = manufacturer code 0x1209 (little-endian)
        <tsn> = zigpy-assigned transaction sequence
        80    = control_alarm command id
        <m>   = alarm mode (0x00 smoke / 0x01 burglar)
        <t>   = alarm timeout in seconds
    """
    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_burglar_alarm": True})

    frame = _mocked_app_broadcast.broadcast.await_args_list[0].kwargs["data"]
    # TSN 0x42 comes from the fixture's get_sequence mock.
    assert frame.hex() == "1509124280" + "01" + "f0"


async def test_broadcast_on_primes_cache_locally(
    bosch_bsd2_cluster, _mocked_app_broadcast
):
    """Arming a broadcast flavour updates the initiating cluster's cache to 1."""
    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_burglar_alarm": True})

    assert bosch_bsd2_cluster._attr_cache[BROADCAST_BURGLAR_ALARM_ATTR_ID] == 1
    assert bosch_bsd2_cluster._attr_cache[BROADCAST_SMOKE_ALARM_ATTR_ID] == 0


async def test_broadcast_arm_mirrors_sibling_off(
    bosch_bsd2_cluster, _mocked_app_broadcast
):
    """Arming broadcast_smoke must disarm broadcast_burglar across the mesh."""
    bosch_bsd2_cluster._update_attribute(BROADCAST_BURGLAR_ALARM_ATTR_ID, 1)

    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_smoke_alarm": True})

    assert bosch_bsd2_cluster._attr_cache[BROADCAST_SMOKE_ALARM_ATTR_ID] == 1
    assert bosch_bsd2_cluster._attr_cache[BROADCAST_BURGLAR_ALARM_ATTR_ID] == 0


async def test_broadcast_state_syncs_across_every_live_bsd2(
    bosch_bsd2_cluster, zigpy_device_from_v2_quirk, _mocked_app_broadcast
):
    """Broadcast write on one BSD-2 mirrors cached state on every other BSD-2."""
    peer_a = _bsd2_cluster(zigpy_device_from_v2_quirk)
    peer_b = _bsd2_cluster(zigpy_device_from_v2_quirk)

    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_burglar_alarm": True})

    for cluster in (bosch_bsd2_cluster, peer_a, peer_b):
        assert cluster._attr_cache[BROADCAST_BURGLAR_ALARM_ATTR_ID] == 1
        # Cross-cluster sibling mirror: arming burglar disarms smoke everywhere.
        assert cluster._attr_cache[BROADCAST_SMOKE_ALARM_ATTR_ID] == 0


async def test_broadcast_off_syncs_across_mesh_but_leaves_sibling(
    bosch_bsd2_cluster, zigpy_device_from_v2_quirk, _mocked_app_broadcast
):
    """Disarming one broadcast flavour only clears that flavour, preserving the sibling."""
    peer = _bsd2_cluster(zigpy_device_from_v2_quirk)

    # Pretend both flavours are armed everywhere so we can prove the stop
    # only touches its own flavour's cache.
    for cluster in (bosch_bsd2_cluster, peer):
        cluster._update_attribute(BROADCAST_BURGLAR_ALARM_ATTR_ID, 1)
        cluster._update_attribute(BROADCAST_SMOKE_ALARM_ATTR_ID, 1)

    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_burglar_alarm": False})

    for cluster in (bosch_bsd2_cluster, peer):
        assert cluster._attr_cache[BROADCAST_BURGLAR_ALARM_ATTR_ID] == 0
        assert cluster._attr_cache[BROADCAST_SMOKE_ALARM_ATTR_ID] == 1


# --- _resolve_synthetic_attr_id classification table ----------------------


async def test_resolve_synthetic_attr_id_accepts_zcl_attribute_def(bosch_bsd2_cluster):
    """Passing a ``ZCLAttributeDef`` descriptor as key routes through the synthetic path.

    zigpy callers are allowed to pass an attribute descriptor (``cluster.AttributeDefs.<x>``)
    instead of the attribute's name or id, so the classifier must recognize that shape.
    """
    attr_def = BoschIasZoneCluster.AttributeDefs.broadcast_smoke_alarm
    assert (
        bosch_bsd2_cluster._resolve_synthetic_attr_id(attr_def)
        == BROADCAST_SMOKE_ALARM_ATTR_ID
    )


async def test_resolve_synthetic_attr_id_returns_none_for_non_numeric_key(
    bosch_bsd2_cluster,
):
    """Keys that aren't str/int/ZCLAttributeDef fall through to ``None`` (defensive catch).

    A tuple isn't any of those shapes and ``int((1, 2))`` raises ``TypeError``, which is
    exactly the ``except`` branch that keeps an opaque key from being mis-classified as
    a synthetic attr. It must return ``None`` so the quirk forwards the write unchanged.
    """
    assert bosch_bsd2_cluster._resolve_synthetic_attr_id((1, 2)) is None


async def test_broadcast_does_not_affect_manual_cache(
    bosch_bsd2_cluster, _mocked_app_broadcast
):
    """Broadcast writes leave the per-device manual_* cache untouched.

    Broadcast state tracks "what was last broadcast to the mesh"; manual state
    tracks "what was last unicast to this specific device". The two views are
    intentionally independent.
    """
    bosch_bsd2_cluster._update_attribute(MANUAL_BURGLAR_ALARM_ATTR_ID, 0)
    bosch_bsd2_cluster._update_attribute(MANUAL_SMOKE_ALARM_ATTR_ID, 0)

    with (
        mock.patch.object(bosch_bsd2_cluster, "control_alarm", mock.AsyncMock()),
        mock.patch("zhaquirks.bosch.rbsh_sd_zb_eu.asyncio.sleep", mock.AsyncMock()),
    ):
        await bosch_bsd2_cluster.write_attributes({"broadcast_burglar_alarm": True})

    assert bosch_bsd2_cluster._attr_cache[MANUAL_BURGLAR_ALARM_ATTR_ID] == 0
    assert bosch_bsd2_cluster._attr_cache[MANUAL_SMOKE_ALARM_ATTR_ID] == 0
