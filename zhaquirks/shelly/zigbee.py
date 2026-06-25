"""Shelly Gen4 Zigbee RPC and input support."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from zigpy.device import ResponseKey
import zigpy.types as t
from zigpy.zcl import ClusterType, ReportingConfig, foundation
from zigpy.zcl.clusters.general import BinaryInput, OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import EventableCluster, LocalDataCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.shelly import (
    SHELLY_CUSTOM_ENDPOINT_ID,
    SHELLY_CUSTOM_PROFILE_ID,
    SHELLY_INPUT_REFRESH_MIN_INTERVAL,
    SHELLY_INPUT_REFRESH_TIMEOUT,
    SHELLY_MANUFACTURER_CODE,
    SHELLY_RPC_CLUSTER_ID,
    SHELLY_RPC_DATA_CHUNK_SIZE,
    SHELLY_RPC_REPORTED_RESPONSE_GRACE_PERIOD,
    SHELLY_RPC_RESPONSE_POLL_INTERVAL,
    SHELLY_RPC_RESPONSE_TIMEOUT,
    SHELLY_RPC_SOURCE,
)
from zhaquirks.shelly.wifi import ShellyWiFiSetupCluster


class ShellyRpcError(Exception):
    """Shelly RPC call failed."""


class ShellyRpcCluster(CustomCluster):
    """Shelly RPC cluster."""

    cluster_id = SHELLY_RPC_CLUSTER_ID
    name = "Shelly RPC"
    ep_attribute = "shelly_rpc"

    class AttributeDefs(BaseAttributeDefs):
        """Shelly RPC attribute definitions."""

        data = ZCLAttributeDef(
            id=0x0000,
            type=t.CharacterString,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        tx_ctl = ZCLAttributeDef(
            id=0x0001,
            type=t.uint32_t,
            access="w",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        rx_ctl = ZCLAttributeDef(
            id=0x0002,
            type=t.uint32_t,
            access="r",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Shelly RPC cluster."""
        super().__init__(*args, **kwargs)
        self._rpc_lock = asyncio.Lock()
        self._rpc_request_id = 0
        self._rpc_rx_chunks: list[str] = []

    def _next_rpc_request_id(self) -> int:
        """Return the next JSON-RPC request id."""
        self._rpc_request_id = (self._rpc_request_id % 0x7FFFFFFF) + 1
        return self._rpc_request_id

    async def apply_custom_configuration(self, *args: Any, **kwargs: Any) -> None:
        """Bind the RPC cluster and enable pending-frame reports."""
        await self.bind()
        await self.configure_reporting_multiple(
            {
                self.AttributeDefs.rx_ctl: ReportingConfig(
                    min_interval=0,
                    max_interval=900,
                    reportable_change=1,
                )
            }
        )

    async def rpc_call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        accept_status_notification: bool = False,
    ) -> Any:
        """Call a Shelly RPC method over the Zigbee RPC cluster."""
        request_id = self._next_rpc_request_id()
        frame: dict[str, Any] = {
            "id": request_id,
            "src": SHELLY_RPC_SOURCE,
            "method": method,
        }
        if params is not None:
            frame["params"] = params

        async with self._rpc_lock:
            self._rpc_rx_chunks.clear()
            await self._write_rpc_frame(frame)
            return await self._read_rpc_response(
                request_id,
                accept_status_notification=accept_status_notification,
            )

    async def _write_rpc_frame(self, frame: dict[str, Any]) -> None:
        """Write a JSON-RPC frame to the Shelly RPC cluster."""
        payload = json.dumps(frame, separators=(",", ":"), ensure_ascii=True)

        await self.write_attributes(
            {self.AttributeDefs.tx_ctl.name: len(payload)},
            manufacturer=SHELLY_MANUFACTURER_CODE,
            update_cache=False,
        )
        for offset in range(0, len(payload), SHELLY_RPC_DATA_CHUNK_SIZE):
            await self.write_attributes(
                {
                    self.AttributeDefs.data.name: payload[
                        offset : offset + SHELLY_RPC_DATA_CHUNK_SIZE
                    ]
                },
                manufacturer=SHELLY_MANUFACTURER_CODE,
                update_cache=False,
            )

    async def _read_rpc_response(
        self,
        request_id: int,
        *,
        accept_status_notification: bool = False,
    ) -> Any:
        """Read RPC frames until the matching response frame is received."""
        deadline = asyncio.get_running_loop().time() + SHELLY_RPC_RESPONSE_TIMEOUT

        while True:
            frame = await self._read_rpc_frame(deadline)
            if frame.get("id") != request_id:
                if "id" not in frame and "result" in frame:
                    return frame.get("result")

                handled = self._handle_rpc_frame(frame)
                if accept_status_notification and handled:
                    return None
                continue

            if "error" in frame:
                raise ShellyRpcError(frame["error"])

            return frame.get("result")

    async def _read_rpc_frame(self, deadline: float | None = None) -> dict[str, Any]:
        """Read one JSON-RPC frame from the Shelly RPC cluster."""
        if deadline is None:
            deadline = asyncio.get_running_loop().time() + SHELLY_RPC_RESPONSE_TIMEOUT

        frame_bytes = await self._read_reported_rpc_frame(deadline)
        frame = self._decode_reported_rpc_frame(frame_bytes)
        if frame is not None:
            return frame

        frame_bytes = b""
        frame_len = await self._read_rx_ctl(deadline)

        while len(frame_bytes) < frame_len:
            if self._rpc_rx_chunks:
                frame_bytes += self._rpc_rx_chunks.pop(0).encode()
                frame = self._decode_reported_rpc_frame(frame_bytes)
                if frame is not None:
                    return frame
                continue

            now = asyncio.get_running_loop().time()
            if now >= deadline:
                raise TimeoutError("Timed out waiting for Shelly RPC data")

            success, _ = await self._read_rpc_attributes(
                [self.AttributeDefs.data.name],
                deadline,
                "Timed out waiting for Shelly RPC data",
            )
            chunk = success.get(self.AttributeDefs.data.name)
            if chunk is None:
                raise TimeoutError("Shelly RPC data read returned no data")

            chunk_bytes = str(chunk).encode()
            if not chunk_bytes:
                now = asyncio.get_running_loop().time()
                if now >= deadline:
                    raise TimeoutError("Timed out waiting for Shelly RPC data")

                await asyncio.sleep(
                    min(SHELLY_RPC_RESPONSE_POLL_INTERVAL, deadline - now)
                )
                continue

            frame_bytes += chunk_bytes
            if len(frame_bytes) < frame_len:
                partial_frame = self._decode_partial_rpc_frame(frame_bytes)
                if partial_frame is not None:
                    return partial_frame

        return json.loads(frame_bytes[:frame_len].decode())

    async def _read_reported_rpc_frame(self, deadline: float) -> bytes:
        """Read a frame delivered as attribute reports, if reports arrive promptly."""
        frame_bytes = b""
        report_deadline = min(
            deadline,
            asyncio.get_running_loop().time()
            + SHELLY_RPC_REPORTED_RESPONSE_GRACE_PERIOD,
        )

        while True:
            while self._rpc_rx_chunks:
                frame_bytes += self._rpc_rx_chunks.pop(0).encode()
                if self._decode_reported_rpc_frame(frame_bytes) is not None:
                    return frame_bytes

            now = asyncio.get_running_loop().time()
            if now >= deadline or now >= report_deadline:
                return frame_bytes

            await asyncio.sleep(min(SHELLY_RPC_RESPONSE_POLL_INTERVAL, deadline - now))

    def _decode_reported_rpc_frame(self, frame_bytes: bytes) -> dict[str, Any] | None:
        """Decode a complete RPC frame from reported chunks."""
        if not frame_bytes:
            return None

        try:
            return json.loads(frame_bytes.decode())
        except json.JSONDecodeError:
            return None

    def _decode_partial_rpc_frame(self, frame_bytes: bytes) -> dict[str, Any] | None:
        """Recover a trailing JSON-RPC result if leading chunks were missed."""
        payload = frame_bytes.decode(errors="ignore")
        result_index = payload.find('"result":')
        if result_index == -1:
            return None

        try:
            return json.loads("{" + payload[result_index:])
        except json.JSONDecodeError:
            return None

    async def _read_rpc_attributes(
        self,
        attributes: list[str],
        deadline: float,
        timeout_message: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read Shelly RPC attributes without exceeding the frame deadline."""
        now = asyncio.get_running_loop().time()
        if now >= deadline:
            raise TimeoutError(timeout_message)

        try:
            return await asyncio.wait_for(
                self.read_attributes(
                    attributes,
                    allow_cache=False,
                    only_cache=False,
                    manufacturer=SHELLY_MANUFACTURER_CODE,
                ),
                timeout=deadline - now,
            )
        except TimeoutError as exc:
            raise TimeoutError(timeout_message) from exc

    def _queue_rpc_chunk(self, payload: str) -> None:
        """Queue a reported RPC data chunk for the active frame reader."""
        if payload:
            self._rpc_rx_chunks.append(payload)

    async def _read_rx_ctl(self, deadline: float) -> int:
        """Read RxCtl until a frame is available or the timeout expires."""
        while True:
            success, _ = await self._read_rpc_attributes(
                [self.AttributeDefs.rx_ctl.name],
                deadline,
                "Timed out waiting for Shelly RPC response",
            )
            frame_len = success.get(self.AttributeDefs.rx_ctl.name, 0)
            if frame_len:
                return int(frame_len)

            now = asyncio.get_running_loop().time()
            if now >= deadline:
                raise TimeoutError("Timed out waiting for Shelly RPC response")

            await asyncio.sleep(min(SHELLY_RPC_RESPONSE_POLL_INTERVAL, deadline - now))

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle RPC frame reports."""
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)

        if hdr.command_id != foundation.GeneralCommand.Report_Attributes:
            return

        for attr in args.attribute_reports:
            if attr.attrid == self.AttributeDefs.data.id:
                payload = str(attr.value.value)
                if self._rpc_lock.locked():
                    self._queue_rpc_chunk(payload)
                    continue

                try:
                    self._handle_rpc_payload(payload)
                except json.JSONDecodeError:
                    self._queue_rpc_chunk(payload)
            elif (
                attr.attrid == self.AttributeDefs.rx_ctl.id
                and attr.value.value
                and not self._rpc_lock.locked()
            ):
                self.create_catching_task(self._read_and_dispatch_rpc_frame())

    async def _read_and_dispatch_rpc_frame(self) -> None:
        """Read and dispatch a pending unsolicited RPC frame."""
        async with self._rpc_lock:
            self._handle_rpc_frame(await self._read_rpc_frame())

    def _handle_rpc_payload(self, payload: str) -> None:
        """Handle a raw JSON-RPC payload from the device."""
        self._handle_rpc_frame(json.loads(payload))

    def _handle_rpc_frame(self, frame: dict[str, Any]) -> bool:
        """Handle Shelly RPC notifications that carry input state."""
        if frame.get("method") != "NotifyStatus":
            return False

        params = frame.get("params")
        if not isinstance(params, dict):
            return False

        handled = False
        for component, status in params.items():
            if not isinstance(component, str) or not component.startswith("input:"):
                continue
            if not isinstance(status, dict) or "state" not in status:
                continue

            try:
                input_id = int(component.removeprefix("input:"))
            except ValueError:
                continue

            self._update_input_state(input_id, status["state"])
            handled = True

        return handled

    def _update_input_state(self, input_id: int, state: bool | None) -> None:
        """Update a virtual Shelly input cluster with a new state."""
        endpoint = self.endpoint.device.endpoints.get(input_id + 1)
        if endpoint is None:
            return

        cluster = endpoint.in_clusters.get(BinaryInput.cluster_id)
        if isinstance(cluster, ShellyInputCluster):
            cluster.update_input_state(state)


