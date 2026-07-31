"""Schneider Electric dimmers and switches quirks."""

from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass

from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBallast,
    SEBasic,
    SEControlMode,
    SEDimmingCurve,
    SEOnOff,
    SESwitchAction,
    SESwitchConfiguration,
    SESwitchIndication,
    SEWiringMode,
)

base_micro_dimmer = (
    QuirkBuilder()
    .replaces(SEBasic, endpoint_id=3)
    .replaces(SEBallast, endpoint_id=3)
    .replaces(SEOnOff, endpoint_id=3)
    .number(
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload.name,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=3,
        min_value=0,
        max_value=0xFFFFFFFF,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="on_time_reload",
        fallback_name="On time reload",
    )
    .number(
        attribute_name=SEOnOff.AttributeDefs.se_pre_warning_time.name,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=3,
        min_value=0,
        max_value=6553,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="pre_warning_time",
        fallback_name="Pre warning time",
    )
    .enum(
        attribute_name=SEBallast.AttributeDefs.se_control_mode.name,
        enum_class=SEControlMode,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        translation_key="control_mode",
        fallback_name="Control mode",
    )
)

base_dimmer = (
    base_micro_dimmer.clone()
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESwitchConfiguration, endpoint_id=21)
    .enum(
        attribute_name=SESwitchConfiguration.AttributeDefs.se_switch_indication.name,
        enum_class=SESwitchIndication,
        cluster_id=SESwitchConfiguration.cluster_id,
        endpoint_id=21,
        translation_key="switch_indication",
        fallback_name="Switch indication",
    )
    .enum(
        attribute_name=SESwitchConfiguration.AttributeDefs.se_switch_actions.name,
        enum_class=SESwitchAction,
        cluster_id=SESwitchConfiguration.cluster_id,
        endpoint_id=21,
        translation_key="switch_actions",
        fallback_name="Switch actions",
    )
)

(
    base_micro_dimmer.clone()
    .applies_to(SE_MANUF_NAME, "PUCK/DIMMER/1")
    .add_to_registry()
)  # fmt: skip

(
    base_dimmer.clone()
    .applies_to(SE_MANUF_NAME, "NHROTARY/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHPB/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "CH/DIMMER/1")
    .add_to_registry()
)

(
    base_dimmer.clone()
    .applies_to(SE_MANUF_NAME, "NHROTARY/UNIDIM/1")
    .applies_to(SE_MANUF_NAME, "NHPB/UNIDIM/1")
    .enum(
        attribute_name=SEBallast.AttributeDefs.se_wiring_mode.name,
        enum_class=SEWiringMode,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="wiring_mode",
        fallback_name="Wiring mode",
    )
    .enum(
        attribute_name=SEBallast.AttributeDefs.se_dimming_curve.name,
        enum_class=SEDimmingCurve,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        translation_key="dimming_curve",
        fallback_name="Dimming curve",
    )
    .add_to_registry()
)
