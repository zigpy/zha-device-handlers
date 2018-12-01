from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, OnOff, Identify,\
    PollControl, Ota, LevelControl
from zhaquirks.centralite import PowerConfigurationCluster
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zhaquirks import EventableCluster
from zigpy.quirks import CustomDevice


DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CentraLite3130(CustomDevice):

    class EventableOnOffCluster(EventableCluster, OnOff):
        cluster_id = OnOff.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    class EventableLevelControlCluster(EventableCluster, LevelControl):
        cluster_id = LevelControl.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 2821]
        #  output_clusters=[3, 6, 8, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.LEVEL_CONTROL_SWITCH,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                DIAGNOSTICS_CLUSTER_ID
            ],
            'output_clusters': [
                Identify.cluster_id,
                EventableOnOffCluster.cluster_id,
                EventableLevelControlCluster.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'manufacturer': 'CentraLite',
        'model': '3130',
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    EventableOnOffCluster,
                    EventableLevelControlCluster,
                    Ota.cluster_id
                ],
            }
        },
    }
