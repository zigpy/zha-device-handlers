"""Tests for the Salus iT600 heating devices."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import RelativeHumidity

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks import salus
from zhaquirks.salus import kl08rf, sq610rf

zhaquirks.setup()

KL08RF_IEEE = t.EUI64([8, 7, 6, 5, 4, 3, 2, 1])
KL08RF_NWK = t.NWK(0xB15F)
FC00 = salus.SalusIt600Cluster.cluster_id

# 2026-10-15 20:44:26 local time.
CLOCK = 0x3263F7AA
CLOCK_BYTES = CLOCK.to_bytes(4, "little")


def _kl08rf(zigpy_device_from_v2_quirk, **kwargs):
    """Return a quirked KL08RF wiring centre (manufacturer only, no model)."""
    return zigpy_device_from_v2_quirk(
        manufacturer=salus.COMPUTIME,
        model=None,
        endpoint_ids=[kl08rf.WIRING_CENTRE_ENDPOINT],
        cluster_ids={
            kl08rf.WIRING_CENTRE_ENDPOINT: {
                FC00: ClusterType.Server,
                Basic.cluster_id: ClusterType.Server,
                Ota.cluster_id: ClusterType.Client,
            }
        },
        **kwargs,
    )


def _sq610rf(zigpy_device_from_v2_quirk, **kwargs):
    """Return a quirked SQ610RFNH thermostat."""
    return zigpy_device_from_v2_quirk(
        manufacturer=salus.SALUS,
        model="SQ610RFNH",
        endpoint_ids=[sq610rf.THERMOSTAT_ENDPOINT],
        cluster_ids={
            sq610rf.THERMOSTAT_ENDPOINT: {
                FC00: ClusterType.Server,
                Basic.cluster_id: ClusterType.Server,
                Ota.cluster_id: ClusterType.Client,
            }
        },
        **kwargs,
    )


def _endpoint(device):
    """Return the device's only application endpoint."""
    return next(ep for ep_id, ep in device.endpoints.items() if ep_id != 0)


def _header(command_id, direction=foundation.Direction.Server_to_Client):
    """Build the ZCL header of an incoming iT600 command."""
    hdr = foundation.ZCLHeader.cluster(
        tsn=0x42, command_id=command_id, manufacturer=salus.COMPUTIME_MANUFACTURER_CODE
    )
    return hdr.replace(
        frame_control=hdr.frame_control.replace(
            direction=direction, disable_default_response=True
        )
    )


def _receive(cluster, command_id, payload, **kwargs):
    """Feed an iT600 command from the device to the cluster."""
    cluster.handle_cluster_request(
        _header(command_id, **kwargs), salus.It600Payload(data=t.Bytes(payload))
    )


def _sent(reply_mock):
    """Return [(command_id, payload)] for each iT600 frame sent to the device."""
    sent = []
    for call in reply_mock.call_args_list:
        hdr, payload = foundation.ZCLHeader.deserialize(call.kwargs["data"])
        assert hdr.frame_control.direction == foundation.Direction.Server_to_Client
        assert hdr.frame_control.disable_default_response
        assert hdr.manufacturer == salus.COMPUTIME_MANUFACTURER_CODE
        sent.append((hdr.command_id, bytes(payload)))
    return sent


def _status_record(**overrides):
    """Build a 77-byte status record (0x71), heating at 21 °C by default."""
    record = bytearray(77)
    record[0:4] = bytes([sq610rf.RECORD_STATUS, 0x10, 0x0D, 0x02])
    record[4:6] = bytes.fromhex("2290")  # temperature 22.90 °C
    record[9:11] = bytes.fromhex("2100")  # active setpoint 21.00 °C
    record[15] = sq610rf.SYSTEM_MODE_HEAT
    record[17] = 1  # heating
    record[18:22] = b"0000"
    record[23] = 1  # keys locked
    record[24] = 0x53  # 53 %
    record[49] = 4  # battery level 4 of 5
    for offset, value in overrides.items():
        record[int(offset[1:])] = value
    return bytes(record)


@pytest.fixture
def clock():
    """Freeze the clock sent in sync responses."""
    with mock.patch.object(salus, "local_seconds_since_2000", return_value=CLOCK):
        yield


def test_payload_bytes():
    """Test the raw payload extraction for every shape zigpy hands us."""
    assert salus.payload_bytes(salus.It600Payload(data=t.Bytes(b"\x01"))) == b"\x01"
    assert salus.payload_bytes(b"\x03\x04") == b"\x03\x04"
    assert salus.payload_bytes(bytearray(b"\x05")) == b"\x05"
    assert salus.payload_bytes(None) == b""


