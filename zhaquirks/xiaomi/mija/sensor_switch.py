"""Xiaomi mija button device."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Ota, Scenes)

from zhaquirks import CustomCluster
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice)

XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

CLICK_TYPE_MAP = {
    2: 'double',
    3: 'triple',
    4: 'quadruple',
    128: 'furious',
}


class MijaButton(XiaomiCustomDevice):
    """Mija button device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 10
        super().__init__(*args, **kwargs)

    class MijaOnOff(CustomCluster, OnOff):
        """Mija on off cluster."""

        cluster_id = OnOff.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            click_type = False

            # Handle Mija OnOff
            if attrid == 0:
                value = not value
                click_type = 'single' if value is True else False

            # Handle Multi Clicks
            elif attrid == 32768:
                click_type = CLICK_TYPE_MAP.get(value, 'unknown')

            if click_type:
                self.listener_event(
                    'zha_send_event',
                    self,
                    'click',
                    {'click_type': click_type}
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
