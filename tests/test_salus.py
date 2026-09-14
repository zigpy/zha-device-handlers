"""Tests for Salus/Computime heating devices."""

import datetime
import time
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Ota

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.salus import kl08rf, sq610rf

zhaquirks.setup()

KL08RF_IEEE = t.EUI64([8, 7, 6, 5, 4, 3, 2, 1])
KL08RF_NWK = t.NWK(0xB15F)


def _kl08rf(zigpy_device_from_v2_quirk, **kwargs):
    """Return a quirked KL08RF wiring centre (manufacturer only, no model)."""
    return zigpy_device_from_v2_quirk(
        manufacturer=kl08rf.COMPUTIME_MFR,
        model=None,
        endpoint_ids=[kl08rf.WC_EP],
        cluster_ids={
            kl08rf.WC_EP: {
                kl08rf.SalusKL08FC00Cluster.cluster_id: ClusterType.Server,
                Basic.cluster_id: ClusterType.Server,
                Ota.cluster_id: ClusterType.Client,
            }
        },
        **kwargs,
    )


def _sq610rf(zigpy_device_from_v2_quirk, **kwargs):
    """Return a quirked SQ610RFNH thermostat."""
    return zigpy_device_from_v2_quirk(
        manufacturer=sq610rf.SALUS,
        model=sq610rf.SALUS_MODEL,
        endpoint_ids=[sq610rf.THERMOSTAT_EP],
        cluster_ids={
            sq610rf.THERMOSTAT_EP: {
                sq610rf.SalusFC00Cluster.cluster_id: ClusterType.Server,
                sq610rf.SalusFC09Cluster.cluster_id: ClusterType.Server,
                Basic.cluster_id: ClusterType.Server,
                Ota.cluster_id: ClusterType.Client,
            }
        },
        **kwargs,
    )


def _mfr_header(command_id, direction=foundation.Direction.Server_to_Client, tsn=0x42):
    """Build the ZCL header of an incoming Salus manufacturer command."""
    hdr = foundation.ZCLHeader.cluster(
        tsn=tsn, command_id=command_id, manufacturer=sq610rf.COMPUTIME
    )
    return hdr.replace(
        frame_control=hdr.frame_control.replace(
            direction=direction, disable_default_response=True
        )
    )


def _sent_fc00(reply_mock):
    """Return [(command_id, body)] for each fc00 frame passed to endpoint.reply."""
    sent = []
    for call in reply_mock.call_args_list:
        hdr, body = foundation.ZCLHeader.deserialize(call.kwargs["data"])
        # Salus replies are always server->client with default response disabled.
        assert hdr.frame_control.direction == foundation.Direction.Server_to_Client
        assert hdr.frame_control.disable_default_response
        assert hdr.manufacturer == sq610rf.COMPUTIME
        sent.append((hdr.command_id, bytes(body)))
    return sent


@pytest.mark.parametrize("module", [kl08rf, sq610rf])
def test_payload_bytes(module):
    """Test the raw fc00 payload extraction for every shape zigpy hands us."""
    # Deserialized _RawPayload struct (the normal path).
    assert module.payload_bytes(module._RawPayload(data=t.Bytes(b"\x01\x02"))) == (
        b"\x01\x02"
    )
    # Raw bytes, when the command id is missing from the table zigpy picked.
    assert module.payload_bytes(b"\x03\x04") == b"\x03\x04"
    assert module.payload_bytes(bytearray(b"\x05")) == b"\x05"
    # Nothing usable.
    assert module.payload_bytes(None) == b""
    assert module.payload_bytes([]) == b""


def test_kl08rf_commission_reply_body():
    """Test wiring-centre slot assignment vs. echo in the fc00 0x81 body."""
    # First contact: no payload, or byte 0 == 0xff -> we assign the slot.
    for req in (b"", b"\xff\x00\xfe"):
        body = kl08rf.commission_reply_body(req)
        assert body[0] == kl08rf.FC00_0X81_WC_SLOT
        assert body[1:3] == b"\x00\xfe"
        assert body[3:] == kl08rf.FC00_0X81_TAIL

    # Established session: the device echoes its own slot, we confirm it.
    assert kl08rf.commission_reply_body(b"\x03\x00\xfe")[0] == 0x03


def test_kl08rf_is_kl08rf(zigpy_device_from_v2_quirk, zigpy_device_mock):
    """Test the endpoint-8 signature filter behind the manufacturer-only match."""
    # A device with endpoint 8 is quirked as a wiring centre...
    device = _kl08rf(zigpy_device_from_v2_quirk)
    assert isinstance(
        device.endpoints[kl08rf.WC_EP].salus_fc00, kl08rf.SalusKL08FC00Cluster
    )
    assert kl08rf._is_kl08rf(device)

    # ...a "Computime" device without one is not.
    other = zigpy_device_mock()
    other.add_endpoint(1)
    assert not kl08rf._is_kl08rf(other)


