"""Aqara Curtain Driver E1 device."""

from __future__ import annotations

from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    LocalIlluminanceMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfigurationPercent,
)

HAND_OPEN = 0x0401
POSITIONS_STORED = 0x0402
STORE_POSITION = 0x0407
HOOKS_LOCK = 0x0427
HOOKS_STATE = 0x0428
LIGHT_LEVEL = 0x0429


class XiaomiAqaraDriverE1(XiaomiAqaraE1Cluster):
    """Xiaomi Aqara Curtain Driver E1 cluster."""

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            HAND_OPEN: ("hand_open", t.Bool, True),
            POSITIONS_STORED: ("positions_stored", t.Bool, True),
            STORE_POSITION: ("store_position", t.uint8_t, True),
            HOOKS_LOCK: ("hooks_lock", t.uint8_t, True),
            HOOKS_STATE: ("hooks_state", t.uint8_t, True),
            LIGHT_LEVEL: ("light_level", t.uint8_t, True),
        }
    )

    def _update_attribute(self, attrid, value):
        if attrid == LIGHT_LEVEL:
            # Light level value seems like it can be 0, 1, or 2.
            # Multiply by 50 to map those values to later show: 1 lx, 50 lx, 100 lx.
            self.endpoint.illuminance.update_attribute(
                IlluminanceMeasurement.AttributeDefs.measured_value.id,
                value * 50,
            )
        super()._update_attribute(attrid, value)


class WindowCoveringE1(CustomCluster, WindowCovering):
    """Xiaomi Window Covering cluster that maps open/close to lift percentage."""

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Overwrite the open/close commands to call the lift percentage command instead."""
        if command_id == WindowCovering.ServerCommandDefs.up_open.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (0,)
        elif command_id == WindowCovering.ServerCommandDefs.down_close.id:
            command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
            args = (100,)

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


class DriverE1(XiaomiCustomDevice):
    """Aqara Curtain Driver E1 device."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.agl001")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=263
            # device_version=1
            # input_clusters=[0, 1, 3, 10, 258, 64704]
            # output_clusters=[3, 10, 25, 64704]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    WindowCovering.cluster_id,
                    XiaomiAqaraDriverE1.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    XiaomiAqaraDriverE1.cluster_id,
                ],
            }
        },
    }
    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfigurationPercent,
                    Identify.cluster_id,
                    Time.cluster_id,
                    WindowCoveringE1,
                    LocalIlluminanceMeasurementCluster,
                    XiaomiAqaraDriverE1,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }
