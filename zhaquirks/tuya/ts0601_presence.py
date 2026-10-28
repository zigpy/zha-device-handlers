"""Tuya TS0601 presence sensor (_TZE200_tyffvoij)."""

from zigpy.quirks.v2 import EntityType
import zigpy.types as t
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """OccupancySensing (0x0406)."""


class TuyaIlluminanceMeasurement(IlluminanceMeasurement, TuyaLocalCluster):
    """IlluminanceMeasurement (0x0400)."""


class MotionDetectionMode(t.enum8):
    """Motion detection mode enum (DP 122)."""

    Motion_only = 0x00
    Motion_and_presence = 0x01
    Presence_only = 0x02


def _cm_to_m(v: int) -> float:
    return float(v) / 100.0


def _m_to_cm(v: float) -> int:
    return int(round(v * 100.0))


(
    TuyaQuirkBuilder("_TZE200_tyffvoij", "TS0601")
    # Suppress duplicate native ZCL IAS Zone binary sensor
    .removes(IasZone)
    # Replace hardware PowerConfiguration (0x0001) with Tuya's virtual power cluster
    # and bind DP 121 directly to battery_percentage_remaining
    .adds(TuyaPowerConfigurationCluster)
    .tuya_dp(
        dp_id=121,
        ep_attribute=TuyaPowerConfigurationCluster.ep_attribute,
        attribute_name="battery_percentage_remaining",
    )
    # --- Occupancy via ZCL 0x0406 ---
    .adds(TuyaOccupancySensing)
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name="occupancy",
    )
    # --- Illuminance via ZCL 0x0400 ---
    .adds(TuyaIlluminanceMeasurement)
    .tuya_illuminance(dp_id=106)
    # ---- DP 2: Radar Sensitivity ----
    .tuya_number(
        dp_id=2,
        attribute_name="sensitivity",
        type=t.uint8_t,
        min_value=0,
        max_value=10,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    # ---- DP 123: Motion Sensitivity ----
    .tuya_number(
        dp_id=123,
        attribute_name="motion_sensitivity",
        type=t.uint8_t,
        min_value=0,
        max_value=10,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    # ---- DP 3: Minimum Detection Distance (m) ----
    .tuya_dp_attribute(
        dp_id=3,
        attribute_name="near_detection_m",
        type=t.uint32_t,
        converter=_cm_to_m,
        dp_converter=_m_to_cm,
    )
    .number(
        cluster_id=TUYA_CLUSTER_ID,
        attribute_name="near_detection_m",
        min_value=0.0,
        max_value=10.0,
        step=0.1,
        unit="m",
        entity_type=EntityType.CONFIG,
        translation_key="min_distance",
        fallback_name="Minimum detection distance",
    )
    # ---- DP 4: Maximum Detection Distance (m) ----
    .tuya_dp_attribute(
        dp_id=4,
        attribute_name="far_detection_m",
        type=t.uint32_t,
        converter=_cm_to_m,
        dp_converter=_m_to_cm,
    )
    .number(
        cluster_id=TUYA_CLUSTER_ID,
        attribute_name="far_detection_m",
        min_value=0.0,
        max_value=10.0,
        step=0.1,
        unit="m",
        entity_type=EntityType.CONFIG,
        translation_key="max_distance",
        fallback_name="Maximum detection distance",
    )
    # ---- DP 102: Presence Timeout (seconds) ----
    .tuya_dp_attribute(
        dp_id=102,
        attribute_name="none_delay_s",
        type=t.uint16_t,
    )
    .number(
        cluster_id=TUYA_CLUSTER_ID,
        attribute_name="none_delay_s",
        min_value=10.0,
        max_value=28800.0,
        step=1.0,
        unit="s",
        entity_type=EntityType.CONFIG,
        translation_key="fade_time",
        fallback_name="Presence timeout",
    )
    # ---- DP 122: Detection Mode ----
    .tuya_enum(
        dp_id=122,
        attribute_name="motion_detection_mode",
        enum_class=MotionDetectionMode,
        entity_type=EntityType.CONFIG,
        translation_key="motion_detection_mode",
        fallback_name="Detection mode",
    )
    .add_to_registry()
)
