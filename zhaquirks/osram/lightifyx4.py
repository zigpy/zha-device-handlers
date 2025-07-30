"""Osram Lightify X4 device."""

import copy

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_ON,
    COMMAND_STOP,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.osram import OSRAM

OSRAM_DEVICE = 0x0810  # 2064 base 10
OSRAM_CLUSTER = 0xFD00  # 64768 base 10
OSRAM_MFG_CODE = 0x110C


class OsramButtonCluster(CustomCluster):
    """OsramButtonCluster."""

    cluster_id = OSRAM_CLUSTER
    name = "OsramCluster"
    ep_attribute = "osram_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        osram_1 = ZCLAttributeDef(
            id=0x000A, type=t.uint8_t, is_manufacturer_specific=True
        )
        osram_2 = ZCLAttributeDef(
            id=0x000B, type=t.uint8_t, is_manufacturer_specific=True
        )
        osram_3 = ZCLAttributeDef(
            id=0x000C, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_4 = ZCLAttributeDef(
            id=0x000D, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_5 = ZCLAttributeDef(
            id=0x0019, type=t.uint8_t, is_manufacturer_specific=True
        )
        osram_6 = ZCLAttributeDef(
            id=0x001A, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_7 = ZCLAttributeDef(
            id=0x001B, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_8 = ZCLAttributeDef(
            id=0x001C, type=t.uint8_t, is_manufacturer_specific=True
        )
        osram_9 = ZCLAttributeDef(
            id=0x001D, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_10 = ZCLAttributeDef(
            id=0x001E, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_11 = ZCLAttributeDef(
            id=0x002C, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_12 = ZCLAttributeDef(
            id=0x002D, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_13 = ZCLAttributeDef(
            id=0x002E, type=t.uint16_t, is_manufacturer_specific=True
        )
        osram_14 = ZCLAttributeDef(
            id=0x002F, type=t.uint16_t, is_manufacturer_specific=True
        )

    attr_config = {
        AttributeDefs.osram_1.id: 0x01,
        AttributeDefs.osram_2.id: 0x00,
        AttributeDefs.osram_3.id: 0xFFFF,
        AttributeDefs.osram_4.id: 0xFFFF,
        AttributeDefs.osram_5.id: 0x06,
        AttributeDefs.osram_6.id: 0x0001,
        AttributeDefs.osram_7.id: 0x0026,
        AttributeDefs.osram_8.id: 0x07,
        AttributeDefs.osram_9.id: 0xFFFF,
        AttributeDefs.osram_10.id: 0xFFFF,
        AttributeDefs.osram_11.id: 0xFFFF,
        AttributeDefs.osram_12.id: 0xFFFF,
        AttributeDefs.osram_13.id: 0xFFFF,
        AttributeDefs.osram_14.id: 0xFFFF,
    }

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=OSRAM_MFG_CODE)
        return result


class LightifyX4(CustomDevice):
    """Osram Lightify X4 device."""

    SIGNATURE_ENDPOINT = {
        PROFILE_ID: zha.PROFILE_ID,
        DEVICE_TYPE: OSRAM_DEVICE,
        INPUT_CLUSTERS: [Basic.cluster_id, LightLink.cluster_id, OSRAM_CLUSTER],
        OUTPUT_CLUSTERS: [
            Groups.cluster_id,
            Identify.cluster_id,
            Scenes.cluster_id,
            OnOff.cluster_id,
            Color.cluster_id,
            LevelControl.cluster_id,
            LightLink.cluster_id,
        ],
    }

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2064
        #  device_version=2
        #  input_clusters=[0, 1, 32, 4096, 64768]
        #  output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
        MODELS_INFO: [(OSRAM, "Switch 4x-LIGHTIFY"), (OSRAM, "Switch 4x EU-LIGHTIFY")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: OSRAM_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER,
                ],
                OUTPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            2: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=3 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            3: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=4 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            4: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=5 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            5: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=6 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            6: copy.deepcopy(SIGNATURE_ENDPOINT),
        },
    }

    REPLACEMENT_ENDPOINT = {
        PROFILE_ID: zha.PROFILE_ID,
        DEVICE_TYPE: OSRAM_DEVICE,
        INPUT_CLUSTERS: [Basic.cluster_id, LightLink.cluster_id, OsramButtonCluster],
        OUTPUT_CLUSTERS: [
            Groups.cluster_id,
            Identify.cluster_id,
            Scenes.cluster_id,
            OnOff.cluster_id,
            Color.cluster_id,
            LevelControl.cluster_id,
            LightLink.cluster_id,
        ],
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: OSRAM_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OsramButtonCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            2: copy.deepcopy(REPLACEMENT_ENDPOINT),
            3: copy.deepcopy(REPLACEMENT_ENDPOINT),
            4: copy.deepcopy(REPLACEMENT_ENDPOINT),
            5: copy.deepcopy(REPLACEMENT_ENDPOINT),
            6: copy.deepcopy(REPLACEMENT_ENDPOINT),
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 2},
        (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_ON, ENDPOINT_ID: 3},
        (SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_ON, ENDPOINT_ID: 4},
        (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 2},
        (LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 3},
        (LONG_PRESS, BUTTON_4): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 4},
        (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 1},
        (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
        (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 3},
        (LONG_RELEASE, BUTTON_4): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 4},
    }


class LightifySwitch(CustomDevice):
    """Osram Lightify Switch device."""

    SIGNATURE_ENDPOINT = {
        PROFILE_ID: zha.PROFILE_ID,
        DEVICE_TYPE: OSRAM_DEVICE,
        INPUT_CLUSTERS: [LightLink.cluster_id, OSRAM_CLUSTER],
        OUTPUT_CLUSTERS: [
            Groups.cluster_id,
            Identify.cluster_id,
            Scenes.cluster_id,
            OnOff.cluster_id,
            Color.cluster_id,
            LevelControl.cluster_id,
            LightLink.cluster_id,
        ],
    }

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2064
        #  device_version=2
        #  input_clusters=[0, 1, 32, 4096, 64768]
        #  output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
        MODELS_INFO: [(OSRAM, "Switch-LIGHTIFY")],
        ENDPOINTS: {
            1: copy.deepcopy(LightifyX4.signature[ENDPOINTS][1]),
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            2: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=3 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            3: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=4 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            4: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=5 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            5: copy.deepcopy(SIGNATURE_ENDPOINT),
            # <SimpleDescriptor endpoint=6 profile=260 device_type=2064
            # device_version=2
            # input_clusters=[4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            6: copy.deepcopy(SIGNATURE_ENDPOINT),
        },
    }

    REPLACEMENT_ENDPOINT = {
        PROFILE_ID: zha.PROFILE_ID,
        DEVICE_TYPE: OSRAM_DEVICE,
        INPUT_CLUSTERS: [LightLink.cluster_id, OsramButtonCluster],
        OUTPUT_CLUSTERS: [
            Groups.cluster_id,
            Identify.cluster_id,
            Scenes.cluster_id,
            OnOff.cluster_id,
            Color.cluster_id,
            LevelControl.cluster_id,
            LightLink.cluster_id,
        ],
    }

    replacement = {
        ENDPOINTS: {
            1: copy.deepcopy(LightifyX4.replacement[ENDPOINTS][1]),
            2: copy.deepcopy(REPLACEMENT_ENDPOINT),
            3: copy.deepcopy(REPLACEMENT_ENDPOINT),
            4: copy.deepcopy(REPLACEMENT_ENDPOINT),
            5: copy.deepcopy(REPLACEMENT_ENDPOINT),
            6: copy.deepcopy(REPLACEMENT_ENDPOINT),
        }
    }

    device_automation_triggers = copy.deepcopy(LightifyX4.device_automation_triggers)
