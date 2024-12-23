"""BlitzWolf IS-3/Tuya motion rechargeable occupancy sensor."""

import asyncio
import math
from typing import Any

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfLength, UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaIlluminanceCluster(IlluminanceMeasurement, TuyaLocalCluster):
    """Tuya Illuminance cluster."""


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
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
    )
    .tuya_sensor(
        dp_id=9,
        attribute_name="distance",
        type=t.uint16_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        entity_type=EntityType.STANDARD,
        translation_key="distance",
        fallback_name="Target distance",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="find_switch",
        fallback_name="Distance switch",
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
    .adds(TuyaIlluminanceCluster)
    .skip_configuration()
)

(
    base_tuya_motion.clone()
    .applies_to("_TZE200_ya4ft0w4", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: True if x in (1, 2) else False,
    )
    .tuya_dp(
        dp_id=103,
        ep_attribute=TuyaIlluminanceCluster.ep_attribute,
        attribute_name=TuyaIlluminanceCluster.AttributeDefs.measured_value.name,
        converter=lambda x: 10000 * math.log10(x) + 1 if x != 0 else 0,
    )
    .tuya_number(
        dp_id=105,
        attribute_name="presence_timeout",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=15000,
        step=1,
        translation_key="presence_timeout",
        fallback_name="Fade time",
    )
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
    base_tuya_motion.clone()
    .applies_to("_TZE200_ar0slwnd", "TS0601")
    .applies_to("_TZE200_mrf6vtua", "TS0601")
    .applies_to("_TZE200_sfiy5tfs", "TS0601")
    .applies_to("_TZE204_sooucan5", "TS0601")
    .applies_to("_TZE200_wukb7rhc", "TS0601")
    .applies_to("_TZE204_qasjif9e", "TS0601")
    .applies_to("_TZE200_ztc6ggyl", "TS0601")
    .applies_to("_TZE204_ztc6ggyl", "TS0601")
    .applies_to("_TZE204_ztqnh5cg", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda x: x == 1,
    )
    # 103?
    .tuya_dp(
        dp_id=104,
        ep_attribute=TuyaIlluminanceCluster.ep_attribute,
        attribute_name=TuyaIlluminanceCluster.AttributeDefs.measured_value.name,
        converter=lambda x: 10000 * math.log10(x) + 1 if x != 0 else 0,
    )
    # 106?
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
