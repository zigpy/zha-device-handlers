"""Linxura button device."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.linxura import LINXURA, LinxuraIASCluster


class LinxuraButton(CustomDevice):
    """Linxura button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 3, 1280]
        # output_clusters=[3]>
        MODELS_INFO: [(LINXURA, BUTTON)],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    LinxuraIASCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        }
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_BUTTON_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_BUTTON_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_BUTTON_HOLD},
    }

