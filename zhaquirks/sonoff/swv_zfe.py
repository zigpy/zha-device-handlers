"""Sonoff SWV-ZFE - Zigbee smart water valve (Flow Edition)."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType, UnitOfTime, UnitOfVolume
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


def swvzfe_be_swap(x: int | None) -> int | None:
    """Byte-swap a UINT32 the device sends big-endian over the ZCL (little-endian) frame."""
    if x is None:
        return None
    return int.from_bytes(x.to_bytes(4, "little"), "big")


def swvzfe_water_shortage(x: int | None) -> bool | None:
    """Extract water shortage flag (bit 0) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x01)


def swvzfe_water_leakage(x: int | None) -> bool | None:
    """Extract water leakage flag (bit 1) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x02)


def swvzfe_frost_protection(x: int | None) -> bool | None:
    """Extract frost protection active flag (bit 2) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x04)


def swvzfe_fail_safe(x: int | None) -> bool | None:
    """Extract fail-safe flag (bit 3) from valve_abnormal_state."""
    if x is None:
        return None
    return bool(x & 0x08)


class SWVZFECluster(CustomCluster):
    """Custom Sonoff cluster for the SWV-ZFE smart water valve."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the private Sonoff cluster."""

        # 0x0000 - Child lock (on/off physical buttons on device)
        child_lock = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
            manufacturer_code=None,
        )

        # 0x5006 - Real-time irrigation duration (seconds, big-endian UINT32)
        real_time_irrigation_duration = ZCLAttributeDef(
            id=0x5006,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x5007 - Real-time irrigation volume (litres, big-endian UINT32)
        real_time_irrigation_volume = ZCLAttributeDef(
            id=0x5007,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x500C - Valve abnormal state bitmask:
        #   bit 0 = water shortage, bit 1 = water leakage,
        #   bit 2 = frost protection, bit 3 = fail safe
        valve_abnormal_state = ZCLAttributeDef(
            id=0x500C,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        # 0x500F - Daily irrigation volume (litres)
        daily_irrigation_volume = ZCLAttributeDef(
            id=0x500F,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x5010 - Valve work state (True = valve is actively open/working)
        valve_work_state = ZCLAttributeDef(
            id=0x5010,
            type=t.Bool,
            manufacturer_code=None,
        )

        # 0x5011 - Auto-close on water shortage (0 = disabled, 30 = enabled)
        auto_close_water_shortage = ZCLAttributeDef(
            id=0x5011,
            type=t.uint16_t,
            manufacturer_code=None,
        )

        # 0x5016 - Device longitude (integer degrees, -180 to 180)
        longitude = ZCLAttributeDef(
            id=0x5016,
            type=t.int32s,
            manufacturer_code=None,
        )

        # 0x5017 - Device latitude (integer degrees, -90 to 90)
        latitude = ZCLAttributeDef(
            id=0x5017,
            type=t.int32s,
            manufacturer_code=None,
        )

        # 0x501A - Daily irrigation duration (minutes)
        daily_irrigation_duration = ZCLAttributeDef(
            id=0x501A,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x501B - Hourly irrigation volume (litres)
        hour_irrigation_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        # 0x501C - Hourly irrigation duration (minutes)
        hour_irrigation_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
            manufacturer_code=None,
        )


(
    QuirkBuilder("SONOFF", "SWV-ZFE")
    .replaces(SWVZFECluster)
    # Child lock - prevent accidental physical operation of the valve
    .switch(
        SWVZFECluster.AttributeDefs.child_lock.name,
        SWVZFECluster.cluster_id,
        on_value=1,
        off_value=0,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # Whether the valve is actively open and flowing
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_work_state.name,
        SWVZFECluster.cluster_id,
        translation_key="valve_work_state",
        fallback_name="Valve working",
    )
    # Auto-close the valve when a water shortage is detected
    .switch(
        SWVZFECluster.AttributeDefs.auto_close_water_shortage.name,
        SWVZFECluster.cluster_id,
        off_value=0,
        on_value=30,
        translation_key="water_shortage_auto_close",
        fallback_name="Water shortage auto-close",
    )
    # Valve abnormal state - decomposed into individual binary sensors per bit
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_water_shortage,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="water_shortage",
        fallback_name="Water shortage",
    )
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_water_leakage,
        device_class=BinarySensorDeviceClass.MOISTURE,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="water_leakage",
        fallback_name="Water leakage",
    )
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_frost_protection,
        unique_id_suffix="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .binary_sensor(
        SWVZFECluster.AttributeDefs.valve_abnormal_state.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_fail_safe,
        device_class=BinarySensorDeviceClass.SAFETY,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="fail_safe",
        fallback_name="Fail safe",
    )
    # Real-time stats (note: big-endian byte-swap required per device firmware)
    .sensor(
        SWVZFECluster.AttributeDefs.real_time_irrigation_duration.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_be_swap,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="real_time_irrigation_duration",
        fallback_name="Real-time irrigation duration",
    )
    .sensor(
        SWVZFECluster.AttributeDefs.real_time_irrigation_volume.name,
        SWVZFECluster.cluster_id,
        attribute_converter=swvzfe_be_swap,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolume.LITERS,
        translation_key="real_time_irrigation_volume",
        fallback_name="Real-time irrigation volume",
    )
    # Daily totals
    .sensor(
        SWVZFECluster.AttributeDefs.daily_irrigation_volume.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfVolume.LITERS,
        translation_key="daily_irrigation_volume",
        fallback_name="Daily irrigation volume",
    )
    .sensor(
        SWVZFECluster.AttributeDefs.daily_irrigation_duration.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfTime.MINUTES,
        translation_key="daily_irrigation_duration",
        fallback_name="Daily irrigation duration",
    )
    # Hourly totals
    .sensor(
        SWVZFECluster.AttributeDefs.hour_irrigation_volume.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolume.LITERS,
        translation_key="hour_irrigation_volume",
        fallback_name="Hourly irrigation volume",
    )
    .sensor(
        SWVZFECluster.AttributeDefs.hour_irrigation_duration.name,
        SWVZFECluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        translation_key="hour_irrigation_duration",
        fallback_name="Hourly irrigation duration",
    )
    # Device location (used by the device for weather-based irrigation adjustment)
    .number(
        SWVZFECluster.AttributeDefs.longitude.name,
        SWVZFECluster.cluster_id,
        min_value=-180,
        max_value=180,
        step=1,
        mode="box",
        translation_key="longitude",
        fallback_name="Longitude",
    )
    .number(
        SWVZFECluster.AttributeDefs.latitude.name,
        SWVZFECluster.cluster_id,
        min_value=-90,
        max_value=90,
        step=1,
        mode="box",
        translation_key="latitude",
        fallback_name="Latitude",
    )
    .add_to_registry()
)
