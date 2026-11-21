"""Offline protocol/quirk checks; no radio or real detector required."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from zha.application.platforms.binary_sensor import BinarySensor
from zha.application.platforms.sensor import EnumSensor
import zigpy.device
from zigpy.exceptions import DeliveryError
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation

from zhaquirks.builder import EntityPlatform
from zhaquirks.tuya import (
    TUYA_ACTIVE_STATUS_RPT,
    TUYA_CLUSTER_ID,
    TUYA_GET_DATA,
    TUYA_QUERY_DATA,
    TUYA_SET_DATA_RESPONSE,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
    tuya_smoke_co as q,
)
from zhaquirks.tuya.mcu import TuyaClusterData


@pytest.fixture
def smoke_co_cluster(zigpy_device_from_v2_quirk) -> q.MoesSmokeCOCluster:
    """Resolve the Tuya cluster on the matched detector."""
    device = zigpy_device_from_v2_quirk(
        "_TZE284_aoah6bv8",
        "TS0601",
        cluster_ids={1: {TUYA_CLUSTER_ID: ClusterType.Server}},
    )
    return device.endpoints[1].in_clusters[TUYA_CLUSTER_ID]


@pytest.fixture
def query_transport(monkeypatch, smoke_co_cluster) -> tuple[AsyncMock, Mock]:
    """Capture serialized Zigbee requests and control the query response window."""
    request = AsyncMock()
    clock = Mock(return_value=100.0)
    monkeypatch.setattr(smoke_co_cluster.endpoint, "request", request)
    monkeypatch.setattr(q, "monotonic", clock)
    return request, clock


def _receive_report(
    cluster: q.MoesSmokeCOCluster, command_id: int, *datapoints: tuple[int, t.enum8]
) -> None:
    """Deliver a serialized Tuya report through the quirk's ZCL handler."""
    hdr = foundation.ZCLHeader.cluster(
        tsn=1, command_id=command_id, direction=foundation.Direction.Server_to_Client
    )
    hdr = hdr.replace(
        frame_control=hdr.frame_control.replace(disable_default_response=True)
    )
    command = TuyaCommand(
        status=0,
        tsn=1,
        datapoints=[
            TuyaDatapointData(dp=dp, data=TuyaData(value)) for dp, value in datapoints
        ],
    )
    schema = cluster.client_commands[command_id].schema(data=command)
    decoded_hdr, decoded_args = cluster.deserialize(
        hdr.serialize() + schema.serialize()
    )
    cluster.handle_cluster_request(decoded_hdr, decoded_args)


