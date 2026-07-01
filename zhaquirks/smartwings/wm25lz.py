"""Device handler for Smartwings blinds."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


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


class WM25LBlinds(CustomDevice):
    """Custom device representing Smartwings WM25LZ blinds."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=514
        # device_version=1
        # input_clusters=[0, 1, 3, 4, 5, 258]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            ("Smartwings", "WM25/L-Z"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    InvertedWindowCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
