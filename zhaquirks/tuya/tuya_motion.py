"""BlitzWolf IS-3/Tuya motion rechargeable occupancy sensor."""

import asyncio
from typing import Any

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import LIGHT_LUX, UnitOfLength, UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


class TuyaMotionWithReset(IasZone, TuyaLocalCluster):
    """Tuya local IAS motion cluster with reset."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Motion_Sensor
    }
    reset_s: int = 15

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._loop = asyncio.get_running_loop()
        self._timer_handle = None

    def _turn_off(self) -> None:
        """Reset IAS zone status."""
        self._timer_handle = None
        self.debug("%s - Resetting Tuya motion sensor", self.endpoint.device.ieee)
        self._update_attribute(IasZone.AttributeDefs.zone_status.id, 0)

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Catch zone status updates and potentially schedule reset."""
        if (
            attrid == IasZone.AttributeDefs.zone_status.id
            and value == IasZone.ZoneStatus.Alarm_1
        ):
            self.debug("%s - Received Tuya motion event", self.endpoint.device.ieee)
            if self._timer_handle:
                self._timer_handle.cancel()
            self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)

        super()._update_attribute(attrid, value)


class TuyaSelfCheckResult(t.enum8):
    """Tuya self check result enum."""

    Checking = 0x00
    CheckSuccess = 0x01
    CheckFailure = 0x02
    Others = 0x03
    CommFault = 0x04
    RadarFault = 0x05


class TuyaPresenceState(t.enum8):
    """Tuya presence state enum."""

    Unoccupied = 0x00
    Presence = 0x01
    Peaceful = 0x02
    Small_movement = 0x03
    Large_movement = 0x04


class TuyaPresenceStateV02(t.enum8):
    """Tuya presence state enum, variation 02."""

    Unoccupied = 0x00
    Large = 0x01
    Medium = 0x02
    Small = 0x03
    Huge = 0x04
    Gigantic = 0x05


class TuyaBreakerMode(t.enum8):
    """Tuya breaker mode enum."""

    Standard = 0x00
    Local = 0x01


class TuyaBreakerStatus(t.enum8):
    """Tuya breaker status enum."""

    Off = 0x00
    On = 0x01


class TuyaStatusIndication(t.enum8):
    """Tuya status indication enum."""

    Off = 0x00
    On = 0x01


class TuyaBreakerPolarity(t.enum8):
    """Tuya breaker polarity enum."""

    NC = 0x00
    NO = 0x01


class TuyaMotionSensorMode(t.enum8):
    """Tuya motion sensor mode enum."""

    On = 0x00
    Off = 0x01
    Occupied = 0x02
    Unoccupied = 0x03


class TuyaHumanMotionState(t.enum8):
    """Tuya human motion state enum."""

    Off = 0x00
    Small = 0x01
    Large = 0x02


class TuyaHumanMotionStateV02(t.enum8):
    """Tuya human motion state enum, variation 02."""

    Off = 0x00
    Large = 0x01
    Small = 0x02
    Static = 0x03


class TuyaMotionWorkMode(t.enum8):
    """Tuya motion working mode enum."""

    Manual = 0x00
    Auto = 0x01


class TuyaMotionPresenceSensitivity(t.enum8):
    """Tuya motion presence sensitivity enum."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class TuyaMotionFadeTime(t.enum8):
    """Tuya motion fade time enum."""

    _10_seconds = 0x00
    _30_seconds = 0x01
    _60_seconds = 0x02
    _120_seconds = 0x03


class TuyaSensitivityMode(t.enum8):
    """Tuya sensitivity mode enum."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class TuyaMotionDetectionMode(t.enum8):
    """Tuya motion detection mode enum."""

    Only_PIR = 0x00
    PIR_and_radar = 0x01
    Only_radar = 0x03