class ShellyInputCluster(LocalDataCluster, BinaryInput):
    """Virtual Shelly input binary cluster."""

    _CONSTANT_ATTRIBUTES = {
        BinaryInput.AttributeDefs.description.id: "Input",
        BinaryInput.AttributeDefs.out_of_service.id: False,
        BinaryInput.AttributeDefs.status_flags.id: 0,
    }
    _VALID_ATTRIBUTES = {BinaryInput.AttributeDefs.present_value.id}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the virtual Shelly input cluster."""
        super().__init__(*args, **kwargs)
        self._last_input_refresh: float | None = None

    @property
    def input_id(self) -> int:
        """Return the Shelly input id for this endpoint."""
        return self.endpoint.endpoint_id - 1

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Refresh input state before serving BinaryInput present_value reads."""
        if BinaryInput.AttributeDefs.present_value.id in attributes:
            await self._refresh_input_state_catching()

        return await super().read_attributes_raw(
            attributes, manufacturer=manufacturer, **kwargs
        )

    async def _refresh_input_state_catching(self) -> None:
        """Refresh input state while keeping read paths tolerant of RPC failures."""
        try:
            await self.refresh_input_state()
        except (TimeoutError, ShellyRpcError, json.JSONDecodeError):
            self.update_input_state(None)
            self.debug("Could not refresh Shelly input state", exc_info=True)

    async def refresh_input_state(self) -> None:
        """Read the current Shelly input state over RPC."""
        loop = asyncio.get_running_loop()
        last_refresh = self._last_input_refresh
        if (
            last_refresh is not None
            and self.get(BinaryInput.AttributeDefs.present_value.name) is not None
            and loop.time() - last_refresh < SHELLY_INPUT_REFRESH_MIN_INTERVAL
        ):
            return

        try:
            rpc_cluster = self.endpoint.device.endpoints[
                SHELLY_CUSTOM_ENDPOINT_ID
            ].in_clusters[SHELLY_RPC_CLUSTER_ID]
        except KeyError:
            return

        if not isinstance(rpc_cluster, ShellyRpcCluster):
            return

        deadline = loop.time() + SHELLY_INPUT_REFRESH_TIMEOUT
        async with asyncio.timeout_at(deadline):
            status = await rpc_cluster.rpc_call(
                "Input.GetStatus",
                {"id": self.input_id},
                accept_status_notification=True,
            )

        if isinstance(status, dict):
            self.update_input_state(status.get("state"))

    def update_input_state(self, state: Any) -> None:
        """Update the cached BinaryInput present_value."""
        if state is not None and not isinstance(state, bool):
            return

        self._update_attribute(BinaryInput.AttributeDefs.present_value.id, state)
        if state is None:
            self._last_input_refresh = None
            return

        try:
            self._last_input_refresh = asyncio.get_running_loop().time()
        except RuntimeError:
            self._last_input_refresh = None