async def test_kl08rf_fc00_commission_handshake(zigpy_device_from_v2_quirk):
    """Test that fc00 0x10 is answered with the 0x81 slot assignment."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WC_EP].salus_fc00

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(
            _mfr_header(0x10, direction=foundation.Direction.Client_to_Server),
            kl08rf._RawPayload(data=t.Bytes(b"\xff\x00\xfe")),
        )
        await wait_for_zigpy_tasks()

    assert _sent_fc00(reply) == [(0x81, kl08rf.commission_reply_body(b"\xff\x00\xfe"))]


async def test_kl08rf_fc00_commission_handshake_disabled(zigpy_device_from_v2_quirk):
    """Test that the 0x10 auto-reply honours the module toggle."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WC_EP].salus_fc00

    with (
        mock.patch.object(kl08rf, "ENABLE_FC00_COMMISSION_REPLY", False),
        mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply,
    ):
        cluster.handle_cluster_request(
            _mfr_header(0x10, direction=foundation.Direction.Client_to_Server),
            kl08rf._RawPayload(data=t.Bytes(b"\xff\x00\xfe")),
        )
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []


@pytest.mark.parametrize("command_id", [0x37, 0xA9, 0x25])
async def test_kl08rf_fc00_accepted_silently(zigpy_device_from_v2_quirk, command_id):
    """Test that keep-alive, distress and unknown fc00 commands get no reply."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WC_EP].salus_fc00

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(
            _mfr_header(command_id, direction=foundation.Direction.Client_to_Server),
            kl08rf._RawPayload(data=t.Bytes(b"\x11\x00\x00")),
        )
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []


async def test_kl08rf_ota_query_next_image(zigpy_device_from_v2_quirk):
    """Test that the OTA probe is answered like a CO10RF: Default Response 0x85."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WC_EP].out_clusters[Ota.cluster_id]
    assert isinstance(cluster, kl08rf.SalusKL08Ota)

    hdr = foundation.ZCLHeader.cluster(
        tsn=0x11, command_id=Ota.ServerCommandDefs.query_next_image.id
    )
    hdr = hdr.replace(
        frame_control=hdr.frame_control.replace(
            direction=foundation.Direction.Client_to_Server
        )
    )

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(hdr, [])
        await wait_for_zigpy_tasks()

    rhdr, data = foundation.ZCLHeader.deserialize(reply.mock_calls[0].kwargs["data"])
    assert rhdr.command_id == foundation.GeneralCommand.Default_Response
    assert rhdr.frame_control.direction == foundation.Direction.Server_to_Client
    # The CO10RF leaves disable-default-response clear; match it exactly.
    assert not rhdr.frame_control.disable_default_response
    rsp, _ = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema.deserialize(data)
    assert rsp.command_id == Ota.ServerCommandDefs.query_next_image.id
    assert rsp.status == foundation.Status.INVALID_FIELD


async def test_kl08rf_ota_other_command_passed_through(zigpy_device_from_v2_quirk):
    """Test that non-query_next_image OTA commands fall through to zigpy."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WC_EP].out_clusters[Ota.cluster_id]

    hdr = foundation.ZCLHeader.cluster(
        tsn=0x12, command_id=Ota.ServerCommandDefs.image_block.id
    )
    hdr = hdr.replace(
        frame_control=hdr.frame_control.replace(
            direction=foundation.Direction.Client_to_Server
        )
    )

    with mock.patch.object(Ota, "handle_cluster_request") as super_handler:
        cluster.handle_cluster_request(hdr, [])

    assert super_handler.call_count == 1


def test_kl08rf_basic_model_identity(zigpy_device_from_v2_quirk):
    """Test the coordinator-identity answer the device gates commissioning on."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WC_EP].basic
    assert isinstance(cluster, kl08rf.SalusKL08Basic)

    model = cluster.handle_read_attribute_model()
    assert model == kl08rf.SALUS_COORD_MODEL
    # Must be a zigpy type: zigpy 2.x serializes the reply value directly.
    assert isinstance(model, t.CharacterString)


