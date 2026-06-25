"""Tests for Shelly quirks."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, call

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, ReportingConfig, foundation
from zigpy.zcl.clusters.general import Basic, BinaryInput, OnOff
from zigpy.zcl.foundation import ZCLAttributeAccess

import zhaquirks
from zhaquirks.shelly import (
    SHELLY_CUSTOM_ENDPOINT_ID,
    SHELLY_CUSTOM_PROFILE_ID,
    SHELLY_INPUT_REFRESH_MIN_INTERVAL,
    SHELLY_INPUT_REFRESH_TIMEOUT,
    SHELLY_MANUFACTURER_CODE,
    SHELLY_RPC_CLUSTER_ID,
    SHELLY_RPC_DATA_CHUNK_SIZE,
    SHELLY_RPC_RESPONSE_TIMEOUT,
    SHELLY_WIFI_SETUP_CLUSTER_ID,
)
from zhaquirks.shelly.wifi import ShellyWiFiSetupCluster
from zhaquirks.shelly.zigbee import (
    ShellyCustomProfileDevice,
    ShellyInputCluster,
    ShellyInputOnOffCluster,
    ShellyRpcCluster,
    ShellyRpcError,
)

zhaquirks.setup()


def test_shelly_input_refresh_timeout_covers_rpc_response_window() -> None:
    """Ensure input refreshes do not cancel the RPC response window early."""

    assert SHELLY_INPUT_REFRESH_TIMEOUT > SHELLY_RPC_RESPONSE_TIMEOUT


def _attribute_report_data(
    attribute: foundation.ZCLAttributeDef, value: object
) -> bytes:
    """Build a typed ZCL attribute report payload for Shelly attributes."""

    header = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        manufacturer=SHELLY_MANUFACTURER_CODE,
        direction=foundation.Direction.Server_to_Client,
    ).serialize()
    response = foundation.Attribute(
        attrid=attribute.id,
        value=foundation.TypeValue(type=attribute.zcl_type, value=value),
    )
    command = (
        foundation.GENERAL_COMMANDS[foundation.GeneralCommand.Report_Attributes]
        .schema([response])
        .serialize()
    )
    return t.SerializableBytes(header + command).serialize()


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_setup_cluster_replaced(zigpy_device_from_v2_quirk, model) -> None:
    """Ensure Shelly relay devices expose typed custom clusters."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_WIFI_SETUP_CLUSTER_ID
    ]

    assert isinstance(quirked, ShellyCustomProfileDevice)
    assert isinstance(rpc_cluster, ShellyRpcCluster)
    assert rpc_cluster.ep_attribute == "shelly_rpc"
    assert rpc_cluster.find_attribute("data") == rpc_cluster.AttributeDefs.data
    assert rpc_cluster.AttributeDefs.data.manufacturer_code == SHELLY_MANUFACTURER_CODE
    assert rpc_cluster.AttributeDefs.data.access == (
        ZCLAttributeAccess.Read | ZCLAttributeAccess.Write
    )
    assert rpc_cluster.AttributeDefs.tx_ctl.access == ZCLAttributeAccess.Write
    assert rpc_cluster.AttributeDefs.rx_ctl.access == ZCLAttributeAccess.Read
    assert isinstance(cluster, ShellyWiFiSetupCluster)
    assert cluster.ep_attribute == "shelly_wifi_setup"
    assert cluster.find_attribute("status") == cluster.AttributeDefs.status
    assert cluster.find_attribute("ssid") == cluster.AttributeDefs.ssid
    assert cluster.AttributeDefs.status.manufacturer_code == SHELLY_MANUFACTURER_CODE
    assert cluster.AttributeDefs.dhcp.access == ZCLAttributeAccess.Read
    assert cluster.AttributeDefs.enable.access == (
        ZCLAttributeAccess.Read | ZCLAttributeAccess.Write
    )
    assert cluster.AttributeDefs.action.access == ZCLAttributeAccess.Write
    assert cluster.AttributeDefs.action.type is t.uint8_t


