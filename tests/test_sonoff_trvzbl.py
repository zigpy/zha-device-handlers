"""Tests for SONOFF TRV-ZBL protocol and custom cluster behavior."""

import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation

import zhaquirks
from zhaquirks.sonoff import trvzbl as trv

zhaquirks.setup()


@pytest.fixture
async def trv_device(zigpy_device_from_v2_quirk):
    """Create a real quirked device and clean up its delayed polling tasks."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "TRV-ZBL",
        cluster_ids={
            1: {
                trv.SonoffThermostat.cluster_id: ClusterType.Server,
                trv.CustomSonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )
    yield device
    cluster = device.endpoints[1].in_clusters[trv.CustomSonoffCluster.cluster_id]
    tasks = [
        cluster._sonoff_trvzbl_temporary_mode_read_task,
        cluster._sonoff_trvzbl_device_work_mode_read_task,
    ]
    for task in tasks:
        if task is not None:
            task.cancel()
    await asyncio.gather(
        *(task for task in tasks if task is not None), return_exceptions=True
    )


@pytest.fixture
def private_cluster(trv_device):
    """Return the private cluster created through the device registry."""
    return trv_device.endpoints[1].in_clusters[trv.CustomSonoffCluster.cluster_id]


@pytest.fixture
def write_mock(private_cluster):
    """Mock transport responses while exercising real attribute serialization."""
    with mock.patch.object(
        private_cluster, "write_attributes_raw", new_callable=mock.AsyncMock
    ) as transport:
        transport.return_value = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        yield transport


@pytest.mark.parametrize(
    "value",
    [
        b"\x00\xff",
        bytearray(b"\x00\xff"),
        memoryview(b"\x00\xff"),
        [0, 255],
        ("0", "255"),
    ],
)
def test_array_payload(value):
    """Encode a ZCL uint8 array with its element type and little-endian count."""
    payload = trv.Uint8ArrayPayload(value)
    assert payload.serialize() == b"\x20\x02\x00\x00\xff"
    decoded, remaining = trv.Uint8ArrayPayload.deserialize(
        payload.serialize() + b"tail"
    )
    assert decoded == b"\x00\xff"
    assert remaining == b"tail"


def test_array_payload_decoded_array():
    """Accept zigpy decoded uint8 arrays and reject a different element type."""
    decoded, _ = foundation.Array.deserialize(b"\x20\x02\x00\x00\xff")
    assert trv.Uint8ArrayPayload(decoded) == b"\x00\xff"
    wrong_type, _ = foundation.Array.deserialize(b"\x21\x01\x00\x00\x00")
    with pytest.raises(ValueError, match="Expected uint8"):
        trv.Uint8ArrayPayload(wrong_type)
    assert trv.Uint8ArrayPayload(None).serialize() == b"\x20\x00\x00"


@pytest.mark.parametrize(
    "data", [b"", b"\x20", b"\x20\x00", b"\x21\x00\x00", b"\x20\x02\x00\x01"]
)
def test_array_payload_invalid(data):
    """Reject missing headers, wrong element types and truncated array bodies."""
    with pytest.raises(ValueError):
        trv.Uint8ArrayPayload.deserialize(data)


@pytest.mark.parametrize(
    ("encode", "decode", "kind", "temperature", "encoded"),
    [
        (
            trv._sonoff_trvzbl_encode_panel_linkage,
            trv._sonoff_trvzbl_decode_panel_linkage,
            2,
            500,
            b"\xf4\x01",
        ),
        (
            trv._sonoff_trvzbl_encode_panel_linkage,
            trv._sonoff_trvzbl_decode_panel_linkage,
            2,
            3000,
            b"\xb8\x0b",
        ),
        (
            trv._sonoff_trvzbl_encode_remote_temperature,
            trv._sonoff_trvzbl_decode_remote_temperature,
            1,
            -3000,
            b"\x48\xf4",
        ),
        (
            trv._sonoff_trvzbl_encode_remote_temperature,
            trv._sonoff_trvzbl_decode_remote_temperature,
            1,
            10000,
            b"\x10\x27",
        ),
    ],
)
@pytest.mark.parametrize("state", [0, 1, 2, 3])
def test_linkage_codec(encode, decode, kind, temperature, encoded, state):
    """Cover every binding state and signed temperature limits with fixed wire bytes."""
    payload = encode(state, temperature)
    assert payload == bytes([1, 1, 0, kind, 3, state]) + (
        encoded if state in (1, 3) else b"\x00\x00"
    )
    assert decode(payload) == (state != 0, temperature if state in (1, 3) else None)


@pytest.mark.parametrize(
    ("encode", "temperature"),
    [
        (trv._sonoff_trvzbl_encode_panel_linkage, 499),
        (trv._sonoff_trvzbl_encode_panel_linkage, 3001),
        (trv._sonoff_trvzbl_encode_remote_temperature, -3001),
        (trv._sonoff_trvzbl_encode_remote_temperature, 10001),
    ],
)
@pytest.mark.parametrize("state", [1, 3])
def test_linkage_temperature_out_of_range(encode, temperature, state):
    """Reject temperatures immediately outside the supported online ranges."""
    with pytest.raises(ValueError):
        encode(state, temperature)


@pytest.mark.parametrize(
    "encode",
    [
        trv._sonoff_trvzbl_encode_panel_linkage,
        trv._sonoff_trvzbl_encode_remote_temperature,
    ],
)
@pytest.mark.parametrize("state", [-1, 4, 255])
def test_linkage_invalid_state(encode, state):
    """Reject undefined binding states before serializing a write."""
    with pytest.raises(ValueError, match="bind state"):
        encode(state, 2100)


@pytest.mark.parametrize(
    "decode",
    [
        trv._sonoff_trvzbl_decode_panel_linkage,
        trv._sonoff_trvzbl_decode_remote_temperature,
    ],
)
@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x01\x01",
        b"\x00\x01\x00",
        b"\x01\x00\x00",
        b"\x01\x01\x01",
        b"\x01\x01\x00\x01",
        b"\x01\x01\x00\x01\x03\x01",
        b"\x01\x01\x00\x02\x03\x04\x34\x08",
    ],
)
def test_linkage_malformed_report(decode, payload):
    """Malformed or unrelated TLVs must not produce a virtual state update."""
    assert decode(payload) == (None, None)


def test_linkage_multiple_tlvs():
    """Find each supported linkage type after an unrelated TLV."""
    payload = bytes.fromhex("01 01 00 7f 01 ff 01 03 01 9c ff 02 03 03 34 08")
    assert trv._sonoff_trvzbl_decode_remote_temperature(payload) == (True, -100)
    assert trv._sonoff_trvzbl_decode_panel_linkage(payload) == (True, 2100)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "Normal"),
        (0x0A0100, "Unknown"),
        (0x0A010001, "Temperature sensor issue"),
        (0x0A020006, "Valve adjustment issue, Low battery"),
        (0x41, "Temperature sensor issue, Unknown"),
        (0x40, "Unknown"),
        (None, "Unknown"),
        ("invalid", "Unknown"),
        (-1, "Unknown"),
        (0x100000000, "Unknown"),
    ],
)
def test_fault_code(value, expected):
    """Decode packed faults, simultaneous faults, unknown bits and invalid inputs."""
    assert trv.convert_sonoff_trvzbl_fault_code(value) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (None, None),
        (b"", "Not detected"),
        (b"\x00\x01\x01", "Detected"),
        (b"\x00\x01\x00", "Not detected"),
        (b"\x20\x03\x00\x00\x01\x01", "Detected"),
        (b"\x00\x01", None),
        (b"\x01\x01\x01", None),
        (b"\x00\x00\x01", None),
    ],
)
def test_window_notification(payload, expected):
    """Decode raw and array-prefixed HVAC notifications without inventing missing state."""
    assert trv.convert_sonoff_trvzbl_open_window_detected(payload) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "none"),
        (1, "Monday"),
        (64, "Sunday"),
        (65, "Monday, Sunday"),
        (129, "Monday, unknown"),
        (None, "unknown"),
    ],
)
def test_weekly_program_days(value, expected):
    """Use the weekly enable bitmap's Monday-first ordering."""
    assert trv.convert_sonoff_trvzbl_weekly_program_state(value) == expected


