"""Schneider Electric switches quirks."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass

from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBasic,
    SEOnOff,
    SEOnTimeReloadOptions,
    SESwitchAction,
    SESwitchConfiguration,
    SESwitchIndication,
)

base_micro_switch = (
    QuirkBuilder()
    .replaces(SEBasic)
    .replaces(SEOnOff)
    .number(
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload.name,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=1,
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
        endpoint_id=1,
        min_value=0,
        max_value=6553,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="pre_warning_time",
        fallback_name="Pre warning time",
    )
    .enum(
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload_options.name,
        enum_class=SEOnTimeReloadOptions,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=1,
        translation_key="on_time_reload_options",
        fallback_name="On time reload options",
    )
)

(
    base_micro_switch.clone()
    .applies_to(SE_MANUF_NAME, "NHPB/SWITCH/1")
    .applies_to(SE_MANUF_NAME, "CH2AX/SWITCH/1")
    .applies_to(SE_MANUF_NAME, "CH10AX/SWITCH/1")
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
    .add_to_registry()
)

(
    base_micro_switch.clone()
    .applies_to(SE_MANUF_NAME, "PUCK/SWITCH/1")
    .add_to_registry()
)  # fmt: skip
