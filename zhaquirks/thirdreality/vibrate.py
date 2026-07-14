"""Third Reality vibration sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import DEGREE, UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityVibrationSensorCluster(CustomCluster):
    """Third Reality's vibration private cluster."""

    cluster_id = 0xFFF1

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # Raw acceleration values (reported on movement events).
        x_acceleration: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.int16s,
            access="rp",
            manufacturer_code=None,
        )
        y_acceleration: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.int16s,
            access="rp",
            manufacturer_code=None,
        )
        z_acceleration: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.int16s,
            access="rp",
            manufacturer_code=None,
        )
        # Cool-down / debounce time for the motion detection (writable).
        cool_down_time: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=None,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RVS01031Z")
    .replaces(ThirdRealityVibrationSensorCluster)
    .number(
        attribute_name=ThirdRealityVibrationSensorCluster.AttributeDefs.cool_down_time.name,
        cluster_id=ThirdRealityVibrationSensorCluster.cluster_id,
        min_value=0,
        max_value=7200,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="cool_down_time",
        fallback_name="Cool down time",
    )
    .sensor(
        attribute_name=ThirdRealityVibrationSensorCluster.AttributeDefs.x_acceleration.name,
        cluster_id=ThirdRealityVibrationSensorCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="x_acceleration",
        fallback_name="X acceleration",
    )
    .sensor(
        attribute_name=ThirdRealityVibrationSensorCluster.AttributeDefs.y_acceleration.name,
        cluster_id=ThirdRealityVibrationSensorCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="y_acceleration",
        fallback_name="Y acceleration",
    )
    .sensor(
        attribute_name=ThirdRealityVibrationSensorCluster.AttributeDefs.z_acceleration.name,
        cluster_id=ThirdRealityVibrationSensorCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="z_acceleration",
        fallback_name="Z acceleration",
    )
    .add_to_registry()
)
