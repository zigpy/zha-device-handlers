"""Quirks for Schneider Electric shutters."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.zcl import ClusterType

from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBasic,
    SESwitchAction,
    SESwitchConfiguration,
    SESwitchIndication,
    SEWindowCovering,
)

(
    QuirkBuilder(SE_MANUF_NAME, "1GANG/SHUTTER/1")
    .applies_to(SE_MANUF_NAME, "NHPB/SHUTTER/1")
    .replaces(SEBasic, endpoint_id=5)
    .replaces(SEWindowCovering, endpoint_id=5)
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESwitchConfiguration, endpoint_id=21)
    .replaces(SEWindowCovering, endpoint_id=21, cluster_type=ClusterType.Client)
    .enum(
        endpoint_id=21,
        cluster_id=SESwitchConfiguration.cluster_id,
        attribute_name=SESwitchConfiguration.AttributeDefs.se_switch_indication.name,
        enum_class=SESwitchIndication,
        translation_key="switch_indication",
        fallback_name="Switch indication",
    )
    .enum(
        endpoint_id=21,
        cluster_id=SESwitchConfiguration.cluster_id,
        attribute_name=SESwitchConfiguration.AttributeDefs.se_switch_actions.name,
        enum_class=SESwitchAction,
        translation_key="switch_actions",
        fallback_name="Switch actions",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_lift_drive_up_time.name,
        unit=UnitOfTime.SECONDS,
        multiplier=0.1,
        min_value=1,
        max_value=300,
        step=0.1,
        translation_key="lift_drive_up_time",
        fallback_name="Lift drive up time",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_lift_drive_down_time.name,
        unit=UnitOfTime.SECONDS,
        multiplier=0.1,
        min_value=1,
        max_value=300,
        step=0.1,
        translation_key="lift_drive_down_time",
        fallback_name="Lift drive down time",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_tilt_open_close_and_step_time.name,
        unit=UnitOfTime.SECONDS,
        multiplier=0.01,
        min_value=0,
        max_value=30,
        step=0.01,
        translation_key="tilt_open_close_and_step_time",
        fallback_name="Tilt open close and step time",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_tilt_position_percentage_after_move_to_level.name,
        min_value=0,
        max_value=255,
        step=1,
        translation_key="tilt_position_percentage_after_move_to_level",
        fallback_name="Tilt position percentage after move to level",
    )
    .add_to_registry()
)

(
    QuirkBuilder(SE_MANUF_NAME, "PUCK/SHUTTER/1")
    .replaces(SEBasic, endpoint_id=5)
    .replaces(SEWindowCovering, endpoint_id=5)
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_lift_drive_up_time.name,
        unit=UnitOfTime.SECONDS,
        multiplier=0.1,
        translation_key="lift_drive_up_time",
        fallback_name="Lift drive up time",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_lift_drive_down_time.name,
        unit=UnitOfTime.SECONDS,
        multiplier=0.1,
        translation_key="lift_drive_down_time",
        fallback_name="Lift drive down time",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_tilt_open_close_and_step_time.name,
        unit=UnitOfTime.SECONDS,
        multiplier=0.01,
        translation_key="tilt_open_close_and_step_time",
        fallback_name="Tilt open close and step time",
    )
    .number(
        endpoint_id=5,
        cluster_id=SEWindowCovering.cluster_id,
        attribute_name=SEWindowCovering.AttributeDefs.se_tilt_position_percentage_after_move_to_level.name,
        min_value=0,
        max_value=255,
        step=1,
        translation_key="tilt_position_percentage_after_move_to_level",
        fallback_name="Tilt position percentage after move to level",
    )
    .add_to_registry()
)
