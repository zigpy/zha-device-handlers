"""Quirk for aqara lumi.motion.ac01."""
from __future__ import annotations

import logging
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as types
from zigpy.zcl.clusters.general import Basic, Identify, MultistateInput, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import APPROACH_DISTANCE, XiaomiAqaraE1Cluster

OCCUPANCY = 0x0000
PRESENT_VALUE = 0x0055
PRESENCE = 0x0142
PRESENCE2 = 101
PRESENCE_EVENT = 0x0143
PRESENCE_EVENT2 = 102
MONITORING_MODE = 0x0144
MOTION_SENSITIVITY = 0x010C
RESET_NO_PRESENCE_STATUS = 0x0157

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
        PRESENCE: ("presence", types.Bool, True),
        MONITORING_MODE: ("monitoring_mode", types.uint8_t, True),
        MOTION_SENSITIVITY: ("motion_sensitivity", types.uint8_t, True),
        APPROACH_DISTANCE: ("approach_distance", types.uint8_t, True),
        RESET_NO_PRESENCE_STATUS: ("reset_no_presence_status", types.uint8_t, True),
    }

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == PRESENCE or attrid == PRESENCE2:
            self.endpoint.occupancy.update_attribute(OCCUPANCY, value)
        elif attrid == PRESENCE_EVENT or attrid == PRESENCE_EVENT2:
            self.endpoint.multistate_input.update_attribute(
                PRESENT_VALUE, AqaraPresenceEvents(value).name.replace("_", " ")
            )


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
                    OccupancySensing,
                    MultistateInput,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