async def test_smoke_co_reports():
    """Test matching, alarm transitions and Tuya report dispatch without hardware."""
    app = MagicMock()
    app.get_sequence.return_value = 1
    device = zigpy.device.Device(
        app, t.EUI64.convert("00:11:22:33:44:55:66:77"), 0x1234
    )
    device.manufacturer = "_TZE284_aoah6bv8"
    device.model = "TS0601"
    ep = device.add_endpoint(1)
    ep.profile_id = 0x0104
    ep.device_type = 0x0051
    for cid in (0, 4, 5, 0xED00, 0xEF00):
        ep.add_input_cluster(cid)
    for cid in (10, 25):
        ep.add_output_cluster(cid)
    assert q.QUIRK.device_match.matches(device)
    device.manufacturer = "_TZE284_other"
    assert not q.QUIRK.device_match.matches(device)
    device.manufacturer = "_TZE284_aoah6bv8"
    for transform in q.QUIRK.zigpy_transforms:
        device = transform(device)
    cluster = device.endpoints[1].in_clusters[0xEF00]
    assert 0xED00 in device.endpoints[1].in_clusters

    def state(name):
        """Read the binary state through ZHA using the cluster cache."""
        return BinarySensor.is_on.fget(
            SimpleNamespace(
                _cluster=cluster,
                _attribute_name=name,
                _attribute_converter=q.alarm_state,
            )
        )

    for name in ("smoke_state", "co_state", "battery_state"):
        assert state(name) is None, (name, cluster.get(name))

    # Numeric attribute IDs must preserve unknown states before any report.
    for name, expected in (
        ("smoke_state", 3),
        ("co_state", 255),
        ("battery_state", 255),
    ):
        attribute_id = cluster.attributes_by_name[name].id
        assert cluster.get(attribute_id) == expected
        assert q.alarm_state(cluster.get(attribute_id)) is None

    def report(dp, value):
        """Round-trip the wire format before updating the cluster."""
        raw = TuyaDatapointData(dp=dp, data=TuyaData(value)).serialize()
        decoded, rest = TuyaDatapointData.deserialize(raw)
        assert not rest
        cluster._dp_2_attr_update(decoded)

    for dp, name, enum in (
        (1, "smoke_state", q.SmokeState),
        (18, "co_state", q.COState),
        (14, "battery_state", q.BatteryState),
    ):
        for value, expected in ((0, True), (1, False), (0, True)):
            report(dp, enum(value))
            assert state(name) is expected
    for value in (2, 3, 254):
        report(1, q.SmokeState(value))
        assert state("smoke_state") is None
    for value in range(4):
        report(9, q.CheckingResult(value))
        assert cluster.get("checking_result") == value
    for value in (0, 1, 2, 4, 8, 16, 31):
        report(11, t.bitmap8(value))
        assert cluster.get("fault_bitmap") == value
    for value in (True, False):
        report(16, t.Bool(value))
        assert bool(cluster.get("muffling")) is value
    for value in (True, False):
        commands = cluster.from_cluster_data(
            TuyaClusterData(
                endpoint_id=1,
                cluster_name=cluster.ep_attribute,
                cluster_attr="muffling",
                attr_value=t.Bool(value),
                expect_reply=False,
                manufacturer=None,
            )
        )
        assert len(commands) == 1
        dp = commands[0].datapoints[0]
        assert dp.dp == 16 and dp.data.dp_type == TuyaDPType.BOOL
        assert bool(dp.data.payload) is value
    # Verify dispatch through each supported response/report command.
    report(1, q.SmokeState.Normal)
    for command_id in (TUYA_GET_DATA, TUYA_SET_DATA_RESPONSE, TUYA_ACTIVE_STATUS_RPT):
        for value, expected in ((0, True), (1, False)):
            _receive_report(cluster, command_id, (18, q.COState(value)))
            assert cluster.get("co_state") == value
            assert state("co_state") is expected
    # Muting must not clear an outstanding CO alarm.
    report(18, q.COState.Alarm)
    report(16, t.Bool(True))
    assert state("co_state") is True


@pytest.mark.parametrize("missing_dp", [1, 14, 18])
async def test_smoke_co_query_after_report(
    smoke_co_cluster, query_transport, missing_dp
):
    """A missing state permits one follow-up after the initial response window."""
    request, clock = query_transport
    cluster = smoke_co_cluster
    await cluster.endpoint.device.apply_custom_configuration()
    initial = [
        (1, q.SmokeState.Normal),
        (14, q.BatteryState.High),
        (18, q.COState.Normal),
    ]
    _receive_report(
        cluster,
        TUYA_SET_DATA_RESPONSE,
        *(item for item in initial if item[0] != missing_dp),
    )
    await asyncio.sleep(0)
    request.assert_awaited_once()

    clock.return_value += q._QUERY_RESPONSE_WINDOW + 1
    await asyncio.sleep(0)
    request.assert_awaited_once()

    for command_id in (TUYA_SET_DATA_RESPONSE, TUYA_ACTIVE_STATUS_RPT):
        _receive_report(cluster, command_id, (9, q.CheckingResult.Check_success))
    await asyncio.sleep(0)
    assert request.await_count == 2

    clock.return_value += q._QUERY_RESPONSE_WINDOW + 1
    _receive_report(cluster, TUYA_GET_DATA, (9, q.CheckingResult.Check_success))
    await asyncio.sleep(0)
    assert request.await_count == 2

    for call in request.await_args_list:
        header, payload = foundation.ZCLHeader.deserialize(call.kwargs["data"])
        assert call.kwargs["cluster"] == TUYA_CLUSTER_ID
        assert header.command_id == TUYA_QUERY_DATA
        assert header.direction == foundation.Direction.Client_to_Server
        assert not header.frame_control.is_manufacturer_specific
        assert not payload


