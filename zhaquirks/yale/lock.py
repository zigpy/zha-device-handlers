"""Device handler for Yale Zigbee Network Modules."""

from zigpy.zcl.clusters.closures import DoorLock

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.builder import (
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


(
    QuirkBuilder("Yale", "YRD220/240 TSDB")
    .applies_to("Yale", "YRD210 PB DB")
    .applies_to("Yale", "YRL220 TS LL")
    .replaces(DoublingPowerConfigurationCluster)
    .binary_sensor(
        endpoint_id=1,
        cluster_id=DoorLock.cluster_id,
        attribute_name=DoorLock.AttributeDefs.enable_one_touch_locking.name,
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=1,
        ),
        unique_id_suffix="one_touch_locking_enabled",
        translation_key="one_touch_locking_enabled",
        fallback_name="One touch locking enabled",
    )
    .binary_sensor(
        endpoint_id=1,
        cluster_id=DoorLock.cluster_id,
        attribute_name=DoorLock.AttributeDefs.enable_inside_status_led.name,
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=1,
        ),
        unique_id_suffix="inside_status_led_enabled",
        translation_key="inside_status_led_enabled",
        fallback_name="Inside status LED enabled",
    )
    .sensor(
        endpoint_id=1,
        cluster_id=DoorLock.cluster_id,
        attribute_name=DoorLock.AttributeDefs.auto_relock_time.name,
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=1,
        ),
        unique_id_suffix="auto_relock_time",
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="automatic_relock_time",
        fallback_name="Automatic relock time",
    )
    .sensor(
        endpoint_id=1,
        cluster_id=DoorLock.cluster_id,
        attribute_name=DoorLock.AttributeDefs.language.name,
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=1,
        ),
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
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=1
        ),
        unique_id_suffix="keypad_sound_volume",
        device_class=SensorDeviceClass.ENUM,
        attribute_converter=sound_volume_converter,
        translation_key="keypad_sound_volume",
        fallback_name="Keypad sound volume",
    )
    .add_to_registry()
)
