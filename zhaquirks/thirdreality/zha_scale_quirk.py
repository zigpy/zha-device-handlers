"""Third Reality Zigbee kitchen scale."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)


class ThirdRealityScaleCluster(CustomCluster):
    """Third Reality kitchen scale private cluster."""

    cluster_id = 0xFF0C

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the scale cluster."""

        SCALE_VAL: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.int16s,
            is_manufacturer_specific=False,
        )

        DISPLAY_VAL: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.int16s,
            is_manufacturer_specific=False,
        )

        PRIVATE_STATUS: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            is_manufacturer_specific=False,
        )
        PRIVATE_UNIT: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            is_manufacturer_specific=False,
        )

        TARGET_VAL: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
            is_manufacturer_specific=False,
        )

    # Track current unit: 0=g, 1=lb:oz
    _current_unit = 0

    def _update_attribute(self, attrid, value):
        """Convert DISPLAY_VAL to lb:oz format string when in oz mode."""
        if attrid == 0x0004:
            self._current_unit = value

        if attrid == 0x0002:
            if self._current_unit == 1:
                # In oz mode: firmware already divided by 10
                # value is total_oz * 10 integer (e.g. 247 = 24.7oz = 1lb 8.7oz)
                total_oz_x10 = value  # e.g. 247
                lb = total_oz_x10 // 160  # 1lb = 16oz, so 160 tenth-oz
                remaining_oz_x10 = total_oz_x10 - lb * 160
                oz = remaining_oz_x10 / 10.0
                formatted = f"{lb}lb {oz:.1f}oz"
                super()._update_attribute(attrid, formatted)
                return

        super()._update_attribute(attrid, value)

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions for the scale cluster."""

        tare: Final = ZCLCommandDef(
            id=0x00,
            schema={},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )
        start_report: Final = ZCLCommandDef(
            id=0x01,
            schema={},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )
        stop_report: Final = ZCLCommandDef(
            id=0x02,
            schema={},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )
        set_target_val: Final = ZCLCommandDef(
            id=0x03,
            schema={"target_val": t.uint8_t},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )
        convert_gram_to_pound_ounce: Final = ZCLCommandDef(
            id=0x04,
            schema={},
            direction=foundation.Direction.Client_to_Server,
            is_manufacturer_specific=False,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RKS030Z")
    .replaces(ThirdRealityScaleCluster)
    .sensor(
        ThirdRealityScaleCluster.AttributeDefs.SCALE_VAL.name,
        ThirdRealityScaleCluster.cluster_id,
        unit="g",
        translation_key="scale_weight",
        fallback_name="Weight",
    )
    .sensor(
        ThirdRealityScaleCluster.AttributeDefs.DISPLAY_VAL.name,
        ThirdRealityScaleCluster.cluster_id,
        translation_key="scale_weight_lb_oz",
        fallback_name="Weight_pound_ounce",
    )
    .command_button(
        ThirdRealityScaleCluster.ServerCommandDefs.tare.name,
        ThirdRealityScaleCluster.cluster_id,
        translation_key="scale_tare",
        fallback_name="Tare_(Zero)",
    )
    .command_button(
        ThirdRealityScaleCluster.ServerCommandDefs.start_report.name,
        ThirdRealityScaleCluster.cluster_id,
        translation_key="scale_start_report",
        fallback_name="Start_Report",
    )
    .command_button(
        ThirdRealityScaleCluster.ServerCommandDefs.stop_report.name,
        ThirdRealityScaleCluster.cluster_id,
        translation_key="scale_stop_report",
        fallback_name="Stop_Report",
    )
    .number(
        ThirdRealityScaleCluster.AttributeDefs.TARGET_VAL.name,
        ThirdRealityScaleCluster.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="set_target_val",
        fallback_name="Set_Target_Val",
    )
    .command_button(
        ThirdRealityScaleCluster.ServerCommandDefs.convert_gram_to_pound_ounce.name,
        ThirdRealityScaleCluster.cluster_id,
        translation_key="scale_convert_unit",
        fallback_name="Convert_(Gram_Pound_Ounce)",
    )
    .add_to_registry()
)
