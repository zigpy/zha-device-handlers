from zigpy.profiles import PROFILES, zha, zll
from zigpy.zcl.clusters.general import Basic, OnOff, Identify,\
    Ota, LevelControl, PowerConfiguration, Scenes, BinaryInput,\
    Groups
from zhaquirks import EventableCluster
from zigpy.quirks import CustomDevice


DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class PhilipsRWL021(CustomDevice):

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
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2096
        #  device_version=2
        #  input_clusters=[0]
        #  output_clusters=[0, 3, 4, 6, 8, 5]>
        1: {
            'profile_id': zll.PROFILE_ID,
            'device_type': zll.DeviceType.SCENE_CONTROLLER,
            'input_clusters': [
                Basic.cluster_id
            ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                EventableOnOffCluster.cluster_id,
                EventableLevelControlCluster.cluster_id,
                Scenes.cluster_id
            ],
        },
        #  <SimpleDescriptor endpoint=2 profile=260 device_type=12
        #  device_version=0
        #  input_clusters=[0, 1, 3, 15, 64512]
        #  output_clusters=[25]>
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.SIMPLE_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id,
                BinaryInput.cluster_id,
                64512
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    EventableOnOffCluster,
                    EventableLevelControlCluster,
                    Scenes.cluster_id
                ],
            },
            2: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    64512
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
        },
    }
