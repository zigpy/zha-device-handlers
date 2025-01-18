"""Schneider Electric switches quirks."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass

from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBasic,
    SEOnOff,
    SESpecific,
    SESwitchIndication,
)

(
    QuirkBuilder(SE_MANUF_NAME, "NHPB/SWITCH/1")
    .applies_to(SE_MANUF_NAME, "CH2AX/SWITCH/1")
    .replaces(SEBasic, endpoint_id=1)
    .replaces(SEOnOff, endpoint_id=1)
    .replaces(SEBasic, endpoint_id=21)
    .replaces(SESpecific, endpoint_id=21)
    .number(
        attribute_name=SEOnOff.AttributeDefs.se_on_time_reload.name,
        cluster_id=SEOnOff.cluster_id,
        endpoint_id=1,
        min_value=0x0,
        max_value=0xFFFFFFFF,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="On Time Reload",
        translation_key="on_time_reload",
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
