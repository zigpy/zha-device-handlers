"""Device handler for CentraLite 3400-G."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasAce, IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent, PowerConfigurationCluster
from zhaquirks.const import MOTION_EVENT

CENTRALITE = "CentraLite"
ZONE_TYPE = 0x0001


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster for CR123A batteries."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


class MotionCluster(LocalDataCluster, MotionOnEvent, IasZone):
    """Virtual motion sensor cluster."""

    # Force zone type to Motion Sensor
    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Motion_Sensor}

    # Reset motion after 90 seconds
    reset_s = 90

    # Skip configuration for virtual cluster
    SKIP_CONFIGURATION = True


class CustomIasAce(CustomCluster, IasAce):
    """Custom IAS ACE cluster to detect GetPanelStatus as motion trigger."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list,
        *,
        dst_addressing: t.Addressing.Group
        | t.Addressing.IEEE
        | t.Addressing.NWK
        | None = None,
    ):
        """Handle cluster request - detect GetPanelStatus (0x07) as motion event."""
        # GetPanelStatus command - keypad sends this when it wakes up from motion
        if hdr.command_id == IasAce.ServerCommandDefs.get_panel_status.id:
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)

        return super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class CentraLiteDeviceV2(CustomDeviceV2):
    """Custom device class for CentraLite 3400-G with motion bus."""

    def __init__(self, *args, **kwargs):
        """Init device with motion bus."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(CENTRALITE, "3400-G")
    .replaces(CustomPowerConfigurationCluster)
    .replaces(CustomIasAce, cluster_type="output")
    .adds_endpoint(2, device_type=zha.DeviceType.OCCUPANCY_SENSOR)
    .adds(MotionCluster, endpoint_id=2)
    .device_class(CentraLiteDeviceV2)
    .add_to_registry()
)
