"""Support for the Wyze lock."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasZone

from . import YUNDING
from .. import Bus, LocalDataCluster
from ..const import (
    CLUSTER_COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    OFF,
    ON,
    ZONE_STATE,
)

WYZE_CLUSTER_ID = 0xFC00
ZONE_TYPE = 0x0001

_LOGGER = logging.getLogger(__name__)


class DoorLockCluster(CustomCluster, DoorLock):
    """DoorLockCluster cluster."""

    cluster_id = DoorLock.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.lock_bus.add_listener(self)

    def lock_event(self, locked):
        """Motion event."""
        self._update_attribute(0x0000, locked)


class MotionCluster(LocalDataCluster, IasZone):
    """Motion cluster."""

    cluster_id = IasZone.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.motion_bus.add_listener(self)
        super()._update_attribute(ZONE_TYPE, IasZone.ZoneType.Contact_Switch)

    def motion_event(self, zone_state):
        """Motion event."""
        super().listener_event(CLUSTER_COMMAND, None, ZONE_STATE, [zone_state])
        _LOGGER.debug("%s - Received motion event message", self.endpoint.device.ieee)


class WyzeCluster(CustomCluster, Basic):
    """Wyze manufacturer specific cluster implementation."""

    cluster_id = WYZE_CLUSTER_ID
    ep_attribute = "wyze_lock_cluster"
    attributes = {}
    server_commands = {}
    client_commands = {}

    def handle_message(self, hdr, args):
        """Handle a message on this cluster."""
        self.debug("ZCL request 0x%04x: %s", hdr.command_id, args)
        i = 0
        for arg in args:
            self.info("index: %s value: %s", i, arg)
            i += 1
        self.warning("argument: %s", ",".join(map(str, args)))
        if len(args) < 70:
            return

        if args[52] == 180 and args[41] == 165:
            self.warning("the lock is unlocked via the app")
            self.endpoint.device.lock_bus.listener_event("lock_event", 2)
        elif args[52] == 180 and args[41] == 162:
            self.warning("the lock is locked via the app")
            self.endpoint.device.lock_bus.listener_event("lock_event", 1)
        elif args[52] == 176 and args[41] == 165:
            self.warning("the lock is unlocked manually")
            self.endpoint.device.lock_bus.listener_event("lock_event", 2)
        elif args[52] == 176 and args[41] == 162:
            self.warning("the lock is locked manually")
            self.endpoint.device.lock_bus.listener_event("lock_event", 1)
        elif args[52] == 189 and args[41] == 162:
            self.warning("the lock is locked via auto lock")
            self.endpoint.device.lock_bus.listener_event("lock_event", 1)
        if args[52] == 74 and args[41] == 177:
            self.warning("the door is open")
            self.endpoint.device.motion_bus.listener_event("motion_event", ON)
        elif args[52] == 74 and args[41] == 178:
            self.warning("the door is closed")
            self.endpoint.device.motion_bus.listener_event("motion_event", OFF)


class WyzeLock(CustomDevice):
    """Wyze lock device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.lock_bus = Bus()
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=10
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 257, 2821, 64512]
        # output_clusters=[10, 25, 64512]>
        MODELS_INFO: [(YUNDING, "Ford")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    DoorLock.cluster_id,
                    Diagnostic.cluster_id,
                    WYZE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id, WYZE_CLUSTER_ID],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    DoorLockCluster,
                    Diagnostic.cluster_id,
                    WyzeCluster,
                    MotionCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id, WyzeCluster],
            }
        }
    }
