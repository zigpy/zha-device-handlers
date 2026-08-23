"""Device handler for Yale Zigbee Network Modules."""

from zigpy import types as t
from zigpy.zcl.clusters.closures import DoorLock

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.builder import (
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    UnitOfTime,
)


def lang_converter(lang: str) -> str:
    """Convert language string into frontend UI strings."""
    mapping = {
        "en": "English",
        "fr": "French",
        "es": "Spanish",
    }
    return mapping.get(lang.strip().lower(), lang)


def sound_volume_converter(level: int | None) -> str | None:
    """Convert lock volume int into frontend UI strings."""
    mapping = {
        0: "Silent",
        1: "Low volume",
        2: "High volume",
    }
    return mapping.get(level, f"Unknown ({level})")


class yale_lock_mode(t.enum8):
    """Lock operation mode enum."""

    Normal = 0x00
    Vacation = 0x01
    Privacy = 0x02


(
    QuirkBuilder("Yale", "YRD220/240 TSDB")
    .applies_to("Yale", "YRD210 PB DB")
    .applies_to("Yale", "YRL220 TS LL")
    .replaces(DoublingPowerConfigurationCluster)
    .binary_sensor(
        attribute_name=DoorLock.AttributeDefs.auto_relock_time.name,
        cluster_id=DoorLock.cluster_id,
        attribute_converter=lambda value: bool(value > 0),
        reporting_config=ReportingConfig(
            min_interval=3600,
            max_interval=10800,
            reportable_change=1,
        ),
        unique_id_suffix="auto_relock_enabled",
        translation_key="auto_relock_enabled",
        fallback_name="Auto-relock enabled",
    )
    .switch(
        attribute_name=DoorLock.AttributeDefs.enable_one_touch_locking.name,
        cluster_id=DoorLock.cluster_id,
        unique_id_suffix="one_touch_locking",
        translation_key="one_touch_locking",
        fallback_name="One touch locking",
    )
    .switch(
        attribute_name=DoorLock.AttributeDefs.enable_inside_status_led.name,
        cluster_id=DoorLock.cluster_id,
        unique_id_suffix="inside_status_led",
        translation_key="inside_status_led",
        fallback_name="Inside status LED",
    )
    .switch(
        attribute_name=DoorLock.AttributeDefs.enable_privacy_mode_button.name,
        cluster_id=DoorLock.cluster_id,
        unique_id_suffix="button_privacy",
        translation_key="button_privacy",
        fallback_name="Button privacy",
    )
    .enum(
        attribute_name=DoorLock.AttributeDefs.operating_mode.name,
        cluster_id=DoorLock.cluster_id,
        enum_class=yale_lock_mode,
        unique_id_suffix="operating_mode",
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    .number(
        attribute_name=DoorLock.AttributeDefs.auto_relock_time.name,
        cluster_id=DoorLock.cluster_id,
        step=10,
        min_value=10,
        max_value=90,
        multiplier=1,
        unique_id_suffix="auto_relock_time",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="auto_relock_time",
        fallback_name="Auto-relock time",
    )
    .sensor(
        endpoint_id=1,
        cluster_id=DoorLock.cluster_id,
        attribute_name=DoorLock.AttributeDefs.language.name,
        unique_id_suffix="announcement_language",
        device_class=SensorDeviceClass.ENUM,
        attribute_converter=lang_converter,
        translation_key="announcement_language",
        fallback_name="Announcement language",
    )
    .sensor(
        endpoint_id=1,
        cluster_id=DoorLock.cluster_id,
        attribute_name=DoorLock.AttributeDefs.sound_volume.name,
        unique_id_suffix="keypad_sound_volume",
        device_class=SensorDeviceClass.ENUM,
        attribute_converter=sound_volume_converter,
        translation_key="keypad_sound_volume",
        fallback_name="Keypad sound volume",
    )
    .add_to_registry()
)