@pytest.mark.parametrize("model", ["1PM", "Mini1PM", "Mini1"])
def test_shelly_input_cluster_added(zigpy_device_from_v2_quirk, model) -> None:
    """Ensure single-input Shelly relay devices expose a virtual binary input."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, 2, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            2: {OnOff.cluster_id: ClusterType.Client},
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            },
        },
    )

    cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    command_cluster = quirked.endpoints[2].out_clusters[OnOff.cluster_id]

    assert isinstance(cluster, ShellyInputCluster)
    assert isinstance(command_cluster, ShellyInputOnOffCluster)
    assert cluster.get(BinaryInput.AttributeDefs.description.name) == "Input"
    assert cluster.get(BinaryInput.AttributeDefs.out_of_service.name) is False
    assert cluster.get(BinaryInput.AttributeDefs.status_flags.name) == 0
    assert cluster.input_id == 0


def test_shelly_input_on_off_commands_update_state(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure firmware 2.0 input commands update the binary input state."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, 2, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            2: {OnOff.cluster_id: ClusterType.Client},
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            },
        },
    )
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    command_cluster = quirked.endpoints[2].out_clusters[OnOff.cluster_id]

    for command, expected_state in (
        (OnOff.ServerCommandDefs.on, True),
        (OnOff.ServerCommandDefs.off, False),
        (OnOff.ServerCommandDefs.toggle, True),
    ):
        command_cluster.handle_cluster_request(
            foundation.ZCLHeader.cluster(tsn=1, command_id=command.id),
            [],
        )
        assert (
            input_cluster.get(BinaryInput.AttributeDefs.present_value.name)
            is expected_state
        )


def test_shelly_input_on_off_attribute_updates_state(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure firmware 2.0 On/Off updates reach the binary input state."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, 2, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            2: {OnOff.cluster_id: ClusterType.Client},
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            },
        },
    )
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    command_cluster = quirked.endpoints[2].out_clusters[OnOff.cluster_id]

    command_cluster.update_attribute(OnOff.AttributeDefs.on_off.id, True)
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is True

    command_cluster.update_attribute(OnOff.AttributeDefs.on_off.id, False)
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is False


async def test_shelly_rpc_cluster_apply_custom_configuration(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure the Shelly RPC cluster binds and reports pending frames."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    rx_ctl_def = rpc_cluster.find_attribute("rx_ctl")
    rpc_cluster.bind = AsyncMock()
    rpc_cluster.configure_reporting_multiple = AsyncMock()

    await quirked.apply_custom_configuration()

    rpc_cluster.bind.assert_awaited_once_with()
    rpc_cluster.configure_reporting_multiple.assert_awaited_once_with(
        {
            rx_ctl_def: ReportingConfig(
                min_interval=0,
                max_interval=900,
                reportable_change=1,
            )
        }
    )


async def test_shelly_input_cluster_refreshes_state_over_rpc(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure the virtual binary input refreshes Shelly input status through RPC."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    rpc_cluster.rpc_call = AsyncMock(return_value={"state": True})

    await input_cluster.refresh_input_state()

    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is True
    rpc_cluster.rpc_call.assert_awaited_once_with(
        "Input.GetStatus",
        {"id": 0},
        accept_status_notification=True,
    )


async def test_shelly_input_cluster_accepts_notify_status_rpc_response(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure input refresh accepts NotifyStatus as the RPC response."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    rpc_cluster.write_attributes = AsyncMock()
    rpc_cluster._read_rpc_frame = AsyncMock(
        return_value={
            "src": "shellymini1pm",
            "dst": "zha",
            "method": "NotifyStatus",
            "params": {"input:0": {"id": 0, "state": True}},
        }
    )

    await input_cluster.refresh_input_state()

    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is True
    rpc_cluster._read_rpc_frame.assert_awaited_once()


async def test_shelly_input_cluster_uses_recent_cached_state(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure recent Shelly input state avoids redundant RPC reads."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    rpc_cluster.rpc_call = AsyncMock()

    input_cluster.update_input_state(False)
    await input_cluster.refresh_input_state()

    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is False
    rpc_cluster.rpc_call.assert_not_awaited()


async def test_shelly_input_cluster_refreshes_after_cached_state_window(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure older cached Shelly input state is refreshed over RPC."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    rpc_cluster.rpc_call = AsyncMock(return_value={"state": True})

    input_cluster.update_input_state(False)
    input_cluster._last_input_refresh = (
        asyncio.get_running_loop().time() - SHELLY_INPUT_REFRESH_MIN_INTERVAL - 0.1
    )
    await input_cluster.refresh_input_state()

    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is True
    rpc_cluster.rpc_call.assert_awaited_once_with(
        "Input.GetStatus",
        {"id": 0},
        accept_status_notification=True,
    )


async def test_shelly_input_cluster_reads_refresh_before_returning(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure input reads return the fresh RPC state instead of stale cache."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    input_cluster.update_input_state(False)

    async def refresh_input_state() -> None:
        input_cluster.update_input_state(True)

    input_cluster.refresh_input_state = AsyncMock(side_effect=refresh_input_state)

    assert await input_cluster.read_attributes(["present_value"]) == (
        {"present_value": True},
        {},
    )
    input_cluster.refresh_input_state.assert_awaited_once()


async def test_shelly_rpc_call_transports_json_frame(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure the Shelly RPC cluster writes and reads JSON-RPC frames."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    request_payload = json.dumps(
        {
            "id": 1,
            "src": "zha",
            "method": "Input.GetStatus",
            "params": {"id": 0},
        },
        separators=(",", ":"),
    )
    response_payload = json.dumps(
        {
            "id": 1,
            "src": "shellymini1pm",
            "dst": "zha",
            "result": {"state": True},
        },
        separators=(",", ":"),
    )
    rpc_cluster.write_attributes = AsyncMock()
    rpc_cluster.read_attributes = AsyncMock(
        side_effect=[
            ({"rx_ctl": len(response_payload)}, {}),
            ({"data": response_payload}, {}),
        ]
    )

    assert await rpc_cluster.rpc_call("Input.GetStatus", {"id": 0}) == {"state": True}
    assert rpc_cluster.write_attributes.await_args_list == [
        call(
            {"tx_ctl": len(request_payload)},
            manufacturer=SHELLY_MANUFACTURER_CODE,
            update_cache=False,
        ),
        *[
            call(
                {"data": request_payload[offset : offset + SHELLY_RPC_DATA_CHUNK_SIZE]},
                manufacturer=SHELLY_MANUFACTURER_CODE,
                update_cache=False,
            )
            for offset in range(0, len(request_payload), SHELLY_RPC_DATA_CHUNK_SIZE)
        ],
    ]
    assert rpc_cluster.read_attributes.await_args_list == [
        call(
            ["rx_ctl"],
            allow_cache=False,
            only_cache=False,
            manufacturer=SHELLY_MANUFACTURER_CODE,
        ),
        call(
            ["data"],
            allow_cache=False,
            only_cache=False,
            manufacturer=SHELLY_MANUFACTURER_CODE,
        ),
    ]


async def test_shelly_rpc_frame_uses_buffered_report_chunks(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure chunked RPC data reports are buffered while a call is active."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    response_payload = json.dumps(
        {
            "id": 1,
            "src": "shellymini1pm",
            "dst": "zha",
            "result": {"id": 0, "state": True},
        },
        separators=(",", ":"),
    )
    rpc_cluster._read_rx_ctl = AsyncMock(return_value=len(response_payload))
    rpc_cluster.read_attributes = AsyncMock()

    await rpc_cluster._rpc_lock.acquire()
    try:
        for offset in range(0, len(response_payload), SHELLY_RPC_DATA_CHUNK_SIZE):
            quirked.packet_received(
                t.ZigbeePacket(
                    profile_id=SHELLY_CUSTOM_PROFILE_ID,
                    cluster_id=SHELLY_RPC_CLUSTER_ID,
                    src_ep=SHELLY_CUSTOM_ENDPOINT_ID,
                    dst_ep=SHELLY_CUSTOM_ENDPOINT_ID,
                    data=t.SerializableBytes(
                        _attribute_report_data(
                            rpc_cluster.AttributeDefs.data,
                            t.CharacterString(
                                response_payload[
                                    offset : offset + SHELLY_RPC_DATA_CHUNK_SIZE
                                ]
                            ),
                        )
                    ),
                )
            )
    finally:
        rpc_cluster._rpc_lock.release()

    assert await rpc_cluster._read_rpc_frame(
        asyncio.get_running_loop().time() + 1
    ) == json.loads(response_payload)
    rpc_cluster.read_attributes.assert_not_awaited()


async def test_shelly_rpc_frame_uses_reported_chunks_before_rx_ctl_read(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure queued report chunks are decoded before polling RxCtl."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    response_payload = json.dumps(
        {
            "id": 1,
            "src": "shellymini1pm",
            "dst": "zha",
            "result": {"id": 0, "state": True},
        },
        separators=(",", ":"),
    )
    rpc_cluster.read_attributes = AsyncMock()

    for offset in range(0, len(response_payload), SHELLY_RPC_DATA_CHUNK_SIZE):
        rpc_cluster._queue_rpc_chunk(
            response_payload[offset : offset + SHELLY_RPC_DATA_CHUNK_SIZE]
        )

    assert await rpc_cluster._read_rpc_frame(
        asyncio.get_running_loop().time() + 1
    ) == json.loads(response_payload)
    rpc_cluster.read_attributes.assert_not_awaited()


async def test_shelly_rpc_frame_discards_incomplete_reported_chunks_before_polling(
    zigpy_device_from_v2_quirk, monkeypatch
) -> None:
    """Ensure stale partial report chunks are not accepted as the next response."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    stale_partial_payload = '","result":{"id":0,"state":true}}'
    response_payload = json.dumps(
        {
            "id": 1,
            "src": "shellymini1pm",
            "dst": "zha",
            "result": {"id": 0, "state": False},
        },
        separators=(",", ":"),
    )
    monkeypatch.setattr(
        "zhaquirks.shelly.zigbee.SHELLY_RPC_REPORTED_RESPONSE_GRACE_PERIOD", 0
    )
    rpc_cluster._queue_rpc_chunk(stale_partial_payload)
    rpc_cluster._read_rx_ctl = AsyncMock(return_value=len(response_payload))
    rpc_cluster.read_attributes = AsyncMock(
        return_value=({rpc_cluster.AttributeDefs.data.name: response_payload}, {})
    )

    assert await rpc_cluster._read_rpc_frame(
        asyncio.get_running_loop().time() + 1
    ) == json.loads(response_payload)
    rpc_cluster.read_attributes.assert_awaited_once_with(
        [rpc_cluster.AttributeDefs.data.name],
        allow_cache=False,
        only_cache=False,
        manufacturer=SHELLY_MANUFACTURER_CODE,
    )


