"""Sonoff SNZB-06P24 - Zigbee presence sensor."""

import asyncio
import time
from typing import Any, Final

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


class SpatialLearningState(t.enum8):
    """Spatial learning state enum."""

    Idle = 0x00
    Learning = 0x01
    Success = 0x02
    Failure = 0x03


class SpatialLearningSubCommand(t.enum8):
    """Spatial learning sub commands."""

    Start = 0x00
    Started = 0x01
    Result = 0x02


class SpatialLearningUiState(t.enum8):
    """Spatial learning UI state enum."""

    Idle = 0x00
    Start = 0x01
    Countdown = 0x02
    Timeout = 0x03


class SonoffSNZB06P24FC11Cluster(CustomCluster):
    """Sonoff manufacturer specific cluster for SNZB-06P24."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_manufacturer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        zone_enable: Final = ZCLAttributeDef(
            id=0x2016, type=t.bitmap16, manufacturer_code=None
        )
        learning_state: Final = ZCLAttributeDef(
            id=0x2017, type=SpatialLearningState, manufacturer_code=None
        )
        illumination_offset: Final = ZCLAttributeDef(
            id=0x2018, type=t.int16s, manufacturer_code=None
        )
        fine_tune_sensitivity: Final = ZCLAttributeDef(
            id=0x2021, type=t.int8s, manufacturer_code=None
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        # The device answers with the same command and direction, followed
        # by the expected end time or the result
        spatial_learning: Final = foundation.ZCLCommandDef(
            id=0x04,
            schema={
                "sub_command": SpatialLearningSubCommand,
                "sequence": t.uint64_t,
                "data?": t.Bytes,
            },
        )
        # Not sent as is, see command()
        start_learning_now: Final = foundation.ZCLCommandDef(id=0xFD, schema={})

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

    async def command(self, command_id, *args, **kwargs):
        """Send start_learning_now as a spatial learning start request."""
        if command_id != self.ServerCommandDefs.start_learning_now.id:
            return await super().command(command_id, *args, **kwargs)

        local = self.endpoint.sonoff_presence_local
        local.learning_requested()

        # The reply echoes the sequence next to the expected end time of the
        # learning, both in ms, so the sequence has to be the current time
        try:
            response = await super().command(
                self.ServerCommandDefs.spatial_learning.id,
                SpatialLearningSubCommand.Start,
                int(time.time() * 1000),
                **kwargs,
            )
        except (Exception, asyncio.CancelledError):
            local.learning_finished()
            raise

        if getattr(response, "status", Status.SUCCESS) != Status.SUCCESS:
            local.learning_finished()
        return response

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ):
        """Track the spatial learning progress reported by the device."""
        if (
            hdr.direction != foundation.Direction.Client_to_Server
            or hdr.command_id != self.ServerCommandDefs.spatial_learning.id
        ):
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
            return

        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        local = self.endpoint.sonoff_presence_local
        if args.sub_command == SpatialLearningSubCommand.Started:
            # Expected end time, in ms like the sequence we sent
            if args.data is not None and len(args.data) >= 8:
                end_time = int.from_bytes(args.data[:8], "little")
                local.learning_started(max(0, end_time - args.sequence) // 1000)
        elif args.sub_command == SpatialLearningSubCommand.Result:
            local.learning_finished()


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
        AttributeDefs.spatial_learning_ui_state.id: SpatialLearningUiState.Idle,
        AttributeDefs.spatial_learning_countdown.id: 0,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._countdown_task: asyncio.Task | None = None
        self._timeout_task: asyncio.Task | None = None
        self._zone_write_lock = asyncio.Lock()
        self._zone_mask_needs_read = False

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
            # Keep concurrent switch changes from overwriting each other's bits.
            async with self._zone_write_lock:
                records += (await self._write_zones(zones, **kwargs))[0]
        return [records]

    async def _write_zones(
        self, zones: dict[int, Any], **kwargs
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        sonoff = self.endpoint.sonoff_manufacturer
        mask_attr = SonoffSNZB06P24FC11Cluster.AttributeDefs.zone_enable
        mask = sonoff.get(mask_attr.id)

        # Never write a guessed mask, it would change the other zones
        if mask is None or self._zone_mask_needs_read:
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

        # An interrupted write may have reached the device; an uncached write
        # deliberately leaves the cached mask stale. Read it before the next edit.
        self._zone_mask_needs_read = True
        response = await sonoff.write_attributes({mask_attr.id: mask}, **kwargs)
        self._zone_mask_needs_read = not kwargs.get("update_cache", True)
        return response

    def learning_requested(self) -> None:
        """Show that spatial learning was requested, until the device answers."""
        self._cancel_tasks()
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.Start,
        )
        self._update_attribute(self.AttributeDefs.spatial_learning_countdown.id, 0)
        self._timeout_task = asyncio.create_task(self._timeout())

    def learning_started(self, duration: int) -> None:
        """Count down while the device learns, give up after a minute."""
        self._cancel_tasks()
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.Countdown,
        )
        self._countdown_task = asyncio.create_task(self._countdown(duration))
        self._timeout_task = asyncio.create_task(self._timeout())

    def learning_finished(self) -> None:
        """Return to idle once the device reports a result."""
        self._cancel_tasks()
        self._update_attribute(self.AttributeDefs.spatial_learning_countdown.id, 0)
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.Idle,
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
            SpatialLearningUiState.Timeout,
        )
        await asyncio.sleep(5)
        self._update_attribute(
            self.AttributeDefs.spatial_learning_ui_state.id,
            SpatialLearningUiState.Idle,
        )


(
    QuirkBuilder("SONOFF", "SNZB-06P24")
    .replaces(SonoffSNZB06P24FC11Cluster)
    .adds(SonoffSNZB06P24LocalCluster)
    .number(
        attribute_name=SonoffSNZB06P24FC11Cluster.AttributeDefs.illumination_offset.name,
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        min_value=-1000,
        max_value=1000,
        step=1,
        mode="box",
        translation_key="illumination_offset",
        fallback_name="Illumination offset",
    )
    .number(
        attribute_name=SonoffSNZB06P24FC11Cluster.AttributeDefs.fine_tune_sensitivity.name,
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        min_value=-6,
        max_value=6,
        step=1,
        mode="slider",
        translation_key="fine_tune_sensitivity",
        fallback_name="Fine-tune sensitivity",
    )
    .command_button(
        command_name=SonoffSNZB06P24FC11Cluster.ServerCommandDefs.start_learning_now.name,
        cluster_id=SonoffSNZB06P24FC11Cluster.cluster_id,
        translation_key="spatial_learning",
        fallback_name="Start spatial learning",
    )
    .enum(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.spatial_learning_ui_state.name,
        enum_class=SpatialLearningUiState,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="spatial_learning_ui_state",
        fallback_name="Spatial learning state",
    )
    .sensor(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.spatial_learning_countdown.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        unit=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        translation_key="spatial_learning_countdown",
        fallback_name="Spatial learning countdown",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_0_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_0_enable",
        fallback_name="Zone 1 (0m-1m)",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_2_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_2_enable",
        fallback_name="Zone 2 (1m-1.5m)",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_3_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_3_enable",
        fallback_name="Zone 3 (1.5m-2m)",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_4_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_4_enable",
        fallback_name="Zone 4 (2m-2.5m)",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_5_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_5_enable",
        fallback_name="Zone 5 (2.5m-3m)",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_6_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_6_enable",
        fallback_name="Zone 6 (3m-3.5m)",
    )
    .switch(
        attribute_name=SonoffSNZB06P24LocalCluster.AttributeDefs.zone_7_enable.name,
        cluster_id=SonoffSNZB06P24LocalCluster.cluster_id,
        translation_key="zone_7_enable",
        fallback_name="Zone 7 (3.5m-4m)",
    )
    .add_to_registry()
)