def test_schedule_command_wire_format():
    """Read commands contain only three bytes; write transitions use signed little endian."""
    assert trv.SonoffScheduleGroupCommand(1, 0, 2).serialize() == bytes.fromhex(
        "01 00 02"
    )
    command = trv.SonoffScheduleGroupCommand(
        "1",
        "1",
        "2",
        transition_count=2,
        day_of_week=6,
        mode=1,
        transition_1_time=0,
        transition_1_heat_setpoint=500,
        transition_2_time=1410,
        transition_2_heat_setpoint=3000,
    )
    assert command.serialize() == bytes.fromhex(
        "01 01 02 02 06 01 00 00 f4 01 82 05 b8 0b"
    )
    assert trv.SonoffRawBytes(b"\x01\x00\x02").serialize() == b"\x01\x00\x02"


@pytest.mark.parametrize(
    "overrides",
    [
        {"read_or_write": 2},
        {"active_num": 256},
        {"transition_count": None},
        {"day_of_week": None},
        {"mode": None},
        {"transition_1_time": None},
        {"transition_1_time": -1},
        {"transition_1_time": 65536},
        {"transition_1_heat_setpoint": -32769},
        {"transition_1_heat_setpoint": 32768},
    ],
)
def test_schedule_command_invalid(overrides):
    """Reject incomplete fields and integer overflow before sending a schedule."""
    fields = {
        "schedule_type": 1,
        "read_or_write": 1,
        "active_num": 0,
        "transition_count": 1,
        "day_of_week": 2,
        "mode": 1,
        "transition_1_time": 0,
        "transition_1_heat_setpoint": 2100,
    }
    fields.update(overrides)
    with pytest.raises(ValueError):
        trv.SonoffScheduleGroupCommand(**fields).serialize()