async def test_shelly_rpc_response_ignores_unmatched_frames(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure RPC response reads skip unrelated frames."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    rpc_cluster._read_rpc_frame = AsyncMock(
        side_effect=[
            {"method": "NotifyStatus", "params": {"input:0": {"state": True}}},
            {"id": 1, "result": {"state": False}},
        ]
    )
    rpc_cluster._handle_rpc_frame = Mock()

    assert await rpc_cluster._read_rpc_response(1) == {"state": False}
    rpc_cluster._handle_rpc_frame.assert_called_once_with(
        {"method": "NotifyStatus", "params": {"input:0": {"state": True}}}
    )


async def test_shelly_rpc_response_accepts_recovered_result(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure a recovered result frame is accepted for the active RPC call."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    rpc_cluster._read_rpc_frame = AsyncMock(
        return_value={"result": {"id": 0, "state": True}}
    )

    assert await rpc_cluster._read_rpc_response(1) == {"id": 0, "state": True}


async def test_shelly_rpc_response_raises_rpc_error(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure RPC error frames raise a ShellyRpcError."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    rpc_cluster._read_rpc_frame = AsyncMock(
        return_value={"id": 1, "error": {"code": -105, "message": "Bad id"}}
    )

    with pytest.raises(ShellyRpcError):
        await rpc_cluster._read_rpc_response(1)


