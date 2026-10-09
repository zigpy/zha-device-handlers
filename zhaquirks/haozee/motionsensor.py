"""ZHA Custom Quirk: NEO NAS-PS10B2 Human Presence Sensor (24 GHz mmWave).

Unterstützte Geräte:
  Modell-ID : TS0601
  Hersteller: _TZE204_1youk3hj  (ältere Firmware)
              _TZE284_1youk3hj  (neuere Firmware)

DP-Mapping – verifiziert via:
  1. ZHA Debug-Log (live Gerätedaten)
  2. offizieller Z2M-Quellcode (zigbee-herdsman-converters/src/devices/neo.ts)

  DP   1  presence               bool    READ
  DP  11  human_motion_state     enum    READ (0=none, 1=small, 2=large)
  DP  12  presence_time          uint32  SET  (3–600 s)
  DP  13  motion_far_detection   uint32  SET  (150–600 cm, Schritte 75)
  DP  15  motion_sensitivity     uint32  SET  (0–7)
  DP  16  motionless_sensitivity uint32  SET  (0–7)
  DP  19  dis_current            uint32  READ (0–600 cm)
  DP 101  work_mode              enum    SET  (0=manual, 1=auto)
  DP 102  lux_value              enum    SET  (0=10lux, 1=20lux, 2=50lux, 3=24h)
  DP 103  output_time            uint32  SET  (10–1800 s)
  DP 104  output_switch          bool    SET
  DP 105  led_switch             bool    SET
"""

from zigpy.quirks.v2 import EntityPlatform
from zigpy.quirks.v2.homeassistant import UnitOfLength, UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Lokaler OccupancySensing-Cluster."""


class TuyaHumanMotionState(t.enum8):
    """DP 11 – Bewegungsstatus (read-only)."""

    none = 0x00
    small = 0x01
    large = 0x02


class TuyaWorkMode(t.enum8):
    """DP 101 – Arbeitsmodus."""

    manual = 0x00
    auto = 0x01


class TuyaLuxValue(t.enum8):
    """DP 102 – Helligkeitsschwelle."""

    lux_10 = 0x00
    lux_20 = 0x01
    lux_50 = 0x02
    always = 0x03  # 24h


# ---------------------------------------------------------------------------
# Quirk-Definition via TuyaQuirkBuilder
# ---------------------------------------------------------------------------

(
    TuyaQuirkBuilder("_TZE204_1youk3hj", "TS0601")
    .applies_to("_TZE284_1youk3hj", "TS0601")
    # DP 1 – Presence → OccupancySensing
    .adds(TuyaOccupancySensing)
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    # DP 11 – Human Motion State (read-only, als Sensor nicht Select)
    .tuya_enum(
        dp_id=11,
        attribute_name="human_motion_state",
        enum_class=TuyaHumanMotionState,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="human_motion_state",
        fallback_name="Human motion state",
    )
    # DP 19 – Current Distance (Sensor)
    .tuya_sensor(
        dp_id=19,
        attribute_name="dis_current",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        translation_key="current_distance",
        fallback_name="Current distance",
    )
    # DP 12 – Presence Time
    .tuya_number(
        dp_id=12,
        attribute_name="presence_time",
        type=t.uint32_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=3,
        max_value=600,
        step=1,
        translation_key="presence_time",
        fallback_name="Presence time",
    )
    # DP 13 – Motion Far Detection (Schritte 75 cm lt. Z2M)
    .tuya_number(
        dp_id=13,
        attribute_name="motion_far_detection",
        type=t.uint32_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=150,
        max_value=600,
        step=75,
        translation_key="motion_far_detection",
        fallback_name="Motion range detection",
    )
    # DP 15 – Motion Sensitivity
    .tuya_number(
        dp_id=15,
        attribute_name="motion_sensitivity",
        type=t.uint32_t,
        min_value=0,
        max_value=7,
        step=1,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    # DP 16 – Motionless Sensitivity
    .tuya_number(
        dp_id=16,
        attribute_name="motionless_sensitivity",
        type=t.uint32_t,
        min_value=0,
        max_value=7,
        step=1,
        translation_key="motionless_sensitivity",
        fallback_name="Motionless sensitivity",
    )
    # DP 103 – Output Time
    .tuya_number(
        dp_id=103,
        attribute_name="output_time",
        type=t.uint32_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=10,
        max_value=1800,
        step=10,
        translation_key="output_time",
        fallback_name="Output time",
    )
    # DP 104 – Output Switch
    .tuya_switch(
        dp_id=104,
        attribute_name="output_switch",
        translation_key="output_switch",
        fallback_name="Output switch",
    )
    # DP 105 – LED Switch
    .tuya_switch(
        dp_id=105,
        attribute_name="led_switch",
        translation_key="led_switch",
        fallback_name="LED switch",
    )
    # DP 101 – Work Mode
    .tuya_enum(
        dp_id=101,
        attribute_name="work_mode",
        enum_class=TuyaWorkMode,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    # DP 102 – Lux Value
    .tuya_enum(
        dp_id=102,
        attribute_name="lux_value",
        enum_class=TuyaLuxValue,
        translation_key="lux_value",
        fallback_name="Lux threshold",
    )
    .skip_configuration()
    .add_to_registry()
)