@pytest.mark.parametrize(
    "wrapper", [bytes, bytearray, lambda value: [value], lambda value: (value,)]
)
def test_schedule_response(wrapper):
    """Decode multi-day responses and suppress duplicate padding only in display text."""
    result = trv.parse_sonoff_trvzbl_schedule_group(
        wrapper(bytes.fromhex("01 00 02 03 06 01 00 00 34 08 68 01 08 07 68 01 08 07"))
    )
    assert result["response_type"] == "read"
    assert result["active_num"] == 2
    assert result["day_name"] == "Monday, Tuesday"
    assert result["schedule"] == "00:00/21 06:00/18"
    assert result["editor_transitions"] == [(0, 2100), (360, 1800), (360, 1800)]


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        bytes.fromhex("01 00 00 01 02"),
        bytes.fromhex("01 00 00 01 02 01 00"),
        bytes.fromhex("01 00 00 01 02 01 c0 fe 34 08"),
    ],
)
def test_schedule_response_without_valid_transition(payload):
    """Reject responses that cannot supply even one complete, valid transition."""
    assert trv.parse_sonoff_trvzbl_schedule_group(payload) is None


@pytest.mark.parametrize(
    ("status", "expected"), [(0, "success"), (1, "fail"), (255, "fail")]
)
def test_schedule_write_ack(status, expected):
    """Map device schedule acknowledgements to success or failure."""
    result = trv.parse_sonoff_trvzbl_schedule_group(bytes([1, 1, 2, status]))
    assert result["response_type"] == "write"
    assert result["status_name"] == expected


async def test_cluster_replacement(trv_device, private_cluster):
    """Resolve the TRV-ZBL fingerprint into all three custom clusters."""
    assert isinstance(trv_device.endpoints[1].basic, trv.SonoffBasicCluster)
    assert isinstance(trv_device.endpoints[1].thermostat, trv.SonoffThermostat)
    assert isinstance(private_cluster, trv.CustomSonoffCluster)


@pytest.mark.parametrize("use_id", [False, True])
async def test_virtual_editor_read_write(private_cluster, write_mock, use_id):
    """Editor changes and reads stay local until an explicit apply operation."""
    attribute = private_cluster.AttributeDefs.temporary_mode_editor_duration
    await private_cluster.write_attributes(
        {attribute.id if use_id else attribute.name: 7200}
    )
    success, failure = await private_cluster.read_attributes(
        [attribute.name], allow_cache=False
    )
    assert success == {attribute.name: 7200}
    assert failure == {}
    write_mock.assert_not_awaited()


@pytest.mark.parametrize("value", [30, 65535])
@pytest.mark.parametrize("use_id", [False, True])
async def test_schedule_invalid_first_time_rolls_back(
    private_cluster, write_mock, value, use_id
):
    """An invalid first transition is rejected without corrupting the editor cache."""
    attr = private_cluster.AttributeDefs.schedule_period_1_time
    before = private_cluster.get(attr.id)
    with pytest.raises(ValueError, match="00:00"):
        await private_cluster.write_attributes(
            {attr.id if use_id else attr.name: value}
        )
    assert private_cluster.get(attr.id) == before
    write_mock.assert_not_awaited()


@pytest.mark.parametrize(
    "status", [foundation.Status.SUCCESS, foundation.Status.FAILURE]
)
async def test_schedule_group_activation(private_cluster, write_mock, status):
    """Update the selected group only after the physical active-group write succeeds."""
    defs = private_cluster.AttributeDefs
    private_cluster.update_attribute(defs.schedule_editor_group.id, 0)
    write_mock.return_value = [
        [
            foundation.WriteAttributesStatusRecord(
                status=status, attrid=defs.weekly_schedule_active_num.id
            )
        ]
    ]
    await private_cluster.write_attributes({defs.schedule_editor_group.name: 2})
    records = write_mock.call_args.args[0]
    assert [(record.attrid, record.value.value) for record in records] == [
        (defs.weekly_schedule_active_num.id, 2)
    ]
    assert private_cluster.get(defs.schedule_editor_group.id) == (
        2 if status == foundation.Status.SUCCESS else 0
    )


@pytest.mark.parametrize(
    ("attribute", "value", "wire", "mirrored"),
    [
        (
            "panel_linkage_target_temperature",
            2100,
            "01 01 00 02 03 01 34 08",
            "panel_linkage_target_temperature",
        ),
        (
            "panel_linkage_enabled",
            True,
            "01 01 00 02 03 02 00 00",
            "panel_linkage_enabled",
        ),
        (
            "external_temperature_sensor",
            True,
            "01 01 00 01 03 02 00 00",
            "external_temperature_sensor",
        ),
    ],
)
@pytest.mark.parametrize(
    "status", [foundation.Status.SUCCESS, foundation.Status.FAILURE]
)
async def test_linkage_write_acknowledgement(
    private_cluster, write_mock, attribute, value, wire, mirrored, status
):
    """Translate virtual writes to a real ZCL array and mirror only acknowledged values."""
    defs = private_cluster.AttributeDefs
    attr = getattr(defs, mirrored)
    before = private_cluster.get(attr.id)
    write_mock.return_value = [
        [
            foundation.WriteAttributesStatusRecord(
                status=status, attrid=defs.remote_attribute_linkage.id
            )
        ]
    ]
    await private_cluster.write_attributes({attribute: value})
    records = write_mock.call_args.args[0]
    assert len(records) == 1
    assert records[0].attrid == defs.remote_attribute_linkage.id
    assert records[0].value.type == foundation.DataTypeId.array
    assert records[0].value.value.serialize() == b"\x20\x08\x00" + bytes.fromhex(wire)
    assert private_cluster.get(attr.id) == (
        value if status == foundation.Status.SUCCESS else before
    )


