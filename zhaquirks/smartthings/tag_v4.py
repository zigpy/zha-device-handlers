"""Device handler for smartthings tagV4 sensors."""

from typing import Any

from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput

from zhaquirks import Bus, LocalDataCluster, PowerConfigurationCluster

ARRIVAL_SENSOR_DEVICE_TYPE = 0x8000


class FastPollingPowerConfigurationCluster(PowerConfigurationCluster):
    """FastPollingPowerConfigurationCluster."""

    FREQUENCY = 45
    MINIMUM_CHANGE = 1

    async def configure_reporting(
        self,
        attribute,
        min_interval,
        max_interval,
        reportable_change,
        manufacturer=None,
    ):
        """Configure reporting."""
        result = await super().configure_reporting(
            PowerConfigurationCluster.BATTERY_VOLTAGE_ATTR,
            self.FREQUENCY,
            self.FREQUENCY,
            self.MINIMUM_CHANGE,
        )
        return result

    def _update_attribute(self, attrid, value):
        self.endpoint.device.tracking_bus.listener_event(
            "update_tracking", attrid, value
        )
        super()._update_attribute(attrid, value)


# stealing this for tracking alerts
class TrackingCluster(LocalDataCluster, BinaryInput):
    """Tracking cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.tracking_bus.add_listener(self)

    def update_tracking(self, attrid, value):
        """Update tracking info."""
        # prevent unbounded null entries from going into zigbee.db
        self._update_attribute(0, 1)


class SmartThingsTagV4(CustomDeviceV2):
    """Custom device representing smartthings tagV4 sensors."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        self.tracking_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder("SmartThings", "tagv4")
    .device_class(SmartThingsTagV4)
    .replaces_endpoint(1, device_type=ARRIVAL_SENSOR_DEVICE_TYPE)  # was SIMPLE_SENSOR
    .replaces(FastPollingPowerConfigurationCluster, endpoint_id=1)
    .replaces(TrackingCluster, endpoint_id=1)
    .add_to_registry()
)
