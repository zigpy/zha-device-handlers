"""Quirks common helpers."""

import asyncio
from typing import Any

from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
    ClusterType,
    foundation,
)
from zigpy.zcl.helpers import AttributeCacheRow

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
