"""Sonoff SNZB-06P24 - Zigbee presence sensor."""

import asyncio
import time
from typing import Any, Final, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType, UnitOfTime
import zigpy.types as t
from zigpy.zcl import BaseCommandDefs, foundation

SONOFF_CLUSTER_FC11_ID = 0xFC11

ATTR_SONOFF_ZONE_ENABLE = 0x2016
ATTR_SONOFF_LEARNING_STATE = 0x2017
ATTR_SONOFF_ILLUM_OFFSET = 0x2018
ATTR_SONOFF_FINE_TUNE_SENSITIVITY = 0x2021
ATTR_SONOFF_SPATIAL_UI_STATE = 0x3010
ATTR_SONOFF_SPATIAL_COUNTDOWN = 0x3011

CMD_SPATIAL_LEARNING = 0x04
CMD_START_LEARNING_NOW = 0xFD


class SpatialLearningState(t.enum8):
    """Spatial learning state enum."""

    Idle = 0x00
    Learning = 0x01
    Success = 0x02
    Failure = 0x03


class SpatialLearningUiState(t.enum8):
    """Spatial learning UI state enum."""

    IDLE = 0x00
    START = 0x01
    COUNTDOWN = 0x02
    TIMEOUT = 0x03


class SonoffSNZB06P24FC11Cluster(CustomCluster):
    """Sonoff manufacturer specific cluster for SNZB-06P24."""

    cluster_id = SONOFF_CLUSTER_FC11_ID
    ep_attribute = "sonoff_manufacturer"

    attributes = {
        ATTR_SONOFF_ZONE_ENABLE: ("zone_enable", t.bitmap16),
        ATTR_SONOFF_LEARNING_STATE: ("learning_state", SpatialLearningState),
        ATTR_SONOFF_ILLUM_OFFSET: ("illumination_offset", t.int16s),
        ATTR_SONOFF_FINE_TUNE_SENSITIVITY: ("fine_tune_sensitivity", t.int8s),
        ATTR_SONOFF_SPATIAL_UI_STATE: (
            "spatial_learning_ui_state",
            SpatialLearningUiState,
        ),
        ATTR_SONOFF_SPATIAL_COUNTDOWN: (
            "spatial_learning_countdown",
            t.uint16_t,
        ),
    }

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        spatial_learning: Final = foundation.ZCLCommandDef(
            id=CMD_SPATIAL_LEARNING,
            schema={"param1": t.uint8_t, "param2": t.uint64_t},
        )
        start_learning_now: Final = foundation.ZCLCommandDef(
            id=CMD_START_LEARNING_NOW,
            schema={},
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        spatial_learning: Final = foundation.ZCLCommandDef(
            id=CMD_SPATIAL_LEARNING,
            schema={"param1": t.uint8_t, "param2": t.uint64_t},
        )

    # Virtual attributes for zone enabling (0x1000 - 0x1007)
    # These effectively map to bits 0-7 of ATTR_SONOFF_ZONE_ENABLE (0x2016)
    attributes.update({0x1000 + i: (f"zone_{i}_enable", t.Bool) for i in range(8)})

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._spatial_countdown_task: asyncio.Task | None = None
        self._spatial_timeout_task: asyncio.Task | None = None
        self._last_spatial_start_ts_ms: int | None = None
        self._update_attribute(
            ATTR_SONOFF_SPATIAL_UI_STATE, SpatialLearningUiState.IDLE
        )
        self._update_attribute(ATTR_SONOFF_SPATIAL_COUNTDOWN, 0)

    def request(
        self,
        general_command: bool,
        command_id: Union[int, t.uint8_t],
        schema: Any,
        *args,
        manufacturer: int | None = None,
        expect_reply: bool = True,
        tsn: int | None = None,
        **kwargs,
    ):
        """Override request to handle virtual start_learning_now."""
        if not general_command and (
            command_id == CMD_START_LEARNING_NOW or command_id == "start_learning_now"
        ):
            # 0, timestamp_ms (little endian handled by uint64 type)
            timestamp_ms = int(time.time() * 1000)
            args = (0, timestamp_ms)
            command_id = CMD_SPATIAL_LEARNING
            manufacturer = 0x1286
            self._last_spatial_start_ts_ms = timestamp_ms
            self._set_spatial_ui_state(SpatialLearningUiState.START)
            self._set_spatial_countdown(0)
            # Retrieve schema for 0x04
            cmd_def = self.server_commands.get(CMD_SPATIAL_LEARNING)
            if cmd_def is not None:
                if hasattr(cmd_def, "schema"):
                    schema = cmd_def.schema
                elif isinstance(cmd_def, (tuple, list)) and len(cmd_def) > 1:
                    schema = cmd_def[1]

        return super().request(
            general_command,
            command_id,
            schema,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )

    def deserialize(self, data: bytes):
        """Deserialize cluster data with custom spatial learning parsing."""
        hdr, payload = foundation.ZCLHeader.deserialize(data)

        if (
            hdr.frame_control.frame_type == foundation.FrameType.CLUSTER_COMMAND
            and hdr.command_id == CMD_SPATIAL_LEARNING
        ):
            self._handle_spatial_learning_payload(bytes(payload))
            return hdr, []

        return super().deserialize(hdr.serialize() + payload)

    def _handle_spatial_learning_payload(self, payload: bytes) -> None:
        """Handle incoming spatial learning command payloads."""
        if not payload:
            return

        cmd_type = payload[0]

        if cmd_type == 0x01 and len(payload) >= 17:
            start_ts = int.from_bytes(payload[1:9], "little")
            end_ts = int.from_bytes(payload[9:17], "little")
            self._last_spatial_start_ts_ms = start_ts

            duration_ms = max(0, end_ts - start_ts)
            duration_sec = int(duration_ms // 1000)

            self._set_spatial_ui_state(SpatialLearningUiState.COUNTDOWN)
            self._start_spatial_countdown(duration_sec)
            self._start_spatial_timeout()
        elif cmd_type == 0x02 and len(payload) >= 11:
            self._stop_spatial_tasks()
            self._set_spatial_countdown(0)
            self._set_spatial_ui_state(SpatialLearningUiState.IDLE)

    def _set_spatial_ui_state(self, state: SpatialLearningUiState) -> None:
        self._update_attribute(ATTR_SONOFF_SPATIAL_UI_STATE, state)

    def _set_spatial_countdown(self, seconds: int) -> None:
        self._update_attribute(ATTR_SONOFF_SPATIAL_COUNTDOWN, max(0, int(seconds)))

    def _stop_spatial_tasks(self) -> None:
        if self._spatial_countdown_task and not self._spatial_countdown_task.done():
            self._spatial_countdown_task.cancel()
        if self._spatial_timeout_task and not self._spatial_timeout_task.done():
            self._spatial_timeout_task.cancel()

    def _start_spatial_countdown(self, seconds: int) -> None:
        if self._spatial_countdown_task and not self._spatial_countdown_task.done():
            self._spatial_countdown_task.cancel()
        self._spatial_countdown_task = asyncio.create_task(
            self._spatial_countdown_worker(seconds)
        )

    async def _spatial_countdown_worker(self, seconds: int) -> None:
        remaining = max(0, int(seconds))
        self._set_spatial_countdown(remaining)
        while remaining > 0:
            await asyncio.sleep(1)
            remaining -= 1
            self._set_spatial_countdown(remaining)

    def _start_spatial_timeout(self) -> None:
        if self._spatial_timeout_task and not self._spatial_timeout_task.done():
            self._spatial_timeout_task.cancel()
        self._spatial_timeout_task = asyncio.create_task(self._spatial_timeout_worker())

    async def _spatial_timeout_worker(self) -> None:
        await asyncio.sleep(60)
        if self._spatial_countdown_task and not self._spatial_countdown_task.done():
            self._spatial_countdown_task.cancel()
        self._set_spatial_countdown(0)
        self._set_spatial_ui_state(SpatialLearningUiState.TIMEOUT)
        await asyncio.sleep(5)
        self._set_spatial_ui_state(SpatialLearningUiState.IDLE)

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Intercept read_attributes to handle virtual zone switches."""
        virtual_attrs = set()
        real_attributes = []

        requested_ids = set()

        for a in attributes:
            aid = a
            if isinstance(a, str):
                if a in self.attributes_by_name:
                    aid = self.attributes_by_name[a].id

            requested_ids.add(aid)
            if isinstance(aid, int) and 0x1000 <= aid <= 0x1007:
                virtual_attrs.add(aid)
            else:
                real_attributes.append(a)

        if not virtual_attrs:
            return await super().read_attributes(
                attributes, allow_cache, only_cache, manufacturer
            )

        # Ensure we read the bitmap if we need it for virtual attributes
        if ATTR_SONOFF_ZONE_ENABLE not in requested_ids:
            real_attributes.append(ATTR_SONOFF_ZONE_ENABLE)

        success, failure = await super().read_attributes(
            real_attributes, allow_cache, only_cache, manufacturer
        )

        if ATTR_SONOFF_ZONE_ENABLE in success:
            bitmap_val = success[ATTR_SONOFF_ZONE_ENABLE]
            for v_id in virtual_attrs:
                idx = v_id - 0x1000
                if idx == 0:
                    val = bool(bitmap_val & 0x03)
                else:
                    val = bool(bitmap_val & (1 << idx))
                success[v_id] = t.Bool(val)
                self._update_attribute(v_id, t.Bool(val))

        if ATTR_SONOFF_ZONE_ENABLE in failure:
            err = failure[ATTR_SONOFF_ZONE_ENABLE]
            for v_id in virtual_attrs:
                failure[v_id] = err

        # Remove bitmap if not requested (by ID or name)
        if ATTR_SONOFF_ZONE_ENABLE not in requested_ids:
            # Also check if user requested it by name "zone_enable"
            # But we only track IDs in requested_ids.
            # If 0x2016 isn't in requested_ids, we pop it.
            success.pop(ATTR_SONOFF_ZONE_ENABLE, None)
            failure.pop(ATTR_SONOFF_ZONE_ENABLE, None)

        return success, failure

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Intercept write_attributes to handle virtual zone switches."""

        virtual_updates = {}
        real_attributes = {}

        for attr, value in attributes.items():
            attr_id = attr
            if isinstance(attr, str):
                if attr in self.attributes_by_name:
                    attr_id = self.attributes_by_name[attr].id

            # Check if it is one of our virtual attributes (0x1000 - 0x1007)
            if isinstance(attr_id, int) and 0x1000 <= attr_id <= 0x1007:
                zone_idx = attr_id - 0x1000
                virtual_updates[zone_idx] = value
            else:
                real_attributes[attr] = value

        if virtual_updates:
            # We need the current mask to update specific bits
            current_mask = self._attr_cache.get(ATTR_SONOFF_ZONE_ENABLE)

            if current_mask is None:
                # Attempt to read if not in cache
                try:
                    read_res = await self.read_attributes(
                        [ATTR_SONOFF_ZONE_ENABLE], manufacturer=manufacturer
                    )
                    if ATTR_SONOFF_ZONE_ENABLE in read_res[0]:
                        current_mask = read_res[0][ATTR_SONOFF_ZONE_ENABLE]
                    else:
                        current_mask = 0x00
                except Exception:
                    # Fallback if read fails
                    current_mask = 0x00

            # Calculate new mask
            new_mask = current_mask
            for idx, state in virtual_updates.items():
                if idx == 0:
                    if state:
                        new_mask |= 0x03
                    else:
                        new_mask &= ~0x03
                elif idx == 1 and 0 in virtual_updates:
                    continue
                elif state:
                    new_mask |= 1 << idx
                else:
                    new_mask &= ~(1 << idx)

            real_attributes[ATTR_SONOFF_ZONE_ENABLE] = new_mask

            # Optimistically update virtual attributes in cache
            for idx, state in virtual_updates.items():
                if idx == 0:
                    self._update_attribute(0x1000, t.Bool(state))
                    self._update_attribute(0x1001, t.Bool(state))
                else:
                    self._update_attribute(0x1000 + idx, t.Bool(state))

        # Perform the actual write
        res = await super().write_attributes(real_attributes, manufacturer)

        # Normalize response records.
        if isinstance(res, list):
            if res and isinstance(res[0], list):
                records = res[0]
            else:
                records = res
        elif hasattr(res, "status_records"):
            records = res.status_records
        else:
            records = [res]

        # Check if the bitmap write was successful
        bitmap_status = foundation.Status.SUCCESS

        for record in records:
            if isinstance(record, foundation.WriteAttributesStatusRecord):
                if record.attrid == ATTR_SONOFF_ZONE_ENABLE:
                    bitmap_status = record.status
                    break

        # Generate records for virtual updates
        if virtual_updates:
            for idx in virtual_updates:
                v_attr_id = 0x1000 + idx
                # If bitmap write failed, report failure for virtual attrs too
                records.append(
                    foundation.WriteAttributesStatusRecord(bitmap_status, v_attr_id)
                )

        return [records]

    def _update_attribute(self, attrid, value):
        """Update attribute value in cache and push to listeners."""
        super()._update_attribute(attrid, value)

        # When the real mask is updated (e.g. report from device), update the virtual attributes
        if attrid == ATTR_SONOFF_ZONE_ENABLE and isinstance(value, int):
            for i in range(8):
                if i == 0:
                    is_on = bool(value & 0x03)
                else:
                    is_on = bool(value & (1 << i))
                super()._update_attribute(0x1000 + i, t.Bool(is_on))


SONOFF_SNZB06P24 = (
    QuirkBuilder("SONOFF", "SNZB-06P24")
    .replaces(SonoffSNZB06P24FC11Cluster)
    # Illumination Offset (Cluster 0xFC11, Attr 0x2018)
    .number(
        attribute_name="illumination_offset",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        min_value=-1000,
        max_value=1000,
        step=1,
        mode="box",
        translation_key="illumination_offset",
        fallback_name="Illumination offset",
    )
    # Fine-tune Sensitivity (Cluster 0xFC11, Attr 0x2021)
    .number(
        attribute_name="fine_tune_sensitivity",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        min_value=-6,
        max_value=6,
        step=1,
        mode="slider",
        translation_key="fine_tune_sensitivity",
        fallback_name="Fine-tune Sensitivity",
    )
    # Spatial Learning Button
    # Cmd 0x04, SubCmd=0 (Start), Sequence=timestamp_ms
    .command_button(
        command_name="start_learning_now",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        command_args=(),
        translation_key="spatial_learning",
        fallback_name="Start spatial learning",
    )
    # Spatial Learning UI State (virtual)
    .enum(
        attribute_name="spatial_learning_ui_state",
        enum_class=SpatialLearningUiState,
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="spatial_learning_ui_state",
        fallback_name="Spatial learning state",
    )
    # Spatial Learning Countdown (virtual)
    .sensor(
        attribute_name="spatial_learning_countdown",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        unit=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        translation_key="spatial_learning_countdown",
        fallback_name="Spatial learning countdown",
    )
    # Zone 1-7 Enable (Switches) - Zone 1 combines 0-50cm + 50-100cm
    .switch(
        attribute_name="zone_0_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_0_enable",
        fallback_name="Zone 1 (0m-1m)",
    )
    .switch(
        attribute_name="zone_2_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_2_enable",
        fallback_name="Zone 2 (1m-1.5m)",
    )
    .switch(
        attribute_name="zone_3_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_3_enable",
        fallback_name="Zone 3 (1.5m-2m)",
    )
    .switch(
        attribute_name="zone_4_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_4_enable",
        fallback_name="Zone 4 (2m-2.5m)",
    )
    .switch(
        attribute_name="zone_5_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_5_enable",
        fallback_name="Zone 5 (2.5m-3m)",
    )
    .switch(
        attribute_name="zone_6_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_6_enable",
        fallback_name="Zone 6 (3m-3.5m)",
    )
    .switch(
        attribute_name="zone_7_enable",
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_7_enable",
        fallback_name="Zone 7 (3.5m-4m)",
    )
    .add_to_registry()
)
