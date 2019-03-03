import logging
import homeassistant.components.zha.const as zha_const
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import LevelControl, Ota, Basic, Groups, OnOff,\
     Identify, Scenes
from zhaquirks.xiaomi import BasicCluster, PowerConfigurationCluster,\
     XiaomiCustomDevice
from zhaquirks import CustomCluster

XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

click_type_map = {
 2: 'double',
 3: 'triple',
 4: 'quadruple',
 128: 'furious',
}

class MijaButton(XiaomiCustomDevice):

    def __init__(self, *args, **kwargs):
        self.battery_size = 9
        super().__init__(*args, **kwargs)

    class MijaOnOff(CustomCluster, OnOff):
        cluster_id = OnOff.cluster_id

        def __init__(self, *args, **kwargs):
            self._currentState = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            click_type = False

            # Handle Mija OnOff
            if(attrid == 0):
                value = False if value else True
                click_type = 'single' if value == True else False

            # Handle Multi Clicks
            elif(attrid == 32768):
                click_type = click_type_map.get(value,'unknown')

            if click_type:
                self.listener_event(
                    'zha_send_event',
                    self,
                    'click',
                    {'click_type':click_type}
                )

            super()._update_attribute(attrid, value)


    signature = {
        # Endpoints:
        #   1: profile=0x104, device_type=DeviceType.DIMMER_SWITCH
        #     Input Clusters:
        #       Basic (0)
        #       Identify (3)
        #       Ota (25)
        #       Manufacturer Specific (65535)
        #     Output Clusters:
        #       Basic (0)
        #       Identify (3)
        #       Groups (4)
        #       Scenes (5)
        #       On/Off (6)
        #       Level control (8)
        #       Ota (25)
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_switch',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DIMMER_SWITCH,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                XIAOMI_CLUSTER_ID
            ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Ota.cluster_id,
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_switch',
                'device_type': zha.DeviceType.REMOTE_CONTROL,
                'input_clusters': [
                    Identify.cluster_id,
                    BasicCluster,
                    PowerConfigurationCluster,
                ],
                'output_clusters': [
                    BasicCluster,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    MijaOnOff,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }
