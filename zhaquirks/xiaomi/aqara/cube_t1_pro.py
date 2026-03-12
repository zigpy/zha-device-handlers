"""Xiaomi Aqara Cube T1 Pro quirk."""

import logging

from zigpy.profiles import zha
import zigpy.types as t

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)
from zhaquirks.xiaomi.aqara.cube_aqgl01 import (
    ACTIVATED_FACE,
    FLIP,
    XIAOMI_SENSORS_REPLACEMENT,
    AnalogInputCluster,
    CubeAQGL01,
    MultistateInputCluster,
)

_LOGGER = logging.getLogger(__name__)


class OppleCluster(CustomCluster):
    """Opple cluster for Aqara Cube T1 Pro face status."""

    cluster_id = 0xFCC0
    name = "opple_cluster"
    ep_attribute = "opple_cluster"

    attributes = {
        0x0147: ("flip_event", t.uint8_t, True),
        0x0149: ("face_status", t.uint8_t, True),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid in (0x0147, 0x0149):
            face = value + 1
            self.listener_event(ZHA_SEND_EVENT, FLIP, {ACTIVATED_FACE: face})


class CustomCubeT1Pro(XiaomiCustomDevice):
    """Aqara Cube T1 Pro custom device."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.remote.cagl02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 259,
                INPUT_CLUSTERS: [0x0000, 0x0001, 0x0003, 0x0006, 0x0012],
                OUTPUT_CLUSTERS: [0x0000, 0x0003, 0x0019],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 259,
                INPUT_CLUSTERS: [0x0012],
                OUTPUT_CLUSTERS: [0x0012],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 259,
                INPUT_CLUSTERS: [0x000C],
                OUTPUT_CLUSTERS: [0x000C],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    OppleCluster,
                    MultistateInputCluster,
                ],
            },
            2: {
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [MultistateInputCluster, OppleCluster],
            },
            3: {
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [AnalogInputCluster, OppleCluster],
            },
        },
    }

    device_automation_triggers = CubeAQGL01.device_automation_triggers
