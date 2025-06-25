"""Support for YNDX-0053x devices."""

from typing import Final

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.foundation import BaseAttributeDefs, BaseCommandDefs

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.yandex import (
    YANDEX,
    YANDEX_ATTRIBUTE_BUTTON_MODE,
    YANDEX_ATTRIBUTE_INTERLOCK,
    YANDEX_ATTRIBUTE_LED_INDICATOR,
    YANDEX_ATTRIBUTE_POWER_TYPE,
    YANDEX_ATTRIBUTE_SWITCH_MODE,
    YANDEX_ATTRIBUTE_SWITCH_TYPE,
    YANDEX_CLUSTER_ID,
    YANDEX_COMMAND_BUTTON_MODE,
    YANDEX_COMMAND_INTERLOCK,
    YANDEX_COMMAND_POWER_TYPE,
    YANDEX_COMMAND_SWITCH_MODE,
    YANDEX_COMMAND_SWITCH_TYPE,
    YandexCluster,
)

### YNDX-00530 DIMMER ###


class YandexClusterDimmer(YandexCluster):
    """Cluster for dimmer."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        led_indicator: Final = YANDEX_ATTRIBUTE_LED_INDICATOR
        button_mode: Final = YANDEX_ATTRIBUTE_BUTTON_MODE

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        button_mode: Final = YANDEX_COMMAND_BUTTON_MODE


class YandexDimmer(CustomDevice):
    """Dimmer."""

    signature = {
        MODELS_INFO: [(YANDEX, "YNDX-00530")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=257
            # device_version=0
            # input_clusters=[0, 3, 4, 6, 8, 64515]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    YandexClusterDimmer,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


### YNDX-00531 AND YNDX-00532 SINGLE-GANG AND DOUBLE-GANG SWITCHES ###


class YandexClusterSwitchMain(YandexCluster):
    """Main cluster for all Yandex switches."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_mode: Final = YANDEX_ATTRIBUTE_SWITCH_MODE
        power_type: Final = YANDEX_ATTRIBUTE_POWER_TYPE
        led_indicator: Final = YANDEX_ATTRIBUTE_LED_INDICATOR

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        switch_mode: Final = YANDEX_COMMAND_SWITCH_MODE
        power_type: Final = YANDEX_COMMAND_POWER_TYPE


class YandexClusterSwitchSecondary(YandexCluster):
    """Secondary cluster for all Yandex switches."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_mode: Final = YANDEX_ATTRIBUTE_SWITCH_MODE

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        switch_mode: Final = YANDEX_COMMAND_SWITCH_MODE


class YandexSingleGangSwitch(CustomDevice):
    """Single-gang switch."""

    signature = {
        MODELS_INFO: [(YANDEX, "YNDX-00531")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=0
            # input_clusters=[0, 3, 6, 64515]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YandexClusterSwitchMain,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # Down
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Up
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
        }
    }


class YandexDoubleGangSwitch(CustomDevice):
    """Double-gang switch."""

    signature = {
        MODELS_INFO: [(YANDEX, "YNDX-00532")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=0
            # input_clusters=[0, 3, 6, 64515]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=256
            # device_version=0
            # input_clusters=[0, 3, 6, 64515]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YandexClusterSwitchMain,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YandexClusterSwitchSecondary,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # Button 1 Down
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 2 Down
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 1 Up
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 2 Up
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
        }
    }


### YNDX-00537 SINGLE RELAY ###


class YandexClusterSingleRelay(YandexCluster):
    """Cluster for single relay."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_type: Final = YANDEX_ATTRIBUTE_SWITCH_TYPE
        power_type: Final = YANDEX_ATTRIBUTE_POWER_TYPE

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        switch_type: Final = YANDEX_COMMAND_SWITCH_TYPE
        power_type: Final = YANDEX_COMMAND_POWER_TYPE


class YandexSingleRelay(CustomDevice):
    """Single relay."""

    signature = {
        MODELS_INFO: [(YANDEX, "YNDX-00537")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=0
            # input_clusters=[0, 3, 6, 64515]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YandexClusterSingleRelay,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # Button (decoupled)
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
        },
    }


### YNDX-00538 DOUBLE RELAY ###


class YandexClusterDoubleRelayMain(YandexCluster):
    """Main cluster for double relay."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_type: Final = YANDEX_ATTRIBUTE_SWITCH_TYPE
        power_type: Final = YANDEX_ATTRIBUTE_POWER_TYPE
        interlock: Final = YANDEX_ATTRIBUTE_INTERLOCK

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        switch_type: Final = YANDEX_COMMAND_SWITCH_TYPE
        power_type: Final = YANDEX_COMMAND_POWER_TYPE
        interlock: Final = YANDEX_COMMAND_INTERLOCK


class YandexClusterDoubleRelaySecondary(YandexCluster):
    """Secondary cluster for double relay."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_type: Final = YANDEX_ATTRIBUTE_SWITCH_TYPE

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        switch_type: Final = YANDEX_COMMAND_SWITCH_TYPE


class YandexDoubleRelay(CustomDevice):
    """Double relay."""

    signature = {
        MODELS_INFO: [(YANDEX, "YNDX-00538")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=0
            # input_clusters=[0, 3, 6, 64515]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=256
            # device_version=0
            # input_clusters=[0, 3, 6, 64515]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YANDEX_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YandexClusterDoubleRelayMain,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    YandexClusterDoubleRelaySecondary,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # Button 1
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 2
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
        },
    }