def test_sq610rf_basic_model_identity(zigpy_device_from_v2_quirk):
    """Test the thermostat's coordinator-identity answer."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].basic
    assert isinstance(cluster, sq610rf.SalusBasic)

    model = cluster.handle_read_attribute_model()
    assert model == sq610rf.SALUS_COORD_MODEL
    assert isinstance(model, t.CharacterString)


async def test_sq610rf_report_updates_attributes(zigpy_device_from_v2_quirk):
    """Test that the fc00 0x12 operational report populates the sensors."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    listener = ClusterListener(cluster)
    # Suppress the auto clock sync so only the report is exercised here.
    cluster._last_time_sync = time.monotonic()

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(
            _mfr_header(0x12),
            sq610rf._RawPayload(
                data=t.Bytes(bytes.fromhex("0201010600ff0000000000ffd009540bf401"))
            ),
        )
        await wait_for_zigpy_tasks()

    # The native wiring centre only APS-acks a 0x12; we must not reply either.
    assert reply.mock_calls == []
    attrs = sq610rf.SalusFC00Cluster.AttributeDefs
    assert cluster.get(attrs.local_temperature.id) == 2512
    assert cluster.get(attrs.occupied_heating_setpoint.id) == 2900
    assert cluster.get(attrs.running_state.id) == t.Bool.true
    assert listener.attribute_updates == [
        (attrs.local_temperature.id, 2512),
        (attrs.occupied_heating_setpoint.id, 2900),
        (attrs.running_state.id, t.Bool.true),
    ]


async def test_sq610rf_report_too_short_ignored(zigpy_device_from_v2_quirk):
    """Test that a truncated 0x12 report is dropped instead of mis-parsed."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    listener = ClusterListener(cluster)
    cluster._last_time_sync = time.monotonic()

    cluster.handle_cluster_request(
        _mfr_header(0x12), sq610rf._RawPayload(data=t.Bytes(b"\x02\x01\x01"))
    )
    await wait_for_zigpy_tasks()

    assert listener.attribute_updates == []


@pytest.mark.parametrize(
    ("body", "expected_secs", "expected_dst"),
    [
        # 0x31de9758 = 2026-07-06 16:42:00 local, DST on.
        ("5897de3103010d", 0x31DE9758, t.Bool.true),
        ("5897de3102000d", 0x31DE9758, t.Bool.false),
    ],
)
async def test_sq610rf_time_announce(
    zigpy_device_from_v2_quirk, body, expected_secs, expected_dst
):
    """Test that the fc00 0x11 date/time broadcast is decoded and cached."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    cluster._last_time_sync = time.monotonic()

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(
            _mfr_header(0x11), sq610rf._RawPayload(data=t.Bytes(bytes.fromhex(body)))
        )
        await wait_for_zigpy_tasks()

    # The native gateway never answers the broadcast, so neither do we.
    assert reply.mock_calls == []
    attrs = sq610rf.SalusFC00Cluster.AttributeDefs
    assert cluster.get(attrs.device_time.id) == expected_secs
    assert cluster.get(attrs.dst_active.id) == expected_dst


async def test_sq610rf_time_announce_too_short_ignored(zigpy_device_from_v2_quirk):
    """Test that a truncated 0x11 broadcast is dropped."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    listener = ClusterListener(cluster)
    cluster._last_time_sync = time.monotonic()

    cluster.handle_cluster_request(
        _mfr_header(0x11), sq610rf._RawPayload(data=t.Bytes(b"\x58\x97"))
    )
    await wait_for_zigpy_tasks()

    assert listener.attribute_updates == []


async def test_sq610rf_update_check_accepted(zigpy_device_from_v2_quirk):
    """Test that the proprietary fc00 0x25 update check is accepted silently."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    cluster._last_time_sync = time.monotonic()

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(
            _mfr_header(0x25), sq610rf._RawPayload(data=t.Bytes(b"\x00"))
        )
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []


async def test_sq610rf_unknown_command_passed_through(zigpy_device_from_v2_quirk):
    """Test that an fc00 command we have no reply for falls through to zigpy."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    cluster._last_time_sync = time.monotonic()

    assert cluster._fc00_reply_for(_mfr_header(0x99), None) is None

    with mock.patch.object(
        sq610rf.CustomCluster, "handle_cluster_request"
    ) as super_handler:
        cluster.handle_cluster_request(
            _mfr_header(0x99), sq610rf._RawPayload(data=t.Bytes(b""))
        )

    assert super_handler.call_count == 1


async def test_sq610rf_commission_handshake(zigpy_device_from_v2_quirk):
    """Test the fc00 0x10 -> 0x81 handshake: assign, then echo the token."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    cluster._last_time_sync = time.monotonic()

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        # First contact: the device sends 0xff, we pick the token and state 0xa5.
        cluster.handle_cluster_request(
            _mfr_header(0x10), sq610rf._RawPayload(data=t.Bytes(b"\xff\x00\xfe"))
        )
        # Later round: echo the device's rolling token and advance to state 0xa8.
        cluster.handle_cluster_request(
            _mfr_header(0x10), sq610rf._RawPayload(data=t.Bytes(b"\x2c\x00\xfe"))
        )
        await wait_for_zigpy_tasks()

    assert _sent_fc00(reply) == [
        (
            0x81,
            bytes(
                [sq610rf.FC00_0X81_DEFAULT_TOKEN, 0x00, sq610rf.FC00_0X81_STATE_FIRST]
            )
            + sq610rf.FC00_0X81_TAIL,
        ),
        (
            0x81,
            bytes([0x2C, 0x00, sq610rf.FC00_0X81_STATE_NEXT]) + sq610rf.FC00_0X81_TAIL,
        ),
    ]