async def test_shelly_rpc_frame_read_failures(
    zigpy_device_from_v2_quirk, monkeypatch
) -> None:
    """Ensure RPC frame read failures are surfaced."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    monkeypatch.setattr(
        "zhaquirks.shelly.zigbee.SHELLY_RPC_REPORTED_RESPONSE_GRACE_PERIOD", 0
    )
    rpc_cluster._read_rx_ctl = AsyncMock(return_value=1)
    rpc_cluster.read_attributes = AsyncMock(return_value=({}, {}))

    with pytest.raises(TimeoutError, match="data read returned no data"):
        await rpc_cluster._read_rpc_frame()

    rpc_cluster._read_rx_ctl = AsyncMock(return_value=88)
    rpc_cluster.read_attributes = AsyncMock(
        return_value=(
            {
                rpc_cluster.AttributeDefs.data.name: (
                    ':"zha","result":{"id":0,"state":true}}'
                )
            },
            {},
        )
    )

    assert await rpc_cluster._read_rpc_frame() == {"result": {"id": 0, "state": True}}

    response_payload = json.dumps({"id": 1, "result": {"state": True}})
    rpc_cluster._read_rx_ctl = AsyncMock(return_value=len(response_payload))
    rpc_cluster.read_attributes = AsyncMock(
        side_effect=[
            ({"data": ""}, {}),
            ({"data": response_payload}, {}),
        ]
    )
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    assert await rpc_cluster._read_rpc_frame(asyncio.get_running_loop().time() + 1) == {
        "id": 1,
        "result": {"state": True},
    }
    asyncio.sleep.assert_awaited_once()

    rpc_cluster._read_rx_ctl = ShellyRpcCluster._read_rx_ctl.__get__(
        rpc_cluster, ShellyRpcCluster
    )
    rpc_cluster.read_attributes = AsyncMock(
        side_effect=[
            ({"rx_ctl": 0}, {}),
            ({"rx_ctl": 1}, {}),
        ]
    )
    assert await rpc_cluster._read_rx_ctl(asyncio.get_running_loop().time() + 1) == 1
    assert asyncio.sleep.await_count == 2

    rpc_cluster.read_attributes = AsyncMock(return_value=({"rx_ctl": 0}, {}))
    with pytest.raises(TimeoutError, match="waiting for Shelly RPC response"):
        await rpc_cluster._read_rx_ctl(asyncio.get_running_loop().time())


async def test_shelly_rpc_report_handlers(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure RPC report handling covers non-data reports and RxCtl reports."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]

    hdr = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Read_Attributes,
        manufacturer=SHELLY_MANUFACTURER_CODE,
    )
    rpc_cluster.handle_cluster_general_request(
        hdr,
        foundation.GENERAL_COMMANDS[foundation.GeneralCommand.Read_Attributes].schema(
            [rpc_cluster.AttributeDefs.rx_ctl.id]
        ),
    )

    hdr = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        manufacturer=SHELLY_MANUFACTURER_CODE,
        direction=foundation.Direction.Server_to_Client,
    )
    args = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema(
        [
            foundation.Attribute(
                attrid=rpc_cluster.AttributeDefs.rx_ctl.id,
                value=foundation.TypeValue(type=t.uint32_t, value=1),
            )
        ]
    )

    def close_task(coro):
        coro.close()

    rpc_cluster.create_catching_task = Mock(side_effect=close_task)
    rpc_cluster.handle_cluster_general_request(hdr, args)
    rpc_cluster.create_catching_task.assert_called_once()

    rpc_cluster._read_rpc_frame = AsyncMock(
        return_value={"method": "NotifyStatus", "params": {"input:0": {"state": True}}}
    )
    rpc_cluster._handle_rpc_frame = Mock()
    await rpc_cluster._read_and_dispatch_rpc_frame()
    rpc_cluster._handle_rpc_frame.assert_called_once()


def test_shelly_rpc_frame_ignores_invalid_notifications(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure invalid RPC notification shapes are ignored."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]

    for frame in (
        {"method": "NotifyEvent", "params": {"input:0": {"state": True}}},
        {"method": "NotifyStatus", "params": None},
        {"method": "NotifyStatus", "params": {0: {"state": True}}},
        {"method": "NotifyStatus", "params": {"input:0": None}},
        {"method": "NotifyStatus", "params": {"input:bad": {"state": True}}},
        {"method": "NotifyStatus", "params": {"input:1": {"state": True}}},
    ):
        rpc_cluster._handle_rpc_frame(frame)

    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is None


async def test_shelly_input_refresh_failures_are_tolerated(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure input refresh failures keep the virtual cluster readable."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    input_cluster.refresh_input_state = AsyncMock(side_effect=TimeoutError)

    assert await input_cluster.read_attributes(["present_value"]) == (
        {"present_value": None},
        {},
    )

    input_cluster.update_input_state("invalid")
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is None


async def test_shelly_input_refresh_failure_clears_stale_state(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure a failed refresh does not keep a stale active input latched."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    input_cluster.update_input_state(True)
    input_cluster.refresh_input_state = AsyncMock(side_effect=TimeoutError)

    assert await input_cluster.read_attributes(["present_value"]) == (
        {"present_value": None},
        {},
    )
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is None


async def test_shelly_input_refresh_missing_or_invalid_rpc_cluster(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure input refresh is tolerant of missing RPC support."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]

    quirked.endpoints.pop(SHELLY_CUSTOM_ENDPOINT_ID)
    await input_cluster.refresh_input_state()

    quirked.add_endpoint(SHELLY_CUSTOM_ENDPOINT_ID)
    quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[SHELLY_RPC_CLUSTER_ID] = (
        object()
    )
    await input_cluster.refresh_input_state()


async def test_shelly_rpc_notify_status_updates_input_cluster(
    zigpy_device_from_v2_quirk,
) -> None:
    """Ensure Shelly RPC status notifications update the virtual binary input."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        "Mini1PM",
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_RPC_CLUSTER_ID: ClusterType.Server,
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    rpc_cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_RPC_CLUSTER_ID
    ]
    input_cluster = quirked.endpoints[1].in_clusters[BinaryInput.cluster_id]
    payload = json.dumps(
        {
            "src": "shellymini1pm",
            "dst": "zha",
            "method": "NotifyStatus",
            "params": {"input:0": {"id": 0, "state": True}},
        },
        separators=(",", ":"),
    )

    quirked.packet_received(
        t.ZigbeePacket(
            profile_id=SHELLY_CUSTOM_PROFILE_ID,
            cluster_id=SHELLY_RPC_CLUSTER_ID,
            src_ep=SHELLY_CUSTOM_ENDPOINT_ID,
            dst_ep=SHELLY_CUSTOM_ENDPOINT_ID,
            data=t.SerializableBytes(
                _attribute_report_data(
                    rpc_cluster.AttributeDefs.data,
                    t.CharacterString(payload),
                )
            ),
        )
    )

    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.name) is True


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_custom_profile_packet_processed(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure Shelly custom profile packets are processed as ZCL for WiFi reads."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    cluster = quirked.endpoints[SHELLY_CUSTOM_ENDPOINT_ID].in_clusters[
        SHELLY_WIFI_SETUP_CLUSTER_ID
    ]

    async def deliver_packet() -> None:
        quirked.packet_received(
            t.ZigbeePacket(
                profile_id=SHELLY_CUSTOM_PROFILE_ID,
                cluster_id=SHELLY_WIFI_SETUP_CLUSTER_ID,
                src_ep=SHELLY_CUSTOM_ENDPOINT_ID,
                dst_ep=SHELLY_CUSTOM_ENDPOINT_ID,
                data=t.SerializableBytes(
                    _attribute_report_data(
                        cluster.AttributeDefs.status,
                        t.CharacterString("got ip"),
                    )
                ),
            )
        )

    asyncio.run(deliver_packet())

    assert cluster.get("status") == "got ip"


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_standard_profile_packet_delegated(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure standard ZHA profile packets fall through to normal zigpy parsing."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_CUSTOM_ENDPOINT_ID],
        cluster_ids={
            SHELLY_CUSTOM_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    # Standard ZHA profile packet should delegate to super()
    zha_packet = t.ZigbeePacket(
        profile_id=zha.PROFILE_ID,
        cluster_id=Basic.cluster_id,
        src_ep=1,
        dst_ep=1,
        data=t.SerializableBytes(
            _attribute_report_data(
                Basic.AttributeDefs.model,
                t.CharacterString("1PM"),
            )
        ),
    )

    hdr, rsp_key = quirked._parse_packet_header(zha_packet)

    assert hdr is not None
    assert rsp_key is not None
    assert rsp_key.endpoint_id == 1
    assert rsp_key.cluster_id == Basic.cluster_id
