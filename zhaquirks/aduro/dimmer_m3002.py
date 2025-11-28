"""AduroSmart M3002 dimmer devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef


class LoadControlMode(t.enum8):
    """Load control modes for AduroSmart devices."""

    LeadingEdgeControl = 0x00
    TrailingEdgeControl = 0x01


class SwitchMode(t.enum8):
    """Switch modes for AduroSmart devices."""

    MomentarySwitch = 0x00
    ToggleSwitch = 0x01
    RollerBlindSwitch = 0x02


class DoubleClickScene(t.enum8):
    """Double click scenes for AduroSmart devices."""

    Disabled = 0x00
    On = 0x01
    Off = 0x02
    DimmingUp = 0x03
    DimmingDown = 0x04
    DimmingToBrightest = 0x05
    DimmingToDarkest = 0x06


class AduroDimmerBasicCluster(CustomCluster, Basic):
    """Aduro Dimmer Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        load_control_mode: Final = ZCLAttributeDef(
            id=0x7600,
            type=t.uint8_t,
            access="rw",
        )

        switch_mode: Final = ZCLAttributeDef(
            id=0x7700,
            type=t.uint8_t,
            access="rw",
        )

        invert_switch: Final = ZCLAttributeDef(
            id=0x7701,
            type=t.Bool,
            access="rw",
        )

        scene_activation: Final = ZCLAttributeDef(
            id=0x7702,
            type=t.Bool,
            access="rw",
        )

        s1_double_click_scene: Final = ZCLAttributeDef(
            id=0x7703,
            type=t.uint8_t,
            access="rw",
        )

        s2_double_click_scene: Final = ZCLAttributeDef(
            id=0x7704,
            type=t.uint8_t,
            access="rw",
        )

        min_brightness_level: Final = ZCLAttributeDef(
            id=0x7800,
            type=t.uint8_t,
            access="rw",
        )

        max_brightness_level: Final = ZCLAttributeDef(
            id=0x7801,
            type=t.uint8_t,
            access="rw",
        )

        manual_dimming_step_size: Final = ZCLAttributeDef(
            id=0x7802,
            type=t.uint8_t,
            access="rw",
        )

        manual_dimming_time: Final = ZCLAttributeDef(
            id=0x7803,
            type=t.uint16_t,
            access="rw",
        )


(
    QuirkBuilder("AduroSmart ERIA", "DimmerM3002")
    .applies_to("Robb Smarrt", "DimmerM3002")
    .replaces(AduroDimmerBasicCluster)
    .enum(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.load_control_mode.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        enum_class=LoadControlMode,
        translation_key="load_control_mode",
        fallback_name="Load Control Mode",
    )
    .enum(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.switch_mode.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        enum_class=SwitchMode,
        translation_key="switch_mode",
        fallback_name="Switch Mode",
    )
    .switch(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.invert_switch.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        translation_key="invert_switch",
        fallback_name="Invert Switch",
    )
    .switch(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.scene_activation.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        translation_key="scene_activation",
        fallback_name="Scene Activation",
    )
    .enum(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.s1_double_click_scene.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        enum_class=DoubleClickScene,
        translation_key="s1_double_click_scene",
        fallback_name="S1 Double Click Scene",
    )
    .enum(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.s2_double_click_scene.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        enum_class=DoubleClickScene,
        translation_key="s2_double_click_scene",
        fallback_name="S2 Double Click Scene",
    )
    .number(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.min_brightness_level.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="min_brightness_level",
        fallback_name="Min Brightness Level",
        mode="box",
    )
    .number(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.max_brightness_level.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="max_brightness_level",
        fallback_name="Max Brightness Level",
        mode="box",
    )
    .number(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.manual_dimming_step_size.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        min_value=1,
        max_value=25,
        step=1,
        unit=PERCENTAGE,
        translation_key="manual_dimming_step_size",
        fallback_name="Manual Dimming Step Size",
        mode="box",
    )
    .number(
        attribute_name=AduroDimmerBasicCluster.AttributeDefs.manual_dimming_time.name,
        cluster_id=AduroDimmerBasicCluster.cluster_id,
        min_value=100,
        max_value=10000,
        step=100,
        unit=UnitOfTime.MILLISECONDS,
        translation_key="manual_dimming_time",
        fallback_name="Manual Dimming Time",
        mode="box",
    )
    .add_to_registry()
)
