"""Linkind window/door sensor (ZB-DoorSensor-D0003)."""
# Adds tampering sensor as separate on/off sensor
# Mauer, 09-02-2022
import logging
from typing import Any, List, Optional, Union

import zigpy.profiles.zha
from zigpy.zcl import foundation

from zigpy.quirks import CustomDevice, CustomCluster
from zhaquirks import Bus
from zigpy.zcl.clusters.homeautomation import Diagnostic
import zigpy.types as t

from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.linkind import LinkindBasicCluster

_LOGGER = logging.getLogger(__name__)


class LinKindIasZone(CustomCluster, IasZone):
    """IasZone cluster,  used extract the tamper bit from IasZone.ZoneStatus."""

    cluster_id = IasZone.cluster_id
    manufacturer_client_commands = {
        0x0000: (
            "status_change_notification",
            (
                IasZone.ZoneStatus,
                t.bitmap8,
                t.Optional(t.uint8_t),
                t.Optional(t.uint16_t),
            ),
            False,
        )
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == 0:
            state = bool(
                args[0] & 4
            )  # check if fourth bit (tamper alarm) is set, if so  set bit of Alarm 1 high. (HA only checks Alarm_1 and Alarm_2 and ignores tamper/battery...
            self.endpoint.device.ias_bus.listener_event("update_state", state)


class LinKindTamperOnOff(CustomCluster, OnOff):
    """OnOff cluster report tamper status."""

    cluster_id = OnOff.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ias_bus.add_listener(self)

    def update_state(self, value):
        """Report new Alarm."""
        self._update_attribute(0, value)


class ZBDoorSensorD0003(CustomDevice):
    """Linkind Door Sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("lk", "ZB-DoorSensor-D0003")],
        ENDPOINTS: {
            # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=1026
            # device_version=0
            # input_clusters=[0, 1, 3, 32, 1280, 2821] 0x0000, 0x0001, 0x0003, 0x0020, 0x0500, 0x0b05
            # 0x0000 = basic, 0x0001 = powerconfiguration, 0x0003 = identify, 0x0020 = pollcontrol, 0x0500 = IasZone, 0x0b05 = Diagnostic
            # output_clusters=[25]
            #
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    PollControl.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    LinkindBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LinKindIasZone,
                    PollControl.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [LinKindTamperOnOff, Ota.cluster_id],
            },
        },
    }
