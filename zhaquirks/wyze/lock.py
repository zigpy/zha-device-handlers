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

from . import YUNDING
from .. import Bus
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

WYZE_CLUSTER_ID = 0xFC00

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
        self.warning("argument: %s", ",".join(map(str, args)))
        if args[41] == 165:
            self.warning("the lock is unlocked")
            self.endpoint.device.lock_bus.listener_event("lock_event", 2)
        elif args[41] == 162:
            self.warning("the lock is locked")
            self.endpoint.device.lock_bus.listener_event("lock_event", 1)


class WyzeLock(CustomDevice):
    """Wyze lock device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.lock_bus = Bus()
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
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id, WyzeCluster],
            }
        }
    }