def test_local_seconds_since_2000():
    """Test that the clock is counted from 2000-01-01."""
    # 2026 lies between 26 and 27 years after 2000.
    assert 26 * 365 * 86400 < salus.local_seconds_since_2000() < 27 * 366 * 86400


def test_sync_response_body(clock):
    """Test the sync response layout zigbee2mqtt sends."""
    assert salus.sync_response_body(0x20) == (
        b"\x20\x00" + CLOCK_BYTES + bytes.fromhex("020d00ffffffff3100")
    )


@pytest.mark.parametrize(
    ("data", "value"),
    [
        (bytes.fromhex("2290"), 2290),
        (bytes.fromhex("0500"), 500),
        (bytes.fromhex("b500"), -500),
        (bytes.fromhex("53"), 53),
    ],
)
def test_bcd_to_int(data, value):
    """Test BCD decoding, including the negative encoding."""
    assert sq610rf.bcd_to_int(data) == value


@pytest.mark.parametrize(
    ("setpoint", "byte"),
    [(500, 0x2A), (1500, 0x3E), (2100, 0x4A), (2150, 0x4B), (2160, 0x4B), (3500, 0x66)],
)
def test_setpoint_to_byte(setpoint, byte):
    """Test the B34 setpoint encoding, rounded to 0.5 °C."""
    assert sq610rf.setpoint_to_byte(setpoint) == byte


def test_kl08rf_filter(zigpy_device_from_v2_quirk, zigpy_device_mock):
    """Test that only a device with endpoint 8 is taken for a wiring centre."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    assert isinstance(
        device.endpoints[kl08rf.WIRING_CENTRE_ENDPOINT].salus_it600,
        kl08rf.SalusKL08Cluster,
    )

    other = zigpy_device_mock()
    other.add_endpoint(1)
    assert not kl08rf.is_kl08rf(other)


@pytest.mark.parametrize(
    ("request_payload", "device_number"),
    [
        (b"\xff\x00\xff\x22\x03\x18\x20", 1),  # first contact
        (b"", 1),
        (b"\x01\x00\xff\x22\x03\x18\x20", 1),  # already number 1
        (b"\x20\x00\xff\x22\x03\x18\x20", 0x20),  # keeps the number it got
    ],
)
async def test_kl08rf_sync(
    zigpy_device_from_v2_quirk, clock, request_payload, device_number
):
    """Test that the wiring centre's sync request assigns number 1."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WIRING_CENTRE_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(
            cluster,
            0x10,
            request_payload,
            direction=foundation.Direction.Client_to_Server,
        )
        await wait_for_zigpy_tasks()

    assert _sent(reply) == [(0x81, salus.sync_response_body(device_number))]


@pytest.mark.parametrize("command_id", [0x37, 0x1A, 0x33, 0xA9])
async def test_kl08rf_other_commands_not_answered(
    zigpy_device_from_v2_quirk, command_id
):
    """Test that the wiring centre's other commands get no reply."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WIRING_CENTRE_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(
            cluster,
            command_id,
            b"\x11\x00\x00",
            direction=foundation.Direction.Client_to_Server,
        )
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []


async def test_unknown_command_passed_to_zigpy(zigpy_device_from_v2_quirk):
    """Test that a command outside the iT600 table falls through to zigpy."""
    device = _kl08rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[kl08rf.WIRING_CENTRE_ENDPOINT].salus_it600

    with mock.patch.object(
        salus.LocalDataCluster, "handle_cluster_request"
    ) as super_handler:
        _receive(cluster, 0x99, b"")

    assert super_handler.call_count == 1


@pytest.mark.parametrize("device_factory", [_kl08rf, _sq610rf])
def test_basic_identity(zigpy_device_from_v2_quirk, device_factory):
    """Test that the device is told it talks to a Salus gateway."""
    device = device_factory(zigpy_device_from_v2_quirk)
    basic = _endpoint(device).basic
    assert isinstance(basic, salus.SalusIt600Basic)

    model = basic.handle_read_attribute_model()
    manufacturer = basic.handle_read_attribute_manufacturer()
    assert model == "SAU2AG1"
    assert manufacturer == "Computime"
    # zigpy 2.x serializes the reply value directly, so it must be a zigpy type.
    assert isinstance(model, t.CharacterString)
    assert isinstance(manufacturer, t.CharacterString)


@pytest.mark.parametrize("device_factory", [_kl08rf, _sq610rf])
async def test_ota_query_next_image(zigpy_device_from_v2_quirk, device_factory):
    """Test that Query Next Image gets a Default Response, Invalid Field."""
    device = device_factory(zigpy_device_from_v2_quirk)
    cluster = _endpoint(device).out_clusters[Ota.cluster_id]
    assert isinstance(cluster, salus.SalusIt600Ota)

    hdr = foundation.ZCLHeader.cluster(
        tsn=0x11, command_id=Ota.ServerCommandDefs.query_next_image.id
    )
    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        cluster.handle_cluster_request(hdr, [])
        await wait_for_zigpy_tasks()

    rhdr, data = foundation.ZCLHeader.deserialize(reply.mock_calls[0].kwargs["data"])
    assert rhdr.tsn == 0x11
    assert rhdr.command_id == foundation.GeneralCommand.Default_Response
    assert rhdr.frame_control.direction == foundation.Direction.Server_to_Client
    assert not rhdr.frame_control.disable_default_response
    rsp, _ = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema.deserialize(data)
    assert rsp.command_id == Ota.ServerCommandDefs.query_next_image.id
    assert rsp.status == foundation.Status.INVALID_FIELD


async def test_ota_other_command_passed_to_zigpy(zigpy_device_from_v2_quirk):
    """Test that other OTA commands reach zigpy's OTA handling."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].out_clusters[Ota.cluster_id]
    hdr = foundation.ZCLHeader.cluster(
        tsn=0x12, command_id=Ota.ServerCommandDefs.image_block.id
    )

    with mock.patch.object(Ota, "handle_cluster_request") as super_handler:
        cluster.handle_cluster_request(hdr, [])

    assert super_handler.call_count == 1


