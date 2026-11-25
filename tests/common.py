"""Quirks common helpers."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

from zha.application.platforms.event import EntityEventTriggeredEvent, ZhaEventButton
from zha.application.platforms.light import Light
from zha.zigbee.device import ZigbeeDevice
import zigpy.device
import zigpy.profiles.zha
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    ClusterType,
    foundation,
)
from zigpy.zcl.helpers import AttributeCacheLoadResult, AttributeCacheRow

ZCL_IAS_MOTION_COMMAND = b"\t!\x00\x01\x00\x00\x00\x00\x00"
ZCL_OCC_ATTR_RPT_OCC = b"\x18d\n\x00\x00\x18\x01"


class ClusterListener:
    """Generic cluster listener."""

    def __init__(self, cluster):
        """Init instance."""
        self.cluster_commands = []
        self.attribute_updates = []
        cluster.add_listener(self)
        cluster.on_event(AttributeReportedEvent.event_type, self._on_attribute_event)
        cluster.on_event(AttributeUpdatedEvent.event_type, self._on_attribute_event)
        cluster.on_event(AttributeWrittenEvent.event_type, self._on_attribute_written)
        cluster.on_event(AttributeReadEvent.event_type, self._on_attribute_read)

    def _on_attribute_event(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ):
        """Handle attribute report/update event."""
        self.attribute_updates.append((event.attribute_id, event.value))

    def _on_attribute_written(self, event: AttributeWrittenEvent):
        """Handle attribute written event (only for successful writes)."""
        if event.status == foundation.Status.SUCCESS:
            self.attribute_updates.append((event.attribute_id, event.value))

    def _on_attribute_read(self, event: AttributeReadEvent):
        """Handle attribute read event."""
        self.attribute_updates.append((event.attribute_id, event.value))

    def cluster_command(self, tsn, command_id, args):
        """Command received listener."""
        self.cluster_commands.append((tsn, command_id, args))


async def wait_for_zigpy_tasks() -> None:
    """Wait for all running zigpy tasks to finish."""
    tasks = []

    for task in asyncio.all_tasks():
        coro = task.get_coro()

        # TODO: track tasks within zigpy
        if "CatchingTaskMixin" in coro.__qualname__:
            tasks.append(task)

    await asyncio.gather(*tasks)


def attribute_cache_row(
    device,
    cluster_id: int,
    attr_id: int,
    value: Any,
    data_type: foundation.DataTypeId | None = None,
    *,
    endpoint_id: int = 1,
    manufacturer_code: int | None = None,
    last_updated: float = 0,
) -> AttributeCacheRow:
    """Build a server cluster attribute row as zigpy loads it from its database."""
    return AttributeCacheRow(
        ieee=device.ieee,
        endpoint_id=endpoint_id,
        cluster_type=ClusterType.Server,
        cluster_id=cluster_id,
        attr_id=attr_id,
        manufacturer_code=manufacturer_code,
        status=foundation.Status.SUCCESS,
        value=value,
        data_type=data_type,
        last_updated=last_updated,
    )


def deleted_rows(result: AttributeCacheLoadResult) -> list[AttributeCacheRow]:
    """Return the rows a load deleted from the attribute table, such as migrated ones."""
    return [change.old for change in result.changes if change.new is None]


class ButtonEventRecorder:
    """Create the ZHA device of a quirked device and record its button events.

    Create it with `await ButtonEventRecorder.create(device)`. Entities are keyed by
    their unique ID suffix.
    """

    def __init__(self, zha_device: ZigbeeDevice) -> None:
        """Start recording the button events of a ZHA device's entities."""
        self.zha_device = zha_device
        self.entities: dict[str, ZhaEventButton] = {}
        self.events: list[tuple[str, str, dict[str, Any]]] = []

        for entity in zha_device.platform_entities.values():
            if not isinstance(entity, ZhaEventButton):
                continue

            suffix = entity.unique_id.removeprefix(f"{entity.endpoint.unique_id}-")
            assert suffix not in self.entities, f"Duplicate entity suffix {suffix}"
            self.entities[suffix] = entity
            entity.on_event(
                EntityEventTriggeredEvent.event,
                lambda event, suffix=suffix: self.events.append(
                    (
                        suffix,
                        event.triggered.event_type,
                        event.triggered.event_attributes,
                    )
                ),
            )

    @classmethod
    async def create(cls, zigpy_device: zigpy.device.Device) -> ButtonEventRecorder:
        """Create the ZHA device and add its entities like ZHA does, then record."""
        # Entities start background tasks, such as polling, through the gateway,
        # which is mocked here: don't run them
        gateway = MagicMock()
        gateway.async_create_background_task.side_effect = (
            lambda coro, *args, **kwargs: coro.close()
        )
        zha_device = ZigbeeDevice.new(zigpy_device, gateway)

        # A light logs the polling interval its polling task sets when it starts
        with patch.object(Light, "start_polling"):
            zha_device._discover_new_entities()
            await zha_device._add_pending_entities(emit_event=False)
        return cls(zha_device)

    def event_types(self) -> dict[str, list[str]]:
        """Return the event types of each button event entity."""
        return {suffix: entity.event_types for suffix, entity in self.entities.items()}

    def pop(self) -> list[tuple[str, str] | tuple[str, str, dict[str, Any]]]:
        """Return the events recorded so far, without empty attributes, and clear them."""
        events = [
            (suffix, event_type, attributes) if attributes else (suffix, event_type)
            for suffix, event_type, attributes in self.events
        ]
        self.events.clear()
        return events
