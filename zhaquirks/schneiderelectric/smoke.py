"""Scneider Electric Smoke Alarm."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.schneiderelectric import SE_MANUF_NAME, SEBasic


class SELEDBrightness(t.enum8):
    """LED brightness."""

    Min = 0x00
    Max = 0x01


class SEAlarmSoundLevel(t.enum8):
    """Alarm sound level."""

    Min = 0x00
    Max = 0x01


class SEAlarmSoundMode(t.enum8):
    """Alarm sound mode."""

    PressureLow = 0x00
    PressureMid = 0x01
    PressureHigh = 0x02


class SEAlarmConfiguration(CustomCluster):
    """Schneider Electric Alarm Configuration cluster."""

    cluster_id = 0xFC04
    name = "SEAlarmConfiguration"

    class AttributeDefs(CustomCluster.AttributeDefs):
        """Attribute definitions."""

        se_led_brightness: Final = ZCLAttributeDef(
            id=0x0000,
            type=SELEDBrightness,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_alarm_sound_level: Final = ZCLAttributeDef(
            id=0x0001,
            type=SEAlarmSoundLevel,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_alarm_sound_mode: Final = ZCLAttributeDef(
            id=0x0002,
            type=SEAlarmSoundMode,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_lifetime: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        se_hush_duration: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_test_mode: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_silence_alarm: Final = ZCLAttributeDef(
            id=0x0006,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder(SE_MANUF_NAME, "W599001")
    .applies_to(SE_MANUF_NAME, "W599501")
    .applies_to(SE_MANUF_NAME, "755WSA")
    .replaces(SEBasic, endpoint_id=20)
    .replaces(SEAlarmConfiguration, endpoint_id=20)
    .enum(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_led_brightness.name,
        translation_key="led_brightness",
        fallback_name="LED brightness",
        enum_class=SELEDBrightness,
    )
    .enum(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_alarm_sound_level.name,
        translation_key="alarm_sound_level",
        fallback_name="Alarm sound level",
        enum_class=SEAlarmSoundLevel,
    )
    .enum(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_alarm_sound_mode.name,
        translation_key="alarm_sound_mode",
        fallback_name="Alarm sound mode",
        enum_class=SEAlarmSoundMode,
    )
    .sensor(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_lifetime.name,
        translation_key="lifetime",
        fallback_name="Lifetime",
        unit=UnitOfTime.YEARS,
        multiplier=0.5,
        entity_type=EntityType.DIAGNOSTIC,
    )
    .number(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_hush_duration.name,
        translation_key="hush_duration",
        fallback_name="Hush duration",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=5,
        max_value=15,
        step=1,
    )
    .switch(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_test_mode.name,
        translation_key="test_mode",
        fallback_name="Test mode",
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=0,
            reportable_change=1,
        ),
    )
    .switch(
        cluster_id=SEAlarmConfiguration.cluster_id,
        endpoint_id=20,
        attribute_name=SEAlarmConfiguration.AttributeDefs.se_silence_alarm.name,
        translation_key="silence_alarm",
        fallback_name="Silence alarm",
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=0,
            reportable_change=1,
        ),
    )
    .add_to_registry()
)