async def test_external_temperature_preconfigure_and_enable(
    private_cluster, write_mock
):
    """A cached sample does not enable linkage until the source switch is turned on."""
    defs = private_cluster.AttributeDefs
    await private_cluster.write_attributes({defs.external_temperature_input.name: -100})
    write_mock.assert_not_awaited()
    assert private_cluster.get(defs.external_temperature_input.id) == -100
    await private_cluster.write_attributes(
        {defs.external_temperature_sensor.name: True}
    )
    record = write_mock.call_args.args[0][0]
    assert record.value.value.serialize() == bytes.fromhex(
        "20 08 00 01 01 00 01 03 01 9c ff"
    )
    assert private_cluster.get(defs.external_temperature_sensor.id) is True


async def test_linkage_report_preserves_last_temperature(private_cluster):
    """Offline and unbound reports change binding state while retaining the last sample."""
    defs = private_cluster.AttributeDefs
    private_cluster.update_attribute(
        defs.remote_attribute_linkage.id, bytes.fromhex("01 01 00 01 03 01 9c ff")
    )
    assert private_cluster.get(defs.external_temperature_input.id) == -100
    for state, enabled in [(2, True), (0, False)]:
        private_cluster.update_attribute(
            defs.remote_attribute_linkage.id, bytes([1, 1, 0, 1, 3, state, 0, 0])
        )
        assert private_cluster.get(defs.external_temperature_sensor.id) is enabled
        assert private_cluster.get(defs.external_temperature_input.id) == -100


@pytest.mark.parametrize("use_id", [False, True])
async def test_boost_blocks_setpoint(trv_device, private_cluster, use_id):
    """Reject target-temperature changes in Boost before reaching the transport."""
    thermostat = trv_device.endpoints[1].thermostat
    private_cluster.update_attribute(
        private_cluster.AttributeDefs.temporary_mode.id, trv.SonoffTemporaryMode.Boost
    )
    attr = thermostat.AttributeDefs.occupied_heating_setpoint
    with mock.patch.object(
        thermostat, "write_attributes_raw", new_callable=mock.AsyncMock
    ) as transport:
        with pytest.raises(ValueError, match="Boost"):
            await thermostat.write_attributes({attr.id if use_id else attr.name: 2200})
        transport.assert_not_awaited()


@pytest.mark.parametrize(
    ("mode", "duration"), [(0, -60), (0, 61), (0, 10860), (1, 86460)]
)
async def test_temporary_duration_invalid(private_cluster, write_mock, mode, duration):
    """Validate whole-minute durations and the separate Boost/Timer upper limits."""
    with pytest.raises(ValueError, match="temporary_mode_duration"):
        await private_cluster.write_attributes(
            {"temporary_mode": mode, "temporary_mode_duration": duration}
        )
    write_mock.assert_not_awaited()


async def test_schedule_fetch_wire(private_cluster):
    """Fetch serializes the selected group without the local day or a length prefix."""
    private_cluster.update_attribute(trv.SONOFF_TRVZBL_SCHEDULE_EDITOR_GROUP_ATTR, 2)
    with mock.patch.object(
        private_cluster.endpoint, "request", new_callable=mock.AsyncMock
    ) as transport:
        await private_cluster.schedule_fetch()
    header, payload = foundation.ZCLHeader.deserialize(
        transport.call_args.kwargs["data"]
    )
    assert header.command_id == private_cluster.ServerCommandDefs.schedule_group_raw.id
    assert payload == bytes.fromhex("01 00 02")


async def test_schedule_apply_wire(private_cluster):
    """Apply includes only enabled transitions and encodes real protocol temperatures."""
    private_cluster.update_attribute(trv.SONOFF_TRVZBL_SCHEDULE_EDITOR_DAY_ATTR, 2)
    for index in range(2, 13):
        await private_cluster.write_attributes(
            {trv.SONOFF_TRVZBL_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[index]: 65535}
        )
    with mock.patch.object(
        private_cluster.endpoint, "request", new_callable=mock.AsyncMock
    ) as transport:
        await private_cluster.schedule_apply()
    _, payload = foundation.ZCLHeader.deserialize(transport.call_args.kwargs["data"])
    assert payload == bytes.fromhex("01 01 00 01 02 01 00 00 40 06")
    assert (
        private_cluster.get(trv.SONOFF_TRVZBL_SCHEDULE_EDITOR_APPLY_STATUS_ATTR)
        == "apply sent"
    )


