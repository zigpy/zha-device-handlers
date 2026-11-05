"""Aqara Curtain Driver E1 device.

Travel limits are calibrated through attribute 0x0407 on the manufacturer
cluster: 0 clears the stored limits, 1 stores the current position as the closed
limit and 2 as the open limit. Use each value only at its own end.

To calibrate: park the curtain at either end, clear, store that end, then drive
to the opposite end. The motor stores the second limit itself when it hits the
stop. The `positions_stored` attribute reports the result.
"""

from __future__ import annotations

from typing import Any, Final

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import CustomCluster
from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    LocalIlluminanceMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfigurationPercent,
)

HAND_OPEN = 0x0401
POSITIONS_STORED = 0x0402
STORE_POSITION = 0x0407
HOOKS_LOCK = 0x0427
HOOKS_STATE = 0x0428
LIGHT_LEVEL = 0x0429

CLEAR_LIMITS = 0x00
STORE_CLOSED_LIMIT = 0x01
STORE_OPEN_LIMIT = 0x02


class XiaomiAqaraDriverE1(XiaomiAqaraE1Cluster):
    """Xiaomi Aqara Curtain Driver E1 cluster."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        hand_open: Final = ZCLAttributeDef(
            id=HAND_OPEN, type=t.Bool, is_manufacturer_specific=True
        )
        positions_stored: Final = ZCLAttributeDef(
            id=POSITIONS_STORED, type=t.Bool, is_manufacturer_specific=True
        )
        store_position: Final = ZCLAttributeDef(
            id=STORE_POSITION, type=t.uint8_t, is_manufacturer_specific=True
        )
        hooks_lock: Final = ZCLAttributeDef(
            id=HOOKS_LOCK, type=t.uint8_t, is_manufacturer_specific=True
        )
        hooks_state: Final = ZCLAttributeDef(
            id=HOOKS_STATE, type=t.uint8_t, is_manufacturer_specific=True
        )
        light_level: Final = ZCLAttributeDef(
            id=LIGHT_LEVEL, type=t.uint8_t, is_manufacturer_specific=True
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


(
    QuirkBuilder(LUMI, "lumi.curtain.agl001")
    .friendly_name(manufacturer="Aqara", model="Curtain Driver E1")
    .node_descriptor(
        NodeDescriptor(0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00)
    )
    .replaces_endpoint(1, device_type=zha.DeviceType.WINDOW_COVERING_DEVICE)
    .replaces(BasicCluster)
    .replaces(XiaomiPowerConfigurationPercent)
    .replaces(WindowCoveringE1)
    .replaces(XiaomiAqaraDriverE1)
    .adds(LocalIlluminanceMeasurementCluster)
    .removes(XiaomiAqaraDriverE1.cluster_id, cluster_type=ClusterType.Client)
    .write_attr_button(
        XiaomiAqaraDriverE1.AttributeDefs.store_position.name,
        CLEAR_LIMITS,
        XiaomiAqaraDriverE1.cluster_id,
        unique_id_suffix="limits_clear",
        translation_key="limits_clear",
        fallback_name="Clear travel limits",
    )
    .write_attr_button(
        XiaomiAqaraDriverE1.AttributeDefs.store_position.name,
        STORE_CLOSED_LIMIT,
        XiaomiAqaraDriverE1.cluster_id,
        unique_id_suffix="limit_set_closed",
        translation_key="limit_set_closed",
        fallback_name="Store closed limit",
    )
    .write_attr_button(
        XiaomiAqaraDriverE1.AttributeDefs.store_position.name,
        STORE_OPEN_LIMIT,
        XiaomiAqaraDriverE1.cluster_id,
        unique_id_suffix="limit_set_open",
        translation_key="limit_set_open",
        fallback_name="Store open limit",
    )
    .binary_sensor(
        XiaomiAqaraDriverE1.AttributeDefs.positions_stored.name,
        XiaomiAqaraDriverE1.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="limits_stored",
        fallback_name="Travel limits stored",
    )
    .switch(
        XiaomiAqaraDriverE1.AttributeDefs.hand_open.name,
        XiaomiAqaraDriverE1.cluster_id,
        translation_key="hand_open",
        fallback_name="Pull to start motor",
    )
    .switch(
        XiaomiAqaraDriverE1.AttributeDefs.hooks_lock.name,
        XiaomiAqaraDriverE1.cluster_id,
        translation_key="hooks_lock",
        fallback_name="Hooks locked",
    )
    .add_to_registry()
)
