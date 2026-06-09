"""Device handler for Terncy awareness switch."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder

from zhaquirks import Bus, DoublingPowerConfigurationCluster
from zhaquirks.terncy import (
    BUTTON_TRIGGERS,
    IlluminanceMeasurementCluster,
    MotionClusterLeft,
    MotionClusterRight,
    OccupancyCluster,
    TemperatureMeasurementCluster,
    TerncyRawCluster,
)

TERNCY_AWARENESS_DEVICE_TYPE = 0x01F0


class TerncyAwarenessSwitchV2(CustomDeviceV2):
    """Terncy awareness switch."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_left_bus = Bus()
        self.motion_right_bus = Bus()
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder("Xiaoyan", "TERNCY-PP01")
    .applies_to("Terncy", "TERNCY-PP01")
    .device_class(TerncyAwarenessSwitchV2)
    .replaces(DoublingPowerConfigurationCluster, endpoint_id=1)
    .replaces(IlluminanceMeasurementCluster, endpoint_id=1)
    .replaces(TemperatureMeasurementCluster, endpoint_id=1)
    .replaces(OccupancyCluster, endpoint_id=1)
    .replaces(TerncyRawCluster, endpoint_id=1)
    .adds(MotionClusterLeft, endpoint_id=1)
    .adds_endpoint(
        endpoint_id=2,
        profile_id=zha.PROFILE_ID,
        device_type=TERNCY_AWARENESS_DEVICE_TYPE,
    )
    .adds(MotionClusterRight, endpoint_id=2)
    .device_automation_triggers(BUTTON_TRIGGERS)
    .add_to_registry()
)
