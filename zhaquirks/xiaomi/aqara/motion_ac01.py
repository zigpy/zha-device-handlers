"""Quirk for aqara lumi.motion.ac01."""
from __future__ import annotations

import logging
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as types
from zigpy.zcl.clusters.general import Basic, DeviceTemperature, Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.const import (
    COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster

OCCUPANCY = 0x0000
PRESENCE = 0x0142
PRESENCE2 = 101
PRESENCE_EVENT = 0x0143
PRESENCE_EVENT2 = 102
MONITORING_MODE = 0x0144
MOTION_SENSITIVITY = 0x010C
APPROACH_DISTANCE = 0x0146
RESET_NO_PRESENCE_STATUS = 0x0157
SENSOR = "sensor"

_LOGGER = logging.getLogger(__name__)


class AqaraPresenceEvents(types.enum8):
    """Aqara presence events."""

    Enter = 0x00
    Leave = 0x01
    Enter_Left = 0x02
    Leave_Right = 0x03
    Enter_Right = 0x04
    Leave_Left = 0x05
    Approach = 0x06
    Away = 0x07
    Unknown = 0xFF


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    ep_attribute = "opple_cluster"
    attributes = {
        PRESENCE: ("presence", types.uint8_t, True),
        MONITORING_MODE: ("monitoring_mode", types.uint8_t, True),
        MOTION_SENSITIVITY: ("motion_sensitivity", types.uint8_t, True),
        APPROACH_DISTANCE: ("approach_distance", types.uint8_t, True),
        RESET_NO_PRESENCE_STATUS: ("reset_no_presence_status", types.uint8_t, True),
    }

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == PRESENCE or attrid == PRESENCE2:
            if value != 0xFF:
                self.endpoint.occupancy.update_attribute(OCCUPANCY, value)
        elif attrid == PRESENCE_EVENT or attrid == PRESENCE_EVENT2:
            self.listener_event(ZHA_SEND_EVENT, AqaraPresenceEvents(value).name, {})


class AqaraLumiMotionAc01(CustomDevice):
    """Aqara lumi.motion.ac01 custom device implementation."""

    signature = {
        MODELS_INFO: [("aqara", "lumi.motion.ac01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xFFF0,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0xFFF0,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    DeviceTemperature.cluster_id,
                    OccupancySensing.cluster_id,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (AqaraPresenceEvents.Enter.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Enter.name
        },
        (AqaraPresenceEvents.Leave.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Leave.name
        },
        (AqaraPresenceEvents.Enter_Left.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Enter_Left.name
        },
        (AqaraPresenceEvents.Leave_Right.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Leave_Right.name
        },
        (AqaraPresenceEvents.Enter_Right.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Enter_Right.name
        },
        (AqaraPresenceEvents.Leave_Left.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Leave_Left.name
        },
        (AqaraPresenceEvents.Approach.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Approach.name
        },
        (AqaraPresenceEvents.Away.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Away.name
        },
        (AqaraPresenceEvents.Unknown.name, SENSOR): {
            COMMAND: AqaraPresenceEvents.Unknown.name
        },
    }