async def test_sq610rf_zone_bind_without_wiring_centre(zigpy_device_from_v2_quirk):
    """Test that with no wiring centre present we point the device at ourselves."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    cluster._last_time_sync = time.monotonic()

    assert cluster._find_wiring_centre() is None

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        # "Which wiring centre?" -> control box 01 at the coordinator (0x0000).
        cluster.handle_cluster_request(
            _mfr_header(0x16), sq610rf._RawPayload(data=t.Bytes(b"\x01"))
        )
        # Zone bind, then bind confirm for zone 6.
        cluster.handle_cluster_request(
            _mfr_header(0x18),
            sq610rf._RawPayload(data=t.Bytes(bytes.fromhex("01060000ff0000"))),
        )
        cluster.handle_cluster_request(
            _mfr_header(0x14), sq610rf._RawPayload(data=t.Bytes(b"\x00\x06"))
        )
        await wait_for_zigpy_tasks()

    assert _sent_fc00(reply) == [
        (0x86, b"\x01\x00\x00"),
        (0x88, sq610rf.FC00_0X88_REPLY),
        (0x84, b"\x00\x06\x00"),
    ]


async def test_sq610rf_zone_bind_defaults_on_short_requests(
    zigpy_device_from_v2_quirk,
):
    """Test the fallbacks used when a 0x16/0x14 request carries no usable body."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00

    assert cluster._fc00_reply_for(_mfr_header(0x16), None) == (0x86, b"\x01\x00\x00")
    assert cluster._fc00_reply_for(_mfr_header(0x14), None) == (0x84, b"\x00\x06\x00")


async def test_sq610rf_finds_real_wiring_centre(
    zigpy_device_from_v2_quirk, zigpy_device_mock, ieee_mock
):
    """Test that a KL08RF on the network is preferred over emulating one."""
    # The coordinator (short address 0x0000) is never a wiring centre.
    zigpy_device_mock(ieee=t.EUI64([0] * 8), nwk=t.NWK(0x0000)).add_endpoint(
        kl08rf.WC_EP
    )
    _kl08rf(zigpy_device_from_v2_quirk, ieee=KL08RF_IEEE, nwk=KL08RF_NWK)
    device = _sq610rf(zigpy_device_from_v2_quirk, ieee=ieee_mock)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    cluster._last_time_sync = time.monotonic()

    assert cluster._find_wiring_centre() == KL08RF_NWK

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(
            _mfr_header(0x16), sq610rf._RawPayload(data=t.Bytes(b"\x01"))
        )
        await wait_for_zigpy_tasks()

    # 0x86 = <control box><wiring centre short address, little endian>.
    assert _sent_fc00(reply) == [(0x86, b"\x01" + KL08RF_NWK.to_bytes(2, "little"))]


def test_sq610rf_find_wiring_centre_without_application(zigpy_device_from_v2_quirk):
    """Test that an unavailable device list falls back to emulating a centre."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00

    # An application object that exposes no device list at all.
    with mock.patch.object(device, "_application", mock.Mock(spec=[])):
        assert cluster._find_wiring_centre() is None


async def test_sq610rf_forced_wiring_centre_box(zigpy_device_from_v2_quirk):
    """Test the FORCE_WC_BOX experiment override of the requested control box."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00

    with mock.patch.object(sq610rf, "FORCE_WC_BOX", 0x04):
        assert cluster._fc00_reply_for(
            _mfr_header(0x16), sq610rf._RawPayload(data=t.Bytes(b"\x01"))
        ) == (0x86, b"\x04\x00\x00")