async def test_entity_metadata(trv_device):
    """Expose temperature and duration controls with correct scaling and unique IDs."""
    entry = DEVICE_REGISTRY.match_entry(trv_device)
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    by_suffix = {item.resolved_unique_id_suffix: item for item in metadata}
    assert len(by_suffix) == len(metadata)
    for name in ("occupied_heating_setpoint", "panel_linkage_target_temperature"):
        item = by_suffix[name]
        assert (item.min, item.max, item.multiplier) == (5, 30, 0.01)
    accuracy = by_suffix["temperature_control_accuracy"]
    assert (accuracy.min, accuracy.max, accuracy.step, accuracy.multiplier) == (
        -2.0,
        -0.2,
        0.2,
        0.01,
    )
    external = by_suffix["external_temperature_input"]
    assert (external.min, external.max, external.multiplier) == (-30, 100, 0.01)
    assert by_suffix["temporary_mode_editor_duration"].multiplier == pytest.approx(
        1 / 60
    )
    for index in range(1, 13):
        assert f"schedule_period_{index}_time" in by_suffix
        assert by_suffix[f"schedule_period_{index}_temperature"].multiplier == 0.01
    assert {
        "schedule_apply",
        "schedule_fetch",
        "temporary_mode_apply",
        "factory_reset",
    } <= by_suffix.keys()


async def test_schedule_response_updates_selected_days(private_cluster):
    """Readback updates matching weekdays, reloads the editor and preserves other days."""
    defs = private_cluster.AttributeDefs
    private_cluster.update_attribute(defs.schedule_editor_day.id, 2)
    header = foundation.ZCLHeader.cluster(
        tsn=1, command_id=private_cluster.ServerCommandDefs.schedule_group_raw.id
    )
    private_cluster.handle_cluster_request(
        header, bytes.fromhex("01 00 00 02 06 01 00 00 34 08 68 01 08 07")
    )
    for day in (2, 4):
        assert (
            private_cluster.get(trv.SONOFF_TRVZBL_SCHEDULE_ATTR_BY_DAY[day])
            == "00:00/21 06:00/18"
        )
    assert private_cluster.get(trv.SONOFF_TRVZBL_SCHEDULE_ATTR_BY_DAY[1]) is None
    assert private_cluster.get(defs.schedule_period_1_temperature.id) == 2100
    assert private_cluster.get(defs.schedule_period_2_time.id) == 360
    assert private_cluster.get(defs.schedule_period_3_time.id) == 65535
    private_cluster.handle_cluster_request(header, b"\x01")
    assert private_cluster.get(defs.schedule_period_2_time.id) == 360
    private_cluster.handle_cluster_request(header, bytes.fromhex("01 01 00 01"))
    assert private_cluster.get(trv.SONOFF_TRVZBL_SCHEDULE_STATUS_ATTR) == "fail"
    assert private_cluster.get(defs.schedule_period_2_time.id) == 360


@pytest.mark.parametrize(
    ("mode", "duration", "expected"),
    [
        (
            trv.SonoffTemporaryModeEditor.Boost,
            0,
            [{"temporary_mode_duration": 0, "temporary_mode": 0}],
        ),
        (
            trv.SonoffTemporaryModeEditor.Boost,
            3600,
            [
                {"temporary_mode_duration": 3660, "temporary_mode": 0},
                {"temporary_mode_duration": 3600},
            ],
        ),
        (
            trv.SonoffTemporaryModeEditor.Boost,
            10860,
            [
                {"temporary_mode_duration": 10740, "temporary_mode": 0},
                {"temporary_mode_duration": 10800},
            ],
        ),
        (
            trv.SonoffTemporaryModeEditor.Timer,
            86400,
            [
                {"timer_mode_target_temperature": 2100},
                {"temporary_mode_duration": 86400},
                {"temporary_mode": 1},
            ],
        ),
    ],
)
async def test_temporary_apply_write_order(
    trv_device, private_cluster, write_mock, mode, duration, expected
):
    """Apply Timer in target/duration/mode order and force the Boost duration refresh."""
    thermostat = trv_device.endpoints[1].thermostat
    thermostat.update_attribute(
        thermostat.AttributeDefs.occupied_heating_setpoint.id, 1900
    )
    thermostat.update_attribute(
        thermostat.AttributeDefs.system_mode.id, trv.SonoffSystemMode.Auto
    )
    await private_cluster.write_attributes(
        {"temporary_mode_editor_mode": mode, "temporary_mode_editor_duration": duration}
    )
    await private_cluster.temporary_mode_apply()
    writes = [
        {
            private_cluster.find_attribute(record.attrid).name: record.value.value
            for record in call.args[0]
        }
        for call in write_mock.call_args_list
    ]
    assert writes == expected
    assert (
        private_cluster.get(trv.SONOFF_TRVZBL_TEMPORARY_MODE_EDITOR_APPLY_STATUS_ATTR)
        == "apply sent"
    )
    assert private_cluster._sonoff_trvzbl_pre_temporary_state == {
        "occupied_heating_setpoint": 1900,
        "system_mode": trv.SonoffSystemMode.Auto,
    }


