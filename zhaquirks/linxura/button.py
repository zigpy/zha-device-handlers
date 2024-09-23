
"""Linxura Button Remote."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_SINGLE,
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
from zhaquirks.Linxura import LINXURA, LinxuraOnOffCluster

Linxura_CLUSTER_ID = 0xFCC1


class LinxuraButtonRemote1(CustomDevice):
    """Linxura 1-button remote device."""


    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2
        # device_version=0
        # input_clusters=[0, 3, 6, 64704]
        # output_clusters=[3, 64704]>
        MODELS_INFO: [(LINXURA, BUTTON)],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Linxura_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Linxura_CLUSTER_ID],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    LinxuraOnOffCluster,
                    Linxura_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Linxura_CLUSTER_ID,
                ],
            },
        },
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
    }