async def test_sq610rf_set_clock_button(zigpy_device_from_v2_quirk):
    """Test that the synthetic set-clock command emits a real fc00 0x11."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    command_id = sq610rf.SalusFC00Cluster.ServerCommandDefs.set_clock_to_ha_time.id

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        rsp = await cluster.command(command_id)

    assert rsp.status == foundation.Status.SUCCESS
    assert rsp.command_id == command_id

    sent = _sent_fc00(reply)
    assert len(sent) == 1
    sent_command_id, body = sent[0]
    # <u32 LE seconds since 2000-01-01, local time><DST b4><DST b5>0x0d
    assert sent_command_id == 0x11
    assert len(body) == 7
    assert body[4:] in (b"\x03\x01\x0d", b"\x02\x00\x0d")
    sent_time = sq610rf.SalusFC00Cluster._ZCL_EPOCH + datetime.timedelta(
        seconds=int.from_bytes(body[0:4], "little")
    )
    lt = time.localtime()
    now_local = datetime.datetime(
        lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec
    )
    assert abs((sent_time - now_local).total_seconds()) < 60


async def test_sq610rf_other_commands_not_intercepted(zigpy_device_from_v2_quirk):
    """Test that commands other than the set-clock button reach zigpy."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00

    with mock.patch.object(
        sq610rf.CustomCluster, "command", mock.AsyncMock()
    ) as super_command:
        await cluster.command(0x31)

    assert super_command.call_count == 1


async def test_sq610rf_auto_clock_sync_is_throttled(zigpy_device_from_v2_quirk):
    """Test that the clock rides device traffic but syncs once per interval."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00
    report = sq610rf._RawPayload(
        data=t.Bytes(bytes.fromhex("0201010600ff0000000000ffd009540bf401"))
    )

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        # First contact syncs...
        cluster.handle_cluster_request(_mfr_header(0x12), report)
        # ...a second frame right after does not.
        cluster.handle_cluster_request(_mfr_header(0x12), report)
        await wait_for_zigpy_tasks()

        assert [command_id for command_id, _ in _sent_fc00(reply)] == [0x11]

        # Once the interval has elapsed, the next frame syncs again.
        cluster._last_time_sync -= sq610rf.TIME_SYNC_INTERVAL_S
        cluster.handle_cluster_request(_mfr_header(0x12), report)
        await wait_for_zigpy_tasks()

    assert [command_id for command_id, _ in _sent_fc00(reply)] == [0x11, 0x11]


async def test_sq610rf_auto_clock_sync_disabled(zigpy_device_from_v2_quirk):
    """Test that the auto clock sync honours the module toggle."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].salus_fc00

    with (
        mock.patch.object(sq610rf, "ENABLE_TIME_AUTO_SYNC", False),
        mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply,
    ):
        cluster.handle_cluster_request(
            _mfr_header(0x12),
            sq610rf._RawPayload(
                data=t.Bytes(bytes.fromhex("0201010600ff0000000000ffd009540bf401"))
            ),
        )
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []
    assert cluster._last_time_sync is None


async def test_sq610rf_ota_query_next_image(zigpy_device_from_v2_quirk):
    """Test that the OTA probe is answered like a CO10RF: Default Response 0x85."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].out_clusters[Ota.cluster_id]
    assert isinstance(cluster, sq610rf.SalusOta)

    hdr = foundation.ZCLHeader.cluster(
        tsn=0x21, command_id=Ota.ServerCommandDefs.query_next_image.id
    )
    hdr = hdr.replace(
        frame_control=hdr.frame_control.replace(
            direction=foundation.Direction.Client_to_Server
        )
    )

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(hdr, [])
        await wait_for_zigpy_tasks()

    rhdr, data = foundation.ZCLHeader.deserialize(reply.mock_calls[0].kwargs["data"])
    assert rhdr.command_id == foundation.GeneralCommand.Default_Response
    assert not rhdr.frame_control.disable_default_response
    rsp, _ = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema.deserialize(data)
    assert rsp.command_id == Ota.ServerCommandDefs.query_next_image.id
    assert rsp.status == foundation.Status.INVALID_FIELD


async def test_sq610rf_ota_other_command_passed_through(zigpy_device_from_v2_quirk):
    """Test that non-query_next_image OTA commands fall through to zigpy."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_EP].out_clusters[Ota.cluster_id]

    hdr = foundation.ZCLHeader.cluster(
        tsn=0x22, command_id=Ota.ServerCommandDefs.image_block.id
    )
    hdr = hdr.replace(
        frame_control=hdr.frame_control.replace(
            direction=foundation.Direction.Client_to_Server
        )
    )

    with mock.patch.object(Ota, "handle_cluster_request") as super_handler:
        cluster.handle_cluster_request(hdr, [])

    assert super_handler.call_count == 1
