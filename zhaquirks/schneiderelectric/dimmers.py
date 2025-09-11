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
    SEOnTimeReloadOptions,
    SESwitchAction,
    SESwitchConfiguration,
    SESwitchIndication,
    SEWiringMode,
)

BASE_DIMMER = (
    QuirkBuilder()
    .replaces(SEBasic, endpoint_id=3)
    .replaces(SEBallast, endpoint_id=3)
    .replaces(SEOnOff, endpoint_id=3)
    .number(
        attribute_name=SEBallast.AttributeDefs.min_level.name,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        min_value=1,
        max_value=254,
        step=1,
        fallback_name="Min light level",
        translation_key="min_level",
    )
    .number(
        attribute_name=SEBallast.AttributeDefs.max_level.name,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        min_value=1,
        max_value=254,
        step=1,
        fallback_name="Max light level",
        translation_key="max_level",
    )
    .number(
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload.name,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=3,
        min_value=0x0,
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
        min_value=0x0,
        max_value=0xFFFF,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="pre_warning_time",
        fallback_name="Pre warning time",
    )
    .enum(
        endpoint_id=3,
        cluster_id=SEOnOff.cluster_id,
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload_options.name,
        enum_class=SEOnTimeReloadOptions,
        translation_key="on_time_reload_options",
        fallback_name="On time reload options",
    )
    .enum(
        endpoint_id=3,
        cluster_id=SEBallast.cluster_id,
        attribute_name=SEBallast.AttributeDefs.se_control_mode.name,
        enum_class=SEControlMode,
        translation_key="control_mode",
        fallback_name="Control mode",
    )
)

BASE_ROTARY_DIMMER = (
    BASE_DIMMER.clone()
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESwitchConfiguration, endpoint_id=21)
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
)

(
    BASE_DIMMER.clone()
    .applies_to(SE_MANUF_NAME, "PUCK/DIMMER/1")
    .add_to_registry()
)

(
    BASE_ROTARY_DIMMER.clone()
    .applies_to(SE_MANUF_NAME, "NHROTARY/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHPB/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "CH/DIMMER/1")
    .add_to_registry()
)

(
    BASE_ROTARY_DIMMER.clone()
    .applies_to(SE_MANUF_NAME, "NHROTARY/UNIDIM/1")
    .applies_to(SE_MANUF_NAME, "NHPB/UNIDIM/1")
    .enum(
        endpoint_id=3,
        cluster_id=SEBallast.cluster_id,
        attribute_name=SEBallast.AttributeDefs.se_wiring_mode.name,
        enum_class=SEWiringMode,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="wiring_mode",
        fallback_name="Wiring mode",
    )
    .enum(
        endpoint_id=3,
        cluster_id=SEBallast.cluster_id,
        attribute_name=SEBallast.AttributeDefs.se_dimming_curve.name,
        enum_class=SEDimmingCurve,
        translation_key="dimming_curve",
        fallback_name="Dimming curve",
    )
    .add_to_registry()
)