def test_sq610rf_clusters(zigpy_device_from_v2_quirk):
    """Test that the thermostat gets the clusters behind its entities."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    assert isinstance(endpoint.salus_it600, sq610rf.SalusSQ610Cluster)
    assert isinstance(endpoint.thermostat, sq610rf.SalusThermostat)
    assert isinstance(endpoint.power, sq610rf.SalusPowerConfiguration)
    assert isinstance(endpoint.humidity, sq610rf.SalusRelativeHumidity)
    assert (
        endpoint.thermostat.get(Thermostat.AttributeDefs.ctrl_sequence_of_oper.id)
        == Thermostat.ControlSequenceOfOperation.Heating_Only
    )
    assert endpoint.thermostat.get("min_heat_setpoint_limit") == 500
    assert endpoint.thermostat.get("max_heat_setpoint_limit") == 3500


@pytest.mark.parametrize(
    ("request_payload", "device_number"),
    [
        (b"\xff\x42\xff\x50\x00\x00\x00", 0x20),  # first contact
        (b"\x2b\x42\x01\x3f\x00\x00\x00", 0x2B),  # keeps the number it got
    ],
)
async def test_sq610rf_sync(
    zigpy_device_from_v2_quirk, clock, request_payload, device_number
):
    """Test that the thermostat's sync request is answered and remembered."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(cluster, 0x10, request_payload)
        await wait_for_zigpy_tasks()

    assert _sent(reply) == [(0x81, salus.sync_response_body(device_number))]
    assert cluster.get("device_number") == device_number


async def test_sq610rf_status_record(zigpy_device_from_v2_quirk):
    """Test that a status record fills the thermostat's entities."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    with mock.patch.object(endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(endpoint.salus_it600, 0x31, _status_record())
        await wait_for_zigpy_tasks()

    # No device number is known yet, so no sync response is sent.
    assert reply.mock_calls == []
    thermostat = endpoint.thermostat
    assert thermostat.get("local_temperature") == 2290
    assert thermostat.get("occupied_heating_setpoint") == 2100
    assert thermostat.get("system_mode") == Thermostat.SystemMode.Heat
    assert thermostat.get("running_state") == Thermostat.RunningState.Heat_State_On
    assert endpoint.salus_it600.get("child_lock") == t.Bool.true
    assert endpoint.humidity.get("measured_value") == 5300
    assert endpoint.power.get("battery_percentage_remaining") == 150


async def test_sq610rf_status_record_idle_unlocked(zigpy_device_from_v2_quirk):
    """Test idle, unlocked and an unknown battery level."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    _receive(endpoint.salus_it600, 0x31, _status_record(b17=0, b23=0, b49=0xFF))

    assert endpoint.thermostat.get("running_state") == Thermostat.RunningState.Idle
    assert endpoint.salus_it600.get("child_lock") == t.Bool.false
    assert endpoint.power.get("battery_percentage_remaining") is None


