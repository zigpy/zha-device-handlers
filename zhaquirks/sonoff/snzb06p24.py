"""Sonoff SNZB-06P24 - Zigbee presence sensor."""

import asyncio
import time
from typing import Any, Final, Union

import zigpy.types as t
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    BaseCommandDefs,
    foundation,
)
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster

SONOFF_CLUSTER_FC11_ID = 0xFC11

ATTR_SONOFF_ZONE_ENABLE = 0x2016
ATTR_SONOFF_LEARNING_STATE = 0x2017
ATTR_SONOFF_ILLUM_OFFSET = 0x2018
ATTR_SONOFF_FINE_TUNE_SENSITIVITY = 0x2021

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

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        zone_enable: Final = ZCLAttributeDef(
            id=ATTR_SONOFF_ZONE_ENABLE, type=t.bitmap16, manufacturer_code=None
        )
        learning_state: Final = ZCLAttributeDef(
            id=ATTR_SONOFF_LEARNING_STATE,
            type=SpatialLearningState,
            manufacturer_code=None,
        )
        illumination_offset: Final = ZCLAttributeDef(
            id=ATTR_SONOFF_ILLUM_OFFSET, type=t.int16s, manufacturer_code=None
        )
        fine_tune_sensitivity: Final = ZCLAttributeDef(
            id=ATTR_SONOFF_FINE_TUNE_SENSITIVITY, type=t.int8s, manufacturer_code=None
        )

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

    def __init__(self, *args, **kwargs):
        """Init and listen for zone mask changes."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReadEvent.event_type, self._handle_zone_change)
        self.on_event(AttributeReportedEvent.event_type, self._handle_zone_change)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_zone_change)
        self.on_event(AttributeWrittenEvent.event_type, self._handle_zone_change)

    def _handle_zone_change(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Sync the zone switches to the local cluster on mask change."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if event.attribute_id == self.AttributeDefs.zone_enable.id:
            self.endpoint.sonoff_presence_local.update_zones(event.value)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read the zone mask during pairing to populate the zone switches."""
        await self.read_attributes([self.AttributeDefs.zone_enable.id])

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
            self.endpoint.sonoff_presence_local.learning_requested()
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
            duration_sec = max(0, end_ts - start_ts) // 1000
            self.endpoint.sonoff_presence_local.learning_started(duration_sec)
        elif cmd_type == 0x02 and len(payload) >= 11:
            self.endpoint.sonoff_presence_local.learning_finished()


