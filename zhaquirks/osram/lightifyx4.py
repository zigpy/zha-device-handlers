"""Osram Lightify X4 device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Ota, PollControl,
    PowerConfiguration, Scenes)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
import zigpy.types as t

OSRAM_DEVICE = 0x0810  # 2064 base 10
OSRAM_CLUSTER = 0xFD00  # 64768 base 10
OSRAM_MFG_CODE = 0x110c


_LOGGER = logging.getLogger(__name__)


class LightifyX4(CustomDevice):
    """Osram Lightify X4 device."""

    class OsramButtonCluster(CustomCluster):
        """OsramButtonCluster."""

        cluster_id = OSRAM_CLUSTER
        name = 'OsramCluster'
        ep_attribute = 'osram_cluster'
        attributes = {
            0x000A: ('osram_1', t.uint8_t),
            0x000B: ('osram_2', t.uint8_t),
            0x000C: ('osram_3', t.uint16_t),
            0x000D: ('osram_4', t.uint16_t),
            0x0019: ('osram_5', t.uint8_t),
            0x001A: ('osram_6', t.uint16_t),
            0x001B: ('osram_7', t.uint16_t),
            0x001C: ('osram_8', t.uint8_t),
            0x001D: ('osram_9', t.uint16_t),
            0x001E: ('osram_10', t.uint16_t),
            0x002C: ('osram_11', t.uint16_t),
            0x002D: ('osram_12', t.uint16_t),
            0x002E: ('osram_13', t.uint16_t),
            0x002F: ('osram_14', t.uint16_t),
        }
        server_commands = {}
        client_commands = {}
        attr_config = {
            0x000A: 0x01,
            0x000B: 0x00,
            0x000C: 0xFFFF,
            0x000D: 0xFFFF,
            0x0019: 0x06,
            0x001A: 0x0001,
            0x001B: 0x0026,
            0x001C: 0x07,
            0x001D: 0xFFFF,
            0x001E: 0xFFFF,
            0x002C: 0xFFFF,
            0x002D: 0xFFFF,
            0x002E: 0xFFFF,
            0x002F: 0xFFFF
        }

        async def bind(self):
            """Bind cluster."""
            result = await super().bind()
            await self.write_attributes(
                self.attr_config,
                manufacturer=OSRAM_MFG_CODE
            )
            return result

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2064
        #  device_version=2
        #  input_clusters=[0, 1, 32, 4096, 64768]
        #  output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
        'models_info': [
            ('OSRAM', 'Switch 4x-LIGHTIFY')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER,
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            2: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            3: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            4: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            # <SimpleDescriptor endpoint=5 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            5: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            # <SimpleDescriptor endpoint=6 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            6: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OsramButtonCluster,
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            2: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OsramButtonCluster
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            3: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OsramButtonCluster
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            4: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OsramButtonCluster
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            5: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            6: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
        }
    }