async def test_sq610rf_status_record_placeholder_temperature(
    zigpy_device_from_v2_quirk,
):
    """Test that the 12.34 °C placeholder is not taken for a reading."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    _receive(endpoint.salus_it600, 0x31, _status_record(b4=0x12, b5=0x34))

    assert endpoint.thermostat.get("local_temperature") is None
    assert endpoint.thermostat.get("occupied_heating_setpoint") == 2100


async def test_sq610rf_status_record_standby(zigpy_device_from_v2_quirk):
    """Test that standby is off and keeps the last setpoint."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    _receive(endpoint.salus_it600, 0x31, _status_record())
    # In standby the active setpoint bytes hold the frost setpoint, 15.00 °C.
    _receive(endpoint.salus_it600, 0x31, _status_record(b3=7, b9=0x15, b10=0x00))

    assert endpoint.thermostat.get("system_mode") == Thermostat.SystemMode.Off
    assert endpoint.thermostat.get("occupied_heating_setpoint") == 2100


async def test_sq610rf_status_record_cooling(zigpy_device_from_v2_quirk):
    """Test that in cool mode the active setpoint is the cooling setpoint."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    _receive(endpoint.salus_it600, 0x31, _status_record(b15=3, b9=0x30))

    assert endpoint.thermostat.get("system_mode") == Thermostat.SystemMode.Cool
    assert endpoint.thermostat.get("occupied_cooling_setpoint") == 3000
    assert endpoint.thermostat.get("occupied_heating_setpoint") is None


async def test_sq610rf_settings_record(zigpy_device_from_v2_quirk):
    """Test that the settings record sets the setpoint limits."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]
    record = bytearray(77)
    record[0] = sq610rf.RECORD_SETTINGS
    record[22:26] = bytes.fromhex("25001500")  # max 25.00 °C, min 15.00 °C

    _receive(endpoint.salus_it600, 0x31, bytes(record))

    assert endpoint.thermostat.get("max_heat_setpoint_limit") == 2500
    assert endpoint.thermostat.get("min_heat_setpoint_limit") == 1500


@pytest.mark.parametrize(
    "record",
    [b"", b"\x71\x10\x0d", b"\x72\x07", b"\x75" + b"\xff" * 76],
)
async def test_sq610rf_other_records_ignored(zigpy_device_from_v2_quirk, record):
    """Test that short and unparsed records change nothing."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]
    listener = ClusterListener(endpoint.thermostat)

    _receive(endpoint.salus_it600, 0x31, record)

    assert listener.attribute_updates == []


async def test_sq610rf_resends_sync_once_a_day(zigpy_device_from_v2_quirk, clock):
    """Test that records keep the clock right without flooding the device."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600
    cluster.update_attribute(cluster.AttributeDefs.device_number.id, 0x2B)
    sync = (0x81, salus.sync_response_body(0x2B))

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        # The first record after a restart syncs, the next one does not.
        _receive(cluster, 0x31, _status_record())
        _receive(cluster, 0x31, _status_record())
        await wait_for_zigpy_tasks()
        assert _sent(reply) == [sync]

        cluster._last_sync -= salus.IT600_SYNC_INTERVAL
        _receive(cluster, 0x31, _status_record())
        await wait_for_zigpy_tasks()

    assert _sent(reply) == [sync, sync]


async def test_sq610rf_zone_report(zigpy_device_from_v2_quirk):
    """Test the zone report the thermostat sends when we are its wiring centre."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]

    with mock.patch.object(endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(
            endpoint.salus_it600,
            0x12,
            bytes.fromhex("0201010600ff0000000000ffd009540bf401"),
        )
        _receive(endpoint.salus_it600, 0x12, b"\x02\x01\x01")
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []
    assert endpoint.thermostat.get("local_temperature") == 2512
    assert endpoint.thermostat.get("occupied_heating_setpoint") == 2900
    assert (
        endpoint.thermostat.get("running_state")
        == Thermostat.RunningState.Heat_State_On
    )

    _receive(
        endpoint.salus_it600,
        0x12,
        bytes.fromhex("0201000600ff0000000000ffd009540bf401"),
    )
    assert endpoint.thermostat.get("running_state") == Thermostat.RunningState.Idle


async def test_sq610rf_zone_pairing_without_wiring_centre(zigpy_device_from_v2_quirk):
    """Test that without a wiring centre we pair the thermostat ourselves."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(cluster, 0x16, b"\x02")
        _receive(cluster, 0x16, b"")
        _receive(cluster, 0x18, bytes.fromhex("01060000ff0000"))
        _receive(cluster, 0x14, b"\x00\x06")
        _receive(cluster, 0x14, b"\x00")
        await wait_for_zigpy_tasks()

    assert _sent(reply) == [
        (0x86, b"\x01\x00\x00"),
        (0x86, b"\x01\x00\x00"),
        (0x88, bytes.fromhex("00ff0000000000")),
        (0x84, b"\x00\x06\x00"),
    ]