base_tuya_motion = (
    TuyaQuirkBuilder()
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=2,
        attribute_name="move_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="move_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .tuya_number(
        dp_id=3,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=8.25,
        step=0.75,
        multiplier=0.01,
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
    )
    .tuya_number(
        dp_id=4,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0.75,
        max_value=9.0,
        step=0.75,
        multiplier=0.01,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_sensor(
        dp_id=9,
        attribute_name="distance",
        type=t.uint16_t,
        divisor=100,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        entity_type=EntityType.STANDARD,
        translation_key="distance",
        fallback_name="Target distance",
    )
    .skip_configuration()
)


(
    base_tuya_motion.clone()
    .applies_to("_TZE200_gkfbdvyx", "TS0601")
    .applies_to("_TZE200_ya4ft0w4", "TS0601")
    .applies_to("_TZE204_ya4ft0w4", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: True if x in (1, 2) else False,
    )
    # 2, 3, 4, and 9 from base
    .tuya_switch(
        dp_id=101,
        attribute_name="distance_tracking",
        entity_type=EntityType.CONFIG,
        translation_key="distance_tracking",
        fallback_name="Distance tracking",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="presence_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="presence_sensitivity",
        fallback_name="Presence sensitivity",
    )
    .tuya_illuminance(dp_id=103)
    .tuya_number(
        dp_id=105,
        attribute_name="presence_timeout",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=15000,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .add_to_registry()
)


(
    base_tuya_motion.clone()
    .applies_to("_TZE200_ar0slwnd", "TS0601")  # Not present in z2m
    .applies_to("_TZE200_mrf6vtua", "TS0601")  # Not present in z2m
    .applies_to("_TZE200_sfiy5tfs", "TS0601")  # Not present in z2m
    .applies_to("_TZE204_sooucan5", "TS0601")  # Not present in z2m
    .applies_to("_TZE200_wukb7rhc", "TS0601")  # Listed in z2m
    .applies_to("_TZE200_ztc6ggyl", "TS0601")  # Listed in z2m
    .applies_to("_TZE204_ztc6ggyl", "TS0601")  # Listed in z2m
    .applies_to("_TZE200_ikvncluo", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE200_lyetpprm", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE200_jva8ink8", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE204_xpq2rzhq", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE200_holel4dk", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE200_xpq2rzhq", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE204_xsm7l9xa", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE200_sgpeacqp", "TS0601")  # Added from z2m, not present prior
    .applies_to("_TZE204_fwondbzy", "TS0601")  # Added from z2m, not present prior
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    # 2, 3, 4, and 9 from base
    .tuya_enum(
        dp_id=6,  # z2m lists as not working, yet exposes
        attribute_name="self_test",
        enum_class=TuyaSelfCheckResult,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="self_test",
        fallback_name="Self test result",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="presence_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        multiplier=0.1,
        translation_key="presence_sensitivity",
        fallback_name="Presence sensitivity",
    )
    .tuya_illuminance(dp_id=104)
    # 103 cli, z2m lists as not working
    .add_to_registry()
)


(
    base_tuya_motion.clone()
    .applies_to("_TZE204_qasjif9e", "TS0601")
    .applies_to("_TZE204_ztqnh5cg", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    # 2, 3, 4, and 9 from base
    .tuya_number(
        dp_id=101,
        attribute_name="detection_delay",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=1500,
        step=0.1,
        multiplier=0.1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_illuminance(dp_id=104)
    .add_to_registry()
)

# Whenzi Tuya WZ-M100
# https://github.com/wzwenzhi/Wenzhi-ZigBee2mqtt/blob/main/wenzhi_tuya_M100_240704.js
(
    base_tuya_motion.clone()
    .applies_to("_TZE204_laokfqwu", "TS0601")
    .applies_to("_TZE200_clrdrnya", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    # 2, 3, 4, and 9 from base
    .tuya_number(
        dp_id=104,
        attribute_name="interval_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=3600,
        step=1,
        translation_key="interval_time",
        fallback_name="Interval time",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="detection_delay",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0.1,
        max_value=10,
        step=0.1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=1500,
        step=5,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_illuminance(dp_id=103)
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TYST11_i5j6ifxj", "5j6ifxj")
    .applies_to("_TYST11_7hfcudw5", "hfcudw5")
    .tuya_ias(
        dp_id=3,
        ias_cfg=TuyaMotionWithReset,
        converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x == 2 else 0,
    )
    .skip_configuration()
    .add_to_registry()
)


# Neo motion, NAS-PD07 occupancy sensor
(
    TuyaQuirkBuilder("_TZE200_7hfcudw5", "TS0601")
    .applies_to("_TZE200_ppuj1vem", "TS0601")
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_temperature(dp_id=104, scale=10)
    .tuya_humidity(dp_id=105)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_uxllnywp", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 4,
    )
    .adds(TuyaOccupancySensing)
    .tuya_sensor(
        dp_id=101,
        attribute_name="target_distance",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        entity_type=EntityType.STANDARD,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .tuya_illuminance(dp_id=102)
    .tuya_number(
        dp_id=103,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=59,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_switch(
        dp_id=104,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=0,
        max_value=840,
        step=1,
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=0.75,
        max_value=840,
        step=1,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=111,
        attribute_name="presence_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="presence_sensitivity",
        fallback_name="Presence sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_dapwryy7", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x != TuyaPresenceState.Unoccupied,
    )
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=101,
        attribute_name="target_distance",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .tuya_illuminance(dp_id=102)
    .tuya_number(
        dp_id=103,
        attribute_name="hold_delay_time",
        type=t.uint16_t,
        min_value=0,
        max_value=28800,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="hold_delay_time",
        fallback_name="Hold delay time",
    )
    .tuya_switch(
        dp_id=104,
        attribute_name="led_indicator",
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="breath_detection_max",
        type=t.uint16_t,
        min_value=0,
        max_value=6,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="breath_detection_max",
        fallback_name="Breath detection max",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="breath_detection_min",
        type=t.uint16_t,
        min_value=0,
        max_value=6,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="breath_detection_min",
        fallback_name="Breath detection min",
    )
    .tuya_number(
        dp_id=114,
        attribute_name="small_move_detection_max",
        type=t.uint16_t,
        min_value=0,
        max_value=6,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="small_move_detection_max",
        fallback_name="Small move detection max",
    )
    .tuya_number(
        dp_id=115,
        attribute_name="small_move_detection_min",
        type=t.uint16_t,
        min_value=0,
        max_value=6,
        step=0.01,
        unit=UnitOfLength.METERS,
        multiplier=0.01,
        translation_key="small_move_detection_min",
        fallback_name="Small move detection min",
    )
    .tuya_number(
        dp_id=116,
        attribute_name="move_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="move_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .tuya_number(
        dp_id=117,
        attribute_name="small_move_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="small_move_sensitivity",
        fallback_name="Small move sensitivity",
    )
    .tuya_number(
        dp_id=118,
        attribute_name="breath_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="breath_sensitivity",
        fallback_name="Breath sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)


(
    base_tuya_motion.clone()
    .applies_to("_TZE204_sbyx0lm6", "TS0601")
    .applies_to("_TZE204_clrdrnya", "TS0601")
    .applies_to("_TZE204_dtzziy1e", "TS0601")
    .applies_to("_TZE204_iaeejhvf", "TS0601")
    .applies_to("_TZE204_mtoaryre", "TS0601")
    .applies_to("_TZE200_mp902om5", "TS0601")
    .applies_to("_TZE204_pfayrzcw", "TS0601")
    .applies_to("_TZE284_4qznlkbu", "TS0601")
    .applies_to("_TZE200_sbyx0lm6", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    # 2, 3, 4, and 9 from base, z2m has slightly different values limits and names
    # 6 is equipment_status, z2m doesn't expose
    .tuya_number(
        dp_id=101,
        attribute_name="detection_delay",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=600,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    # 103 cline, z2m doesn't expose
    .tuya_illuminance(dp_id=104)
    .tuya_number(
        dp_id=105,
        attribute_name="entry_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=9,
        step=1,
        translation_key="entry_sensitivity",
        fallback_name="Entry sensitivity",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="entry_distance_indentation",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=9,
        step=0.1,
        multiplier=0.01,
        translation_key="entry_distance_indentation",
        fallback_name="Entry distance indentation",
    )
    .tuya_enum(
        dp_id=107,
        attribute_name="breaker_mode",
        enum_class=TuyaBreakerMode,
        translation_key="breaker_mode",
        fallback_name="Breaker mode",
    )
    .tuya_enum(
        dp_id=108,
        attribute_name="breaker_status",
        enum_class=TuyaBreakerStatus,
        translation_key="breaker_status",
        fallback_name="Breaker status",
    )
    .tuya_enum(
        dp_id=109,
        attribute_name="status_indication",
        enum_class=TuyaStatusIndication,
        translation_key="status_indication",
        fallback_name="Status indication",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="illuminance_threshold",
        type=t.uint16_t,
        device_class=SensorDeviceClass.ILLUMINANCE,
        unit=LIGHT_LUX,
        min_value=0,
        max_value=420,
        step=0.1,
        multiplier=0.1,
        translation_key="illuminance_threshold",
        fallback_name="Illuminance threshold",
    )
    .tuya_enum(
        dp_id=111,
        attribute_name="breaker_polarity",
        enum_class=TuyaBreakerPolarity,
        translation_key="breaker_polarity",
        fallback_name="Breaker polarity",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="block_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        translation_key="block_time",
        fallback_name="Block time",
    )
    # 113 parameter_setting_result, z2m doesn't expose
    # 114 factory_parameters, z2m doesn't expose
    .tuya_enum(
        dp_id=115,
        attribute_name="sensor_mode",
        enum_class=TuyaMotionSensorMode,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_muvkrjr5", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=13,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=1.5,
        max_value=6.0,
        step=0.75,
        multiplier=0.01,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=16,
        attribute_name="motion_sensitivity",
        type=t.uint16_t,
        min_value=68,
        max_value=90,
        step=1,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .tuya_sensor(
        dp_id=19,
        attribute_name="target_distance",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        entity_type=EntityType.STANDARD,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .tuya_binary_sensor(
        dp_id=101,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    # 102 is ignored, per z2m
    .tuya_number(
        dp_id=103,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=3,
        max_value=1799,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_kyhbrfyl", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_enum(
        dp_id=11,
        attribute_name="human_motion_state",
        enum_class=TuyaHumanMotionState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="human_motion_state",
        fallback_name="Human motion state",
    )
    .tuya_number(
        dp_id=12,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=3,
        max_value=600,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_number(
        dp_id=13,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=150,
        max_value=600,
        step=1,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=15,
        attribute_name="radar_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=7,
        step=1,
        translation_key="radar_sensitivity",
        fallback_name="Radar sensitivity",
    )
    .tuya_number(
        dp_id=16,
        attribute_name="presence_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=7,
        step=1,
        translation_key="presence_sensitivity",
        fallback_name="Presence sensitivity",
    )
    .tuya_sensor(
        dp_id=19,
        attribute_name="target_distance",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        entity_type=EntityType.STANDARD,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .skip_configuration()
    .add_to_registry()
)


# Heimen HS80S-TY
(
    TuyaQuirkBuilder("_TZ6210_duv6fhwt", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .tuya_illuminance(dp_id=101)
    .adds(TuyaOccupancySensing)
    .tuya_switch(
        dp_id=102,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .tuya_binary_sensor(
        dp_id=103,
        attribute_name="tamper",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Tamper",
    )
    .tuya_number(
        dp_id=104,
        attribute_name="motionless_detection",
        type=t.uint16_t,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="motionless_detection",
        fallback_name="Motionless detection",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=1,
        max_value=30,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .skip_configuration()
    .add_to_registry()
)


# NEO NAS-PS10B2
(
    TuyaQuirkBuilder("_TZE204_1youk3hj", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_enum(
        dp_id=11,
        attribute_name="human_motion_state",
        enum_class=TuyaHumanMotionState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="human_motion_state",
        fallback_name="Human motion state",
    )
    .tuya_number(
        dp_id=12,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=3,
        max_value=600,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_number(
        dp_id=13,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=150,
        max_value=600,
        step=75,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=15,
        attribute_name="radar_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=7,
        step=1,
        translation_key="radar_sensitivity",
        fallback_name="Radar sensitivity",
    )
    .tuya_sensor(
        dp_id=19,
        attribute_name="target_distance",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        entity_type=EntityType.STANDARD,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .tuya_number(
        dp_id=16,
        attribute_name="motionless_sensitivity",
        type=t.uint8_t,
        min_value=0,
        max_value=7,
        step=1,
        translation_key="motionless_sensitivity",
        fallback_name="Motionless detection sensitivity",
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="work_mode",
        enum_class=TuyaMotionWorkMode,
        entity_type=EntityType.STANDARD,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    .tuya_illuminance(
        dp_id=102,
        converter=lambda x: {0: 10, 1: 20, 2: 50, 3: 100}[x],
    )
    .tuya_number(
        dp_id=103,
        attribute_name="output_time",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=10,
        max_value=1800,
        step=1,
        translation_key="output_time",
        fallback_name="Output time",
    )
    .tuya_switch(
        dp_id=104,
        attribute_name="output_switch",
        entity_type=EntityType.STANDARD,
        translation_key="output_switch",
        fallback_name="Output switch",
    )
    .tuya_switch(
        dp_id=105,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .skip_configuration()
    .add_to_registry()
)


# TuyaZG-204ZL
(
    TuyaQuirkBuilder("_TZE200_3towulqd", "TS0601")
    .applies_to("_TZE200_1ibpyhdc", "TS0601")
    .applies_to("_TZE200_bh3n6gk8", "TS0601")
    .applies_to("_TZE200_ttcovulf", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 0,
    )
    .adds(TuyaOccupancySensing)
    .tuya_battery(dp_id=4)
    .tuya_enum(
        dp_id=9,
        attribute_name="presence_sensitivity",
        enum_class=TuyaMotionPresenceSensitivity,
        translation_key="presence_sensitivity",
        fallback_name="Presence sensitivity",
    )
    .tuya_enum(
        dp_id=10,
        attribute_name="fading_time",
        enum_class=TuyaMotionFadeTime,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_illuminance(dp_id=12)
    .tuya_number(
        dp_id=105,
        attribute_name="illuminance_interval",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=1,
        max_value=720,
        step=1,
        translation_key="illuminance_interval",
        fallback_name="Illuminance interval",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya Mini human breath sensor ZY-M100-S_1
(
    TuyaQuirkBuilder("_TZE204_sxm7l9xa", "TS0601")
    .applies_to("_TZE204_e5m9c5hl", "TS0601")
    .tuya_illuminance(dp_id=104)
    .tuya_dp(
        dp_id=105,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=106,
        attribute_name="radar_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=9,
        step=1,
        translation_key="radar_sensitivity",
        fallback_name="Radar sensitivity",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=0,
        max_value=950,
        step=15,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=0,
        max_value=950,
        step=15,
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
    )
    .tuya_sensor(
        dp_id=109,
        attribute_name="target_distance",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        entity_type=EntityType.STANDARD,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=1500,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_number(
        dp_id=111,
        attribute_name="detection_delay",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya PIR Motion Sensor ZM-35ZH-Q occupancy sensor
(
    TuyaQuirkBuilder("_TZE200_gjldowol", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_battery(dp_id=4)
    .tuya_enum(
        dp_id=9,
        attribute_name="motion_sensitivity",
        enum_class=TuyaSensitivityMode,
        translation_key="motion_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .tuya_illuminance(dp_id=12)
    .tuya_number(
        dp_id=101,
        attribute_name="illuminance_interval",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=1,
        max_value=720,
        step=1,
        translation_key="illuminance_interval",
        fallback_name="Illuminance interval",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="fading_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=3600,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya ZG-205Z/A, 5.8Ghz/24Ghz Human presence sensor.
(
    TuyaQuirkBuilder("_TZE200_2aaelwxk", "TS0225")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=2,
        attribute_name="large_motion_detection_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="large_motion_detection_sensitivity",
        fallback_name="Motion detection sensitivity",
    )
    .tuya_number(
        dp_id=4,
        attribute_name="large_motion_detection_distance",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=10,
        step=1,
        multiplier=0.01,
        translation_key="large_motion_detection_distance",
        fallback_name="Motion detection distance",
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="motion_state",
        enum_class=TuyaPresenceStateV02,
        translation_key="motion_state",
        fallback_name="Motion state",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="presence_timeout",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=28800,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_number(
        dp_id=104,
        attribute_name="medium_motion_detection_distance",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=6,
        step=0.01,
        multiplier=0.01,
        translation_key="medium_motion_detection_distance",
        fallback_name="Medium motion detection distance",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="medium_motion_detection_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="medium_motion_detection_sensitivity",
        fallback_name="Medium motion detection sensitivity",
    )
    .tuya_illuminance(dp_id=106)
    .tuya_switch(
        dp_id=107,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="small_motion_detection_distance",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=6,
        step=0.01,
        multiplier=0.01,
        translation_key="small_motion_detection_distance",
        fallback_name="Small motion detection distance",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="small_motion_detection_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="small_motion_detection_sensitivity",
        fallback_name="Small motion detection sensitivity",
    )
    # Remaining DPs not exposed in z2m.
    .skip_configuration()
    .add_to_registry()
)


# Tuya PIR 24Ghz human presence sensor, ZG-204ZM
(
    TuyaQuirkBuilder("_TZE200_2aaelwxk", "TS0601")
    .applies_to("_TZE200_kb5noeto", "TS0601")
    .applies_to("HOBEIAN", "ZG-204ZM")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=2,
        attribute_name="static_detection_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="static_detection_sensitivity",
        fallback_name="Static detection sensitivity",
    )
    .tuya_number(
        dp_id=4,
        attribute_name="static_detection_distance",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=10,
        step=1,
        multiplier=0.01,
        translation_key="static_detection_distance",
        fallback_name="Static detection distance",
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="human_motion_state",
        enum_class=TuyaHumanMotionStateV02,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="human_motion_state",
        fallback_name="Human motion state",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="presence_timeout",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=28800,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_illuminance(dp_id=106)
    .tuya_switch(
        dp_id=107,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .tuya_battery(dp_id=121)
    .tuya_enum(
        dp_id=122,
        attribute_name="motion_detection_mode",
        enum_class=TuyaMotionDetectionMode,
        translation_key="motion_detection_mode",
        fallback_name="Motion detection mode",
    )
    .tuya_number(
        dp_id=123,
        attribute_name="motion_detection_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="motion_detection_sensitivity",
        fallback_name="Motion detection sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya mmWave radar 5.8GHz, ZY_HPS01
(
    TuyaQuirkBuilder("_TZE204_ex3rcdha", "TS0601")
    .tuya_illuminance(dp_id=12)
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 0,
    )
    .adds(TuyaOccupancySensing)
    .tuya_number(
        dp_id=104,
        attribute_name="presence_timeout",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=180,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="move_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="move_sensitivity",
        fallback_name="Motion sensitivity",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="breath_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="breath_sensitivity",
        fallback_name="Breath sensitivity",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=0,
        max_value=600,
        step=1,
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=0,
        max_value=600,
        step=1,
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
    )
    .tuya_number(
        dp_id=111,
        attribute_name="breath_detection_min",
        type=t.uint16_t,
        min_value=0,
        max_value=600,
        step=10,
        unit=UnitOfLength.CENTIMETERS,
        translation_key="breath_detection_min",
        fallback_name="Breath detection min",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="breath_detection_max",
        type=t.uint16_t,
        min_value=0,
        max_value=600,
        step=10,
        unit=UnitOfLength.CENTIMETERS,
        translation_key="breath_detection_max",
        fallback_name="Breath detection max",
    )
    .skip_configuration()
    .add_to_registry()
)
