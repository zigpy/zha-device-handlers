"""Aqara Curtain Controller C3 (ZNCLDJ01LM)."""

from __future__ import annotations

from typing import Any, Final

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import AQARA, BasicCluster, XiaomiAqaraE1Cluster


class AqaraCurtainC3Control(t.enum8):
    """Aqara C3 curtain control command values."""

    Stop = 0x00
    Toggle = 0x03
    Open = 0x07
    Close = 0x08


class XiaomiAqaraCurtainC3(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the Curtain Controller C3."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        positions_stored: Final = ZCLAttributeDef(
            id=0x0402,
            type=t.Bool,
            access="rp",
            is_manufacturer_specific=True,
        )

        traverse_time: Final = ZCLAttributeDef(
            id=0x0403,
            type=t.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        store_position: Final = ZCLAttributeDef(
            id=0x0407,
            type=t.uint8_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        control: Final = ZCLAttributeDef(
            id=0x0420,
            type=AqaraCurtainC3Control,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        curtain_position: Final = ZCLAttributeDef(
            id=0x041F,
            type=t.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        curtain_state: Final = ZCLAttributeDef(
            id=0x0421,
            type=t.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        last_manual_operation: Final = ZCLAttributeDef(
            id=0x0425,
            type=t.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        calibration_status: Final = ZCLAttributeDef(
            id=0x0426,
            type=t.uint8_t,
            access="rp",
            is_manufacturer_specific=True,
        )

        hand_open: Final = ZCLAttributeDef(
            id=0x043A,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

        speed: Final = ZCLAttributeDef(
            id=0x043B,
            type=t.uint8_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        adaptive_pulling_speed: Final = ZCLAttributeDef(
            id=0x0442,
            type=t.uint8_t,
            access="rwp",
            is_manufacturer_specific=True,
        )

        aqara_attributes: Final = ZCLAttributeDef(
            id=0x00F7,
            type=t.LVBytes,
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        """Handle attribute updates and sync position to WindowCovering cluster."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.curtain_position.id:
            self.endpoint.window_covering.update_attribute(
                WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                value,
            )


class WindowCoveringC3(CustomCluster, WindowCovering):
    """Window covering cluster for the Curtain Controller C3.

    Maps open/close commands to go_to_lift_percentage so the device
    handles inversion correctly based on window_covering_mode.
    """

    _CONSTANT_ATTRIBUTES = {
        WindowCovering.AttributeDefs.window_covering_type.id: WindowCovering.WindowCoveringType.Drapery,
    }

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ) -> Any:
        """Map open/close commands to go_to_lift_percentage."""
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
    QuirkBuilder(AQARA, "lumi.curtain.acn04")
    .replaces(BasicCluster)
    .replaces(WindowCoveringC3)
    .replaces(XiaomiAqaraCurtainC3)
    .switch(
        XiaomiAqaraCurtainC3.AttributeDefs.hand_open.name,
        XiaomiAqaraCurtainC3.cluster_id,
        translation_key="hand_open",
        fallback_name="Hand open",
    )
    .switch(
        WindowCovering.AttributeDefs.window_covering_mode.name,
        WindowCovering.cluster_id,
        translation_key="reverse_direction",
        fallback_name="Reverse direction",
    )
    .number(
        XiaomiAqaraCurtainC3.AttributeDefs.speed.name,
        XiaomiAqaraCurtainC3.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        translation_key="speed",
        fallback_name="Speed",
    )
    .binary_sensor(
        XiaomiAqaraCurtainC3.AttributeDefs.positions_stored.name,
        XiaomiAqaraCurtainC3.cluster_id,
        translation_key="calibrated",
        fallback_name="Calibrated",
    )
    .sensor(
        XiaomiAqaraCurtainC3.AttributeDefs.traverse_time.name,
        XiaomiAqaraCurtainC3.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="traverse_time",
        fallback_name="Traverse time",
    )
    .add_to_registry()
)