async def test_sq610rf_zone_pairing_with_wiring_centre(
    zigpy_device_from_v2_quirk, zigpy_device_mock, ieee_mock
):
    """Test that a KL08RF on the network is preferred over the coordinator."""
    # The coordinator is never a wiring centre.
    zigpy_device_mock(ieee=t.EUI64([0] * 8), nwk=t.NWK(0x0000)).add_endpoint(
        kl08rf.WIRING_CENTRE_ENDPOINT
    )
    _kl08rf(zigpy_device_from_v2_quirk, ieee=KL08RF_IEEE, nwk=KL08RF_NWK)
    device = _sq610rf(zigpy_device_from_v2_quirk, ieee=ieee_mock)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(cluster, 0x16, b"\x01")
        # Only wiring centre number 1 exists.
        _receive(cluster, 0x16, b"\x02")
        await wait_for_zigpy_tasks()

    assert _sent(reply) == [
        (0x86, b"\x01" + KL08RF_NWK.to_bytes(2, "little")),
        (0x86, b"\x00\xff\xff"),
    ]


@pytest.mark.parametrize("command_id", [0x11, 0x25, 0x33])
async def test_sq610rf_other_commands_not_answered(
    zigpy_device_from_v2_quirk, command_id
):
    """Test that echoes and announcements get no reply."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        _receive(cluster, command_id, b"\x01B34\x4a")
        await wait_for_zigpy_tasks()

    assert reply.mock_calls == []


@pytest.mark.parametrize(
    ("attribute", "value", "frames", "cached"),
    [
        ("occupied_heating_setpoint", 2160, [b"B34\x4b"], 2150),
        ("occupied_cooling_setpoint", 3000, [b"B33\x5c"], 3000),
        ("system_mode", Thermostat.SystemMode.Off, [b"B20\x07"], 0),
        ("system_mode", Thermostat.SystemMode.Heat, [b"B20\x02", b"B48\x04"], 4),
        ("system_mode", Thermostat.SystemMode.Cool, [b"B20\x02", b"B48\x03"], 3),
    ],
)
async def test_sq610rf_thermostat_write(
    zigpy_device_from_v2_quirk, attribute, value, frames, cached
):
    """Test that thermostat writes go out as B-commands."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    thermostat = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].thermostat

    with mock.patch.object(thermostat.endpoint, "reply", mock.AsyncMock()) as reply:
        result = await thermostat.write_attributes({attribute: value})

    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    assert _sent(reply) == [
        (0x32, bytes([handle]) + frame) for handle, frame in enumerate(frames, 1)
    ]
    assert thermostat.get(attribute) == cached


@pytest.mark.parametrize(("value", "arg"), [(True, 0x41), (False, 0x42)])
async def test_sq610rf_child_lock_write(zigpy_device_from_v2_quirk, value, arg):
    """Test that the child lock is written with B03."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        await cluster.write_attributes({"child_lock": value})

    assert _sent(reply) == [(0x32, b"\x01B03\x00\x00" + bytes([arg]) + bytes(10))]
    assert cluster.get("child_lock") == value


async def test_sq610rf_b_command_handle_wraps(zigpy_device_from_v2_quirk):
    """Test that B-command handles stay within 1-127."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT].salus_it600
    cluster._handle = 0x7E

    with mock.patch.object(cluster.endpoint, "reply", mock.AsyncMock()) as reply:
        for _ in range(3):
            await cluster.it600_write(b"B74", 0, 0, 0, 0, 0)

    assert [payload[0] for _, payload in _sent(reply)] == [0x7F, 0x01, 0x02]


def test_power_and_humidity_are_local(zigpy_device_from_v2_quirk):
    """Test that battery and humidity never go over the air."""
    device = _sq610rf(zigpy_device_from_v2_quirk)
    endpoint = device.endpoints[sq610rf.THERMOSTAT_ENDPOINT]
    assert endpoint.power.cluster_id == PowerConfiguration.cluster_id
    assert endpoint.humidity.cluster_id == RelativeHumidity.cluster_id
    assert isinstance(endpoint.power, salus.LocalDataCluster)
    assert isinstance(endpoint.humidity, salus.LocalDataCluster)