class ShellyInputOnOffCluster(EventableCluster, OnOff):
    """Map Shelly 2.0 input commands to the virtual binary input."""

    def _update_input_state(self, state: bool) -> None:
        """Forward an input state update to the virtual binary input."""
        input_endpoint = self.endpoint.device.endpoints.get(1)
        if input_endpoint is None:
            return

        input_cluster = input_endpoint.in_clusters.get(BinaryInput.cluster_id)
        if isinstance(input_cluster, ShellyInputCluster):
            input_cluster.update_input_state(state)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Forward current-firmware On/Off attribute updates."""
        super()._update_attribute(attrid, value)

        if attrid == OnOff.AttributeDefs.on_off.id and value in (False, True, 0, 1):
            self._update_input_state(bool(value))

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Update input state from the firmware's On/Off client commands."""
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

        if hdr.command_id == OnOff.ServerCommandDefs.on.id:
            self._update_input_state(True)
        elif hdr.command_id == OnOff.ServerCommandDefs.off.id:
            self._update_input_state(False)
        elif hdr.command_id == OnOff.ServerCommandDefs.toggle.id:
            input_endpoint = self.endpoint.device.endpoints.get(1)
            if input_endpoint is None:
                return
            input_cluster = input_endpoint.in_clusters.get(BinaryInput.cluster_id)
            if not isinstance(input_cluster, ShellyInputCluster):
                return
            current_state = input_cluster.get(
                BinaryInput.AttributeDefs.present_value.name
            )
            if isinstance(current_state, bool):
                input_cluster.update_input_state(not current_state)


