"""Aqara Roller Shade Driver E1 device."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogOutput,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    MultistateOutput,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraRollerE1Cluster,
    XiaomiCustomDevice,
)


class RollerE1AQ(XiaomiCustomDevice):
    """Aqara Roller Shade Driver E1 device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.acn002")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutput.cluster_id,
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraRollerE1Cluster.cluster_id,
                    MultistateOutput.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutput.cluster_id,
                    BasicCluster,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraRollerE1Cluster,
                    MultistateOutput.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