@pytest.mark.parametrize(
    ("duration", "target"),
    [(-60, 2100), (61, 2100), (86460, 2100), (3600, 499), (3600, 3001)],
)
async def test_temporary_apply_invalid(
    trv_device, private_cluster, write_mock, duration, target
):
    """Invalid Timer settings must never be sent as device attribute writes."""
    thermostat = trv_device.endpoints[1].thermostat
    thermostat.update_attribute(
        thermostat.AttributeDefs.occupied_heating_setpoint.id, 1900
    )
    thermostat.update_attribute(
        thermostat.AttributeDefs.system_mode.id, trv.SonoffSystemMode.Auto
    )
    await private_cluster.write_attributes(
        {
            "temporary_mode_editor_mode": trv.SonoffTemporaryModeEditor.Timer,
            "temporary_mode_editor_duration": duration,
            "temporary_mode_editor_target_temperature": target,
        }
    )
    with pytest.raises(ValueError):
        await private_cluster.temporary_mode_apply()
    write_mock.assert_not_awaited()


async def test_temporary_exit_restores_state(trv_device, private_cluster):
    """Exit uses the saved setpoint even during Boost and restores the original system mode."""
    thermostat = trv_device.endpoints[1].thermostat
    private_cluster._sonoff_trvzbl_pre_temporary_state = {
        "occupied_heating_setpoint": 1900,
        "system_mode": trv.SonoffSystemMode.Auto,
    }
    private_cluster.update_attribute(
        private_cluster.AttributeDefs.temporary_mode.id, trv.SonoffTemporaryMode.Boost
    )
    with mock.patch.object(
        thermostat, "write_attributes_raw", new_callable=mock.AsyncMock
    ) as transport:
        transport.return_value = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        await private_cluster.temporary_mode_exit()
    writes = [
        {
            thermostat.find_attribute(record.attrid).name: record.value.value
            for record in call.args[0]
        }
        for call in transport.call_args_list
    ]
    assert writes == [
        {"occupied_heating_setpoint": 1900},
        {"system_mode": trv.SonoffSystemMode.Auto},
    ]
    assert (
        private_cluster.get(private_cluster.AttributeDefs.temporary_mode.id)
        == trv.SonoffTemporaryMode.None_
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.temporary_mode_duration.id)
        == 0
    )
    assert private_cluster._sonoff_trvzbl_pre_temporary_state is None


@pytest.mark.parametrize(
    "method_name",
    [
        "_sonoff_trvzbl_read_temporary_mode_later",
        "_sonoff_trvzbl_read_device_work_mode_later",
    ],
)
async def test_delayed_read_retries(private_cluster, method_name):
    """A transport error and an empty response are retried, stopping at the third attempt."""
    attribute_name = (
        "temporary_mode" if "temporary" in method_name else "device_work_mode"
    )
    with mock.patch.object(
        private_cluster, "read_attributes", new_callable=mock.AsyncMock
    ) as reader:
        reader.side_effect = [TimeoutError(), ({}, {}), ({attribute_name: 1}, {})]
        await getattr(private_cluster, method_name)(delay=0)
    assert reader.await_count == 3
    reader.assert_awaited_with([attribute_name], allow_cache=False)


@pytest.mark.parametrize(
    ("convert", "value", "expected"),
    [
        (trv.convert_sonoff_trvzbl_motor_travel_calibration_status, 0, "Normal"),
        (trv.convert_sonoff_trvzbl_motor_travel_calibration_status, 1, "Failed"),
        (trv.convert_sonoff_trvzbl_motor_travel_calibration_status, 3, "Unknown 0x03"),
        (trv.convert_sonoff_trvzbl_motor_travel_calibration_status, None, "Unknown"),
        (trv.convert_sonoff_trvzbl_device_work_mode, 3, "Manual"),
        (trv.convert_sonoff_trvzbl_device_work_mode, 4, "Schedule"),
        (trv.convert_sonoff_trvzbl_device_work_mode, 255, "Unknown 0xFF"),
        (trv.convert_sonoff_trvzbl_device_work_mode, "bad", "Unknown"),
    ],
)
def test_status_converters(convert, value, expected):
    """Retain unknown diagnostics instead of mapping them to a valid device state."""
    assert convert(value) == expected


@pytest.mark.parametrize(
    "value", [None, b"\x00\x01\x01", bytearray(b"\x00\x01\x01"), [0, 1, 1], (0, 1, 1)]
)
def test_hvac_payload_normalization(value):
    """Normalize the report representations accepted from zigpy and service input."""
    payload = trv.SonoffHvacMessageNotification(value)
    assert payload.serialize() == (b"" if value is None else b"\x00\x01\x01")
    assert trv.SonoffHvacMessageNotification.deserialize(payload.serialize()) == (
        payload,
        b"",
    )
    assert trv.SonoffRawBytes.deserialize(payload.serialize()) == (payload, b"")


