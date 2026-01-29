"""Device handler for Smartwings blinds."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks import DoublingPowerConfigurationCluster


class InvertedWindowCoveringCluster(CustomCluster, WindowCovering):
    """WindowCovering cluster implementation that inverts the commands for up and down."""

    CMD_UP_OPEN = WindowCovering.commands_by_name["up_open"].id
    CMD_DOWN_CLOSE = WindowCovering.commands_by_name["down_close"].id

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Coroutine:
        """Override default commands for up and down. They need to be backwards."""
        # swap up and down commands
        if command_id == self.CMD_UP_OPEN:
            command_id = self.CMD_DOWN_CLOSE
        elif command_id == self.CMD_DOWN_CLOSE:
            command_id = self.CMD_UP_OPEN

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


(
    QuirkBuilder("Smartwings", "WM25/L-Z")
    .replaces(DoublingPowerConfigurationCluster, endpoint_id=1)
    .replaces(InvertedWindowCoveringCluster, endpoint_id=1)
    .add_to_registry()
)
