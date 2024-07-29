"""Quirks common helpers."""

import asyncio
import datetime

ZCL_IAS_MOTION_COMMAND = b"\t!\x00\x01\x00\x00\x00\x00\x00"
ZCL_OCC_ATTR_RPT_OCC = b"\x18d\n\x00\x00\x18\x01"


class ClusterListener:
    """Generic cluster listener."""

    def __init__(self, cluster):
        """Init instance."""
        self.cluster_commands = []
        self.attribute_updates = []
        cluster.add_listener(self)

    def attribute_updated(self, attr_id, value, timestamp):
        """Attribute updated listener."""
        self.attribute_updates.append((attr_id, value))

    def cluster_command(self, tsn, command_id, args):
        """Command received listener."""
        self.cluster_commands.append((tsn, command_id, args))


class MockDatetime(datetime.datetime):
    """Override for datetime functions."""

    @classmethod
    def now(cls):
        """Return testvalue."""

        return cls(1970, 1, 1, 1, 0, 0)

    @classmethod
    def utcnow(cls):
        """Return testvalue."""

        return cls(1970, 1, 1, 2, 0, 0)


async def wait_for_zigpy_tasks() -> None:
    """Wait for all running zigpy tasks to finish."""
    tasks = []

    for task in asyncio.all_tasks():
        coro = task.get_coro()

        # TODO: track tasks within zigpy
        if "CatchingTaskMixin" in coro.__qualname__:
            tasks.append(task)

    await asyncio.gather(*tasks)