def test_hvac_decoded_array():
    """Accept a decoded ZCL array and safely ignore non-iterable notifications."""
    decoded, _ = foundation.Array.deserialize(bytes.fromhex("20 03 00 00 01 01"))
    assert trv.SonoffHvacMessageNotification(decoded) == b"\x00\x01\x01"
    assert trv.SonoffHvacMessageNotification(object()) == b""
    assert trv.convert_sonoff_trvzbl_open_window_detected(["0", "1", "1"]) == "Detected"
    assert trv.convert_sonoff_trvzbl_open_window_detected(object()) is None


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        (
            {
                "cluster_id": trv.SonoffThermostat.cluster_id,
                "unique_id_suffix": "local_temperature_calibration",
            },
            True,
        ),
        ({"attribute_name": "min_heat_setpoint_limit"}, True),
        ({"fallback_name": "Max heat setpoint limit"}, True),
        ({"translation_key": "battery"}, False),
        ({"unique_id_suffix": "identify"}, False),
        ({}, False),
    ],
)
def test_default_entity_filter(fields, expected):
    """Hide replaced thermostat settings while retaining native battery and identify entities."""
    assert (
        trv._sonoff_trvzbl_is_replaced_default_entity(SimpleNamespace(**fields))
        is expected
    )


@pytest.mark.parametrize("use_id", [False, True])
async def test_temperature_offset_proxy(trv_device, private_cluster, use_id):
    """Calibration reads and writes use the standard thermostat attribute, preserving raw units."""
    thermostat = trv_device.endpoints[1].thermostat
    attr = private_cluster.AttributeDefs.local_temperature_offset
    with mock.patch.object(
        thermostat, "write_attributes", new_callable=mock.AsyncMock
    ) as writer:
        await private_cluster.write_attributes({attr.id if use_id else attr.name: -20})
    writer.assert_awaited_once_with(
        {"local_temperature_calibration": -20}, manufacturer=None
    )
    with mock.patch.object(
        thermostat, "read_attributes", new_callable=mock.AsyncMock
    ) as reader:
        reader.return_value = ({"local_temperature_calibration": 12}, {})
        success, failure = await private_cluster.read_attributes(
            [attr.name], allow_cache=False
        )
    reader.assert_awaited_once_with(
        ["local_temperature_calibration"],
        allow_cache=False,
        only_cache=False,
        manufacturer=None,
    )
    assert success == {attr.name: 12}
    assert failure == {}
    assert private_cluster.get(attr.id) == 12


async def test_temperature_offset_missing_thermostat(trv_device, private_cluster):
    """Missing thermostat permits cached calibration reads but cannot accept writes or exits."""
    trv_device.endpoints[1].in_clusters.pop(trv.SonoffThermostat.cluster_id)
    attr = private_cluster.AttributeDefs.local_temperature_offset
    private_cluster.update_attribute(attr.id, 10)
    assert await private_cluster.read_attributes([attr.name]) == ({attr.name: 10}, {})
    with pytest.raises(ValueError, match="thermostat cluster"):
        await private_cluster.write_attributes({attr.name: 20})
    with pytest.raises(ValueError, match="thermostat cluster"):
        await private_cluster.temporary_mode_exit()
    await private_cluster._sonoff_trvzbl_capture_pre_temporary_state()
    assert private_cluster._sonoff_trvzbl_pre_temporary_state is None


@pytest.mark.parametrize("use_id", [False, True])
@pytest.mark.parametrize("day", [0, 128, "invalid"])
async def test_invalid_editor_day_uses_today(private_cluster, use_id, day):
    """Invalid day selections fall back to the local weekday and load its cached schedule."""
    attr = private_cluster.AttributeDefs.schedule_editor_day
    with mock.patch.object(trv, "_sonoff_trvzbl_today_schedule_day", return_value=2):
        await private_cluster.write_attributes({attr.id if use_id else attr.name: day})
        success, failure = await private_cluster.read_attributes([attr.name])
    assert success == {attr.name: 2}
    assert failure == {}
    assert (
        private_cluster.get(private_cluster.AttributeDefs.schedule_period_1_time.id)
        == 0
    )


@pytest.mark.parametrize("use_id", [False, True])
async def test_raw_linkage_write(private_cluster, write_mock, use_id):
    """Blueprint writes of the real linkage attribute update both virtual mirrors."""
    attr = private_cluster.AttributeDefs.remote_attribute_linkage
    payload = trv.Uint8ArrayPayload(bytes.fromhex("01 01 00 02 03 01 34 08"))
    await private_cluster.write_attributes({attr.id if use_id else attr.name: payload})
    assert (
        private_cluster.get(private_cluster.AttributeDefs.panel_linkage_enabled.id)
        is True
    )
    assert (
        private_cluster.get(
            private_cluster.AttributeDefs.panel_linkage_target_temperature.id
        )
        == 2100
    )
    assert write_mock.await_count == 1


async def test_linkage_enable_disable_and_sample_update(private_cluster, write_mock):
    """Enable uses a cached target; disabling emits unbound frames; online samples are forwarded."""
    defs = private_cluster.AttributeDefs
    private_cluster.update_attribute(defs.panel_linkage_target_temperature.id, 2100)
    await private_cluster.write_attributes({defs.panel_linkage_enabled.name: True})
    await private_cluster.write_attributes({defs.panel_linkage_enabled.name: False})
    await private_cluster.write_attributes(
        {defs.external_temperature_sensor.name: False}
    )
    private_cluster.update_attribute(defs.external_temperature_sensor.id, True)
    await private_cluster.write_attributes({defs.external_temperature_input.name: 2200})
    frames = [
        call.args[0][0].value.value.serialize() for call in write_mock.call_args_list
    ]
    assert frames == [
        bytes.fromhex(value)
        for value in (
            "20 08 00 01 01 00 02 03 01 34 08",
            "20 08 00 01 01 00 02 03 00 00 00",
            "20 08 00 01 01 00 01 03 00 00 00",
            "20 08 00 01 01 00 01 03 01 98 08",
        )
    ]