class SonoffSNZB06P24LocalCluster(LocalDataCluster):
    """Local cluster for the zone switches and spatial learning progress."""

    cluster_id = 0xFBFE
    ep_attribute = "sonoff_presence_local"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        zone_0_enable: Final = ZCLAttributeDef(id=0x1000, type=t.Bool)
        zone_2_enable: Final = ZCLAttributeDef(id=0x1002, type=t.Bool)
        zone_3_enable: Final = ZCLAttributeDef(id=0x1003, type=t.Bool)
        zone_4_enable: Final = ZCLAttributeDef(id=0x1004, type=t.Bool)
        zone_5_enable: Final = ZCLAttributeDef(id=0x1005, type=t.Bool)
        zone_6_enable: Final = ZCLAttributeDef(id=0x1006, type=t.Bool)
        zone_7_enable: Final = ZCLAttributeDef(id=0x1007, type=t.Bool)
        spatial_learning_ui_state: Final = ZCLAttributeDef(
            id=0x3010, type=SpatialLearningUiState
        )
        spatial_learning_countdown: Final = ZCLAttributeDef(id=0x3011, type=t.uint16_t)

    # Bits of the device zone mask, one per 0.5m band. Zone 1 covers the
    # first two bands.
    _ZONE_BITS: dict[int, int] = {
        AttributeDefs.zone_0_enable.id: 0x0003,
        AttributeDefs.zone_2_enable.id: 0x0004,
        AttributeDefs.zone_3_enable.id: 0x0008,
        AttributeDefs.zone_4_enable.id: 0x0010,
        AttributeDefs.zone_5_enable.id: 0x0020,
        AttributeDefs.zone_6_enable.id: 0x0040,
        AttributeDefs.zone_7_enable.id: 0x0080,
    }

    # Every zone is enabled out of the box. This is only shown until the
    # mask is read, writes always start from the mask read from the device.
    _DEFAULT_VALUES = {
        **dict.fromkeys(_ZONE_BITS, t.Bool.true),
        AttributeDefs.spatial_learning_ui_state.id: SpatialLearningUiState.IDLE,
        AttributeDefs.spatial_learning_countdown.id: 0,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._countdown_task: asyncio.Task | None = None
        self._timeout_task: asyncio.Task | None = None

    def update_zones(self, mask: int) -> None:
        """Update the zone switches from the device mask."""
        for attr_id, bits in self._ZONE_BITS.items():
            self._update_attribute(attr_id, bool(mask & bits))

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate zone switch writes into a mask write on the FC11 cluster."""
        zones = {}
        others = {}
        for attr, value in attributes.items():
            attr_id = self.find_attribute(attr).id
            if attr_id in self._ZONE_BITS:
                zones[attr_id] = value
            else:
                others[attr] = value

        records = []
        if others:
            records += (await super().write_attributes(others, **kwargs))[0]
        if zones:
            records += (await self._write_zones(zones, **kwargs))[0]
        return [records]

    async def _write_zones(
        self, zones: dict[int, Any], **kwargs
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        sonoff = self.endpoint.sonoff_manufacturer
        mask_attr = SonoffSNZB06P24FC11Cluster.AttributeDefs.zone_enable
        mask = sonoff.get(mask_attr.id)

        # Never write a guessed mask, it would change the other zones
        if mask is None:
            success, failure = await sonoff.read_attributes([mask_attr.id])
            if mask_attr.id not in success:
                status = failure.get(mask_attr.id, Status.FAILURE)
                return [[foundation.WriteAttributesStatusRecord(status, mask_attr.id)]]
            mask = success[mask_attr.id]

        mask = int(mask)
        for attr_id, value in zones.items():
            if value:
                mask |= self._ZONE_BITS[attr_id]
            else:
                mask &= ~self._ZONE_BITS[attr_id]

        return await sonoff.write_attributes({mask_attr.id: mask}, **kwargs)

    def learning_requested(self) -> None:
        """Show that spatial learning was requested."""
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.START,
        )
        self._update_attribute(self.AttributeDefs.spatial_learning_countdown.id, 0)

    def learning_started(self, duration: int) -> None:
        """Count down while the device learns, give up after a minute."""
        self._cancel_tasks()
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.COUNTDOWN,
        )
        self._countdown_task = asyncio.create_task(self._countdown(duration))
        self._timeout_task = asyncio.create_task(self._timeout())

    def learning_finished(self) -> None:
        """Return to idle once the device reports a result."""
        self._cancel_tasks()
        self._update_attribute(self.AttributeDefs.spatial_learning_countdown.id, 0)
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.IDLE,
        )

    def _cancel_tasks(self) -> None:
        for task in (self._countdown_task, self._timeout_task):
            if task is not None:
                task.cancel()

    async def _countdown(self, seconds: int) -> None:
        for remaining in range(seconds, 0, -1):
            self._update_attribute(
                self.AttributeDefs.spatial_learning_countdown.id, remaining
            )
            await asyncio.sleep(1)
        self._update_attribute(self.AttributeDefs.spatial_learning_countdown.id, 0)

    async def _timeout(self) -> None:
        await asyncio.sleep(60)
        if self._countdown_task is not None:
            self._countdown_task.cancel()
        self._update_attribute(self.AttributeDefs.spatial_learning_countdown.id, 0)
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.TIMEOUT,
        )
        await asyncio.sleep(5)
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.IDLE,
        )


SONOFF_SNZB06P24 = (
    QuirkBuilder("SONOFF", "SNZB-06P24")
    .replaces(SonoffSNZB06P24FC11Cluster)
    .adds(SonoffSNZB06P24LocalCluster)
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
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="spatial_learning_ui_state",
        fallback_name="Spatial learning state",
    )
    # Spatial Learning Countdown (virtual)
    .sensor(
        attribute_name="spatial_learning_countdown",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        unit=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        translation_key="spatial_learning_countdown",
        fallback_name="Spatial learning countdown",
    )
    # Zone 1-7 Enable (Switches) - Zone 1 combines 0-50cm + 50-100cm
    .switch(
        attribute_name="zone_0_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_0_enable",
        fallback_name="Zone 1 (0m-1m)",
    )
    .switch(
        attribute_name="zone_2_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_2_enable",
        fallback_name="Zone 2 (1m-1.5m)",
    )
    .switch(
        attribute_name="zone_3_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_3_enable",
        fallback_name="Zone 3 (1.5m-2m)",
    )
    .switch(
        attribute_name="zone_4_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_4_enable",
        fallback_name="Zone 4 (2m-2.5m)",
    )
    .switch(
        attribute_name="zone_5_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_5_enable",
        fallback_name="Zone 5 (2.5m-3m)",
    )
    .switch(
        attribute_name="zone_6_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_6_enable",
        fallback_name="Zone 6 (3m-3.5m)",
    )
    .switch(
        attribute_name="zone_7_enable",
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="zone_7_enable",
        fallback_name="Zone 7 (3.5m-4m)",
    )
    .add_to_registry()
)