async def test_smoke_co_skip_followup_when_last_state_arrives(
    smoke_co_cluster, query_transport
):
    """Apply incoming values before checking whether a query is needed."""
    request, clock = query_transport
    cluster = smoke_co_cluster
    await cluster.endpoint.device.apply_custom_configuration()
    _receive_report(
        cluster,
        TUYA_SET_DATA_RESPONSE,
        (1, q.SmokeState.Detecting),
        (18, q.COState.Alarm),
    )
    clock.return_value += q._QUERY_RESPONSE_WINDOW + 1
    _receive_report(cluster, TUYA_GET_DATA, (14, q.BatteryState.Low))
    await asyncio.sleep(0)
    request.assert_awaited_once()
    assert cluster.get("battery_state") == q.BatteryState.Low
    assert cluster.get("co_state") == q.COState.Alarm


@pytest.mark.parametrize("error", [DeliveryError, TimeoutError])
async def test_smoke_co_query_delivery_failure(
    smoke_co_cluster, query_transport, error
):
    """A failed initial query allows a single attempt on a later report."""
    request, _clock = query_transport
    request.side_effect = [
        error("Initial query failed"),
        error("Follow-up query failed"),
    ]
    cluster = smoke_co_cluster
    await cluster.endpoint.device.apply_custom_configuration()
    request.assert_awaited_once()
    _receive_report(
        cluster, TUYA_ACTIVE_STATUS_RPT, (9, q.CheckingResult.Check_success)
    )
    await asyncio.sleep(0)
    _receive_report(
        cluster, TUYA_ACTIVE_STATUS_RPT, (9, q.CheckingResult.Check_success)
    )
    await asyncio.sleep(0)
    assert request.await_count == 2
    assert cluster.get("smoke_state") == q.SmokeState.Unknown
    assert cluster.get("co_state") == q.COState.Unknown
    assert cluster.get("battery_state") == q.BatteryState.Unknown


async def test_smoke_co_query_already_pending(smoke_co_cluster, query_transport):
    """Reports and concurrent configuration leave one active status request."""
    request, _clock = query_transport
    cluster = smoke_co_cluster
    device = cluster.endpoint.device
    query_started, finish_query = asyncio.Event(), asyncio.Event()

    async def hold_request(**_kwargs):
        query_started.set()
        await finish_query.wait()

    request.side_effect = hold_request
    configuration = asyncio.create_task(device.apply_custom_configuration())
    try:
        await query_started.wait()
        _receive_report(cluster, TUYA_SET_DATA_RESPONSE, (1, q.SmokeState.Normal))
        await device.apply_custom_configuration()
        await asyncio.sleep(0)
        request.assert_awaited_once()
    finally:
        finish_query.set()
        await configuration


def test_smoke_co_entities():
    """Verify all declared entities, unique IDs, enum names and read-only states."""
    metadata = q.QUIRK.zha_device_factory.quirk_definition.entity_metadata
    assert len(metadata) == 9
    identities = [
        (m.endpoint_id, m.unique_id_suffix or m.attribute_name) for m in metadata
    ]
    assert len(set(identities)) == len(identities)
    assert sum(m.entity_platform == EntityPlatform.BINARY_SENSOR for m in metadata) == 3
    assert sum(m.entity_platform == EntityPlatform.SENSOR for m in metadata) == 5
    assert sum(m.entity_platform == EntityPlatform.SWITCH for m in metadata) == 1
    for m in metadata:
        if m.entity_platform == EntityPlatform.BINARY_SENSOR:
            assert m.attribute_converter(0) is True
            assert m.attribute_converter(1) is False
            assert m.attribute_converter(255) is None
    for enum in (q.SmokeState, q.COState):
        sensor = SimpleNamespace(_enum=enum)
        assert EnumSensor.formatter(sensor, t.enum8(0)) == "Alarm"
        assert EnumSensor.formatter(sensor, t.enum8(1)) == "Normal"