class ShellyCustomProfileDevice(CustomZigpyDevice):
    """Handle Shelly responses sent on their custom endpoint profile."""

    def _parse_packet_header(
        self, packet: t.ZigbeePacket
    ) -> tuple[foundation.ZCLHeader, ResponseKey] | tuple[None, None]:
        """Parse Shelly custom-profile packets as ZCL for normal zigpy matching."""
        if packet.profile_id != SHELLY_CUSTOM_PROFILE_ID:
            return super()._parse_packet_header(packet)

        hdr, _ = foundation.ZCLHeader.deserialize(packet.data.serialize())
        rsp_key = ResponseKey(
            endpoint_id=packet.src_ep,
            cluster_id=packet.cluster_id,
            direction=hdr.frame_control.direction,
            tsn=hdr.tsn,
        )
        return hdr, rsp_key


(
    QuirkBuilder("Shelly", "1PM")
    .applies_to("Shelly", "Mini1PM")
    .applies_to("Shelly", "Mini1")
    .device_class(ShellyCustomProfileDevice)
    .replaces(ShellyRpcCluster, endpoint_id=SHELLY_CUSTOM_ENDPOINT_ID)
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_CUSTOM_ENDPOINT_ID)
    .adds(ShellyInputCluster, endpoint_id=1)
    .replaces(
        ShellyInputOnOffCluster,
        endpoint_id=2,
        cluster_type=ClusterType.Client,
    )
    .add_to_registry()
)

(
    QuirkBuilder("Shelly", "2PM")
    .applies_to("Shelly", "EM Mini")
    .device_class(ShellyCustomProfileDevice)
    .replaces(ShellyRpcCluster, endpoint_id=SHELLY_CUSTOM_ENDPOINT_ID)
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_CUSTOM_ENDPOINT_ID)
    .add_to_registry()
)
