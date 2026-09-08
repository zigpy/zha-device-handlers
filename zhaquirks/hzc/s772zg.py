"""Quirk for HZC S772-ZG two-channel switch."""

from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ExternalSwitchType(t.enum8):
    """External switch type enum."""

    doorbell_switch = 0x00
    mechanical_toggle_switch = 0x01


class StartUpOnOff(t.enum8):
    """Start up on off enum without the Toggle option.

    The S772-ZG does not support Toggle, so only Off, On and
    PreviousValue are exposed.
    """

    Off = 0x00
    On = 0x01
    PreviousValue = 0xFF


class HzcTimerCluster(CustomCluster):
    """Private cluster 0xE00C for auto on/off timers."""

    cluster_id = 0xE00C
    name = "HZC Timer"
    ep_attribute = "hzc_timer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        auto_off_timer: Final = ZCLAttributeDef(id=0x0000, type=t.uint32_t)
        auto_on_timer: Final = ZCLAttributeDef(id=0x0001, type=t.uint32_t)


class HzcDelayCluster(CustomCluster):
    """Private cluster 0xE007 for on/off delay and external switch type."""

    cluster_id = 0xE007
    name = "HZC Delay"
    ep_attribute = "hzc_delay"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        external_switch_type: Final = ZCLAttributeDef(
            id=0x0000, type=ExternalSwitchType
        )
        on_delay: Final = ZCLAttributeDef(id=0x0002, type=t.uint8_t)
        off_delay: Final = ZCLAttributeDef(id=0x0004, type=t.uint8_t)


(
    QuirkBuilder("HZC", "S772-ZG")
    .adds(HzcTimerCluster, endpoint_id=1)
    .adds(HzcTimerCluster, endpoint_id=2)
    .adds(HzcDelayCluster, endpoint_id=1)
    .adds(HzcDelayCluster, endpoint_id=2)
    .number(
        attribute_name="auto_off_timer",
        cluster_id=HzcTimerCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=86400,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 1 auto off timer",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .number(
        attribute_name="auto_on_timer",
        cluster_id=HzcTimerCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=86400,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 1 auto on timer",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .number(
        attribute_name="off_delay",
        cluster_id=HzcDelayCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 1 off delay",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .number(
        attribute_name="on_delay",
        cluster_id=HzcDelayCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 1 on delay",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "StartupOnOffSelectEntity",
    )
    .enum(
        attribute_name=OnOff.AttributeDefs.start_up_on_off.name,
        enum_class=StartUpOnOff,
        cluster_id=OnOff.cluster_id,
        endpoint_id=1,
        translation_key="channel_1_power_on_state",
        fallback_name="Channel 1 power on state",
    )
    .number(
        attribute_name="auto_off_timer",
        cluster_id=HzcTimerCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=86400,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 2 auto off timer",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .number(
        attribute_name="auto_on_timer",
        cluster_id=HzcTimerCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=86400,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 2 auto on timer",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .number(
        attribute_name="off_delay",
        cluster_id=HzcDelayCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 2 off delay",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .number(
        attribute_name="on_delay",
        cluster_id=HzcDelayCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        fallback_name="Channel 2 on delay",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "StartupOnOffSelectEntity",
    )
    .enum(
        attribute_name=OnOff.AttributeDefs.start_up_on_off.name,
        enum_class=StartUpOnOff,
        cluster_id=OnOff.cluster_id,
        endpoint_id=2,
        translation_key="channel_2_power_on_state",
        fallback_name="Channel 2 power on state",
    )
    # External switch type per channel (EP1/EP2: AID 0x0000)
    .enum(
        attribute_name="external_switch_type",
        enum_class=ExternalSwitchType,
        cluster_id=HzcDelayCluster.cluster_id,
        endpoint_id=1,
        translation_key="channel_1_external_switch_type",
        fallback_name="Channel 1 external switch type",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .enum(
        attribute_name="external_switch_type",
        enum_class=ExternalSwitchType,
        cluster_id=HzcDelayCluster.cluster_id,
        endpoint_id=2,
        translation_key="channel_2_external_switch_type",
        fallback_name="Channel 2 external switch type",
        reporting_config=ReportingConfig(
            min_interval=1, max_interval=300, reportable_change=1
        ),
    )
    .add_to_registry()
)
