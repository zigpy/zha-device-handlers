import logging
import homeassistant.components.zha.const as zha_const
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, PowerConfiguration, Identify
from zhaquirks.xiaomi import BasicCluster, PowerConfigurationCluster,\
    TemperatureMeasurementCluster, XiaomiCustomDevice
from zhaquirks import CustomCluster

BUTTON_DEVICE_TYPE = 0x0104
BUTTON_DEVICE_TYPE_REPLACEMENT = 0x6FF1
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

PROFILES[zha.PROFILE_ID].CLUSTERS[BUTTON_DEVICE_TYPE_REPLACEMENT] = (
    [
        BasicCluster.cluster_id,
        OnOff.cluster_id
    ],
    [
        BasicCluster.cluster_id,
        Groups.cluster_id
    ]
)

zha_const.DEVICE_CLASS[zha.PROFILE_ID].update(
    {
        BUTTON_DEVICE_TYPE_REPLACEMENT: 'sensor'
    }
)


class MijaButton(XiaomiCustomDevice):

    def __init__(self, *args, **kwargs):
        self.battery_size = 9
        super().__init__(*args, **kwargs)

    class MijaOnOff(OnOff):
        cluster_id = OnOff.cluster_id

        def __init__(self, *args, **kwargs):
            self._currentState = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):                        
            # Handle Mija OnOff
            if(attrid == 0):
                if(value):
                    value = False
                else:
                    value = True
                    
            # Handle Multi Clicks
            if(attrid == 32768):
                updateAttrib = False
                click_type = value
                if(click_type == 2):
                    click_type = 'double'
                elif(click_type == 3):
                    click_type = 'triple'
                elif(click_type == 4):
                    click_type = 'quadruple'
                elif(click_type == 128):
                    click_type = 'furious'
                else:
                    click_type = 'unknown'
                
                
                self.listener_event(
                    'zha_send_event',
                    self,
                    'click',
                    {'click_type':click_type}
                )
                
            super()._update_attribute(attrid, value)


    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 6, 65535]
        # output_clusters=[0, 4, 65535]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': BUTTON_DEVICE_TYPE,
            # 'input_clusters': [
            #     Basic.cluster_id,
            #     OnOff.cluster_id,
            #     XIAOMI_CLUSTER_ID
            # ],
            # 'output_clusters': [
            #     Basic.cluster_id,
            #     Groups.cluster_id,
            #     XIAOMI_CLUSTER_ID
            # ],
            'input_clusters': [
                0,
                3,
                25,
                XIAOMI_CLUSTER_ID
            ],
            'output_clusters': [
                0,
                3,
                4,
                5,
                6,
                8,
                25
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_switch.v1',
                'device_type': BUTTON_DEVICE_TYPE_REPLACEMENT,
                'input_clusters': [
                    Identify.cluster_id,
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    MijaOnOff
                ],
            }
        },
    }
