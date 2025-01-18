"""Schneider Electric dimmers quirks."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass

from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBallast,
    SEBasic,
    SEControlMode,
    SEOnOff,
    SESpecific,
    SESwitchIndication,
)

(
    # Note: UNIDIM and DIMMER have unique settings in Ballast Cluster.
    QuirkBuilder(SE_MANUF_NAME, "NHROTARY/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHROTARY/UNIDIM/1")
    .applies_to(SE_MANUF_NAME, "NHPB/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHPB/UNIDIM/1")
    .applies_to(SE_MANUF_NAME, "CH/DIMMER/1")
    .replaces(SEBasic, endpoint_id=3)
    .replaces(SEBallast, endpoint_id=3)
    .replaces(SEOnOff, endpoint_id=3)
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESpecific, endpoint_id=21)
    .number(
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload.name,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=3,
        min_value=0x0,
        max_value=0xFFFFFFFF,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        fallback_name="On Time Reload",
        translation_key="on_time_reload",
    )
    .number(
        attribute_name=SEBallast.AttributeDefs.min_level.name,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        min_value=1,
        max_value=254,
        step=1,
        fallback_name="Min Light Level",
        translation_key="min_level",
    )
    .number(
        attribute_name=SEBallast.AttributeDefs.max_level.name,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        min_value=1,
        max_value=254,
        step=1,
        fallback_name="Max Light Level",
        translation_key="max_level",
    )
    .enum(
        attribute_name=SEBallast.AttributeDefs.se_control_mode.name,
        enum_class=SEControlMode,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=3,
        translation_key="control_mode",
        fallback_name="Control Mode",
    )
    .enum(
        attribute_name=SESpecific.AttributeDefs.se_switch_indication.name,
        enum_class=SESwitchIndication,
        cluster_id=SESpecific.cluster_id,
        endpoint_id=21,
        translation_key="switch_indication",
        fallback_name="Switch Indication",
    )
    .add_to_registry()
)