async def test_capture_missing_state_and_no_overwrite(trv_device, private_cluster):
    """Capture uncached thermostat values once and retain them across subsequent applies."""
    thermostat = trv_device.endpoints[1].thermostat
    with mock.patch.object(
        thermostat, "read_attributes", new_callable=mock.AsyncMock
    ) as reader:
        reader.return_value = (
            {
                "occupied_heating_setpoint": 1800,
                "system_mode": trv.SonoffSystemMode.Auto,
            },
            {},
        )
        await private_cluster._sonoff_trvzbl_capture_pre_temporary_state()
        await private_cluster._sonoff_trvzbl_capture_pre_temporary_state()
    assert reader.await_count == 1
    assert private_cluster._sonoff_trvzbl_pre_temporary_state == {
        "occupied_heating_setpoint": 1800,
        "system_mode": trv.SonoffSystemMode.Auto,
    }


async def test_capture_read_failure(trv_device, private_cluster):
    """A failed optional snapshot read does not prevent temporary mode from being configured."""
    thermostat = trv_device.endpoints[1].thermostat
    with mock.patch.object(thermostat, "read_attributes", side_effect=TimeoutError()):
        await private_cluster._sonoff_trvzbl_capture_pre_temporary_state()
    assert private_cluster._sonoff_trvzbl_pre_temporary_state == {
        "occupied_heating_setpoint": None,
        "system_mode": None,
    }


async def test_exit_reads_uncached_setpoint(trv_device, private_cluster):
    """Exit reads the live setpoint when there is no saved or cached target."""
    thermostat = trv_device.endpoints[1].thermostat
    with (
        mock.patch.object(
            thermostat, "read_attributes", new_callable=mock.AsyncMock
        ) as reader,
        mock.patch.object(
            thermostat, "write_attributes_raw", new_callable=mock.AsyncMock
        ) as writer,
    ):
        reader.return_value = (
            {thermostat.AttributeDefs.occupied_heating_setpoint.id: 2050},
            {},
        )
        writer.return_value = [
            [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
        ]
        await private_cluster.temporary_mode_exit()
    assert writer.call_args.args[0][0].value.value == 2050
    reader.assert_awaited_once_with(
        ["occupied_heating_setpoint"], allow_cache=False, manufacturer=None
    )


async def test_temporary_none_apply_exits(private_cluster):
    """Applying the None editor option invokes the exit operation without private writes."""
    await private_cluster.write_attributes(
        {"temporary_mode_editor_mode": trv.SonoffTemporaryModeEditor.None_}
    )
    with mock.patch.object(
        private_cluster, "temporary_mode_exit", new_callable=mock.AsyncMock
    ) as exit_mode:
        await private_cluster.temporary_mode_apply()
    exit_mode.assert_awaited_once_with(expect_reply=False)


async def test_temporary_none_write_is_local(private_cluster, write_mock):
    """Do not transmit the display-only inactive sentinel rejected by the physical device."""
    await private_cluster.write_attributes(
        {"temporary_mode": trv.SonoffTemporaryMode.None_}
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.temporary_mode_editor_mode.id)
        == trv.SonoffTemporaryModeEditor.None_
    )
    write_mock.assert_not_awaited()


@pytest.mark.parametrize(("slot", "value"), [(1, 30), (1, 65535), (2, 0), (2, 1440)])
async def test_schedule_apply_invalid_time(private_cluster, slot, value):
    """Malformed cached editor times cannot be sent even if they bypass the editor write path."""
    private_cluster.update_attribute(
        trv.SONOFF_TRVZBL_SCHEDULE_EDITOR_PERIOD_TIME_ATTRS[slot], value
    )
    with (
        mock.patch.object(
            private_cluster.endpoint, "request", new_callable=mock.AsyncMock
        ) as transport,
        pytest.raises(ValueError),
    ):
        await private_cluster.schedule_apply()
    transport.assert_not_awaited()


@pytest.mark.parametrize("temperature", [499, 3001, -32769, 32768])
async def test_schedule_apply_invalid_temperature(private_cluster, temperature):
    """Reject invalid temperature bounds and signed integer overflow before sending."""
    private_cluster.update_attribute(
        trv.SONOFF_TRVZBL_SCHEDULE_EDITOR_PERIOD_TEMP_ATTRS[1], temperature
    )
    with (
        mock.patch.object(
            private_cluster.endpoint, "request", new_callable=mock.AsyncMock
        ) as transport,
        pytest.raises(ValueError),
    ):
        await private_cluster.schedule_apply()
    transport.assert_not_awaited()
