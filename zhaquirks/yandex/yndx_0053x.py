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
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
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


### YNDX-00531 & YNDX-00532 SINGLE-GANG & DOUBLE-GANG SWITCHES, ###

YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_ENDPOINT_ID = 2
YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_ENDPOINT_ID = 3

YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_NAME = "Button (Down)"
YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_NAME = "Button (Up)"

YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_ENDPOINT_ID = 3
YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_ENDPOINT_ID = 4
YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_ENDPOINT_ID = 5
YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_ENDPOINT_ID = 6

YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_NAME = "Button 1 (Down)"
YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_NAME = "Button 2 (Down)"
YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_NAME = "Button 1 (Up)"
YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_NAME = "Button 2 (Up)"


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
            YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_ENDPOINT_ID: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Up
            YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_ENDPOINT_ID: {
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

    device_automation_triggers = {
        (SHORT_PRESS, YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_GANG_SWITCH_BUTTON_DOWN_ENDPOINT_ID,
        },
        (SHORT_PRESS, YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_GANG_SWITCH_BUTTON_UP_ENDPOINT_ID,
        },
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
            YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_ENDPOINT_ID: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 2 Down
            YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_ENDPOINT_ID: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 1 Up
            YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_ENDPOINT_ID: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 2 Up
            YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_ENDPOINT_ID: {
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

    device_automation_triggers = {
        (SHORT_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_DOWN_ENDPOINT_ID,
        },
        (SHORT_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_DOWN_ENDPOINT_ID,
        },
        (SHORT_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_1_UP_ENDPOINT_ID,
        },
        (SHORT_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_GANG_SWITCH_BUTTON_2_UP_ENDPOINT_ID,
        },
    }


### YNDX-00537 SINGLE RELAY ###

YANDEX_SINGLE_RELAY_BUTTON_ENDPOINT_ID = 2

YANDEX_SINGLE_RELAY_BUTTON_NAME = "Button"

YANDEX_DOUBLE_RELAY_BUTTON_1_ENDPOINT_ID = 3
YANDEX_DOUBLE_RELAY_BUTTON_2_ENDPOINT_ID = 4

YANDEX_DOUBLE_RELAY_BUTTON_1_NAME = "Button 1"
YANDEX_DOUBLE_RELAY_BUTTON_2_NAME = "Button 2"


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
            YANDEX_SINGLE_RELAY_BUTTON_ENDPOINT_ID: {
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

    device_automation_triggers = {
        (SHORT_PRESS, YANDEX_SINGLE_RELAY_BUTTON_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_RELAY_BUTTON_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_SINGLE_RELAY_BUTTON_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_RELAY_BUTTON_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_SINGLE_RELAY_BUTTON_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_SINGLE_RELAY_BUTTON_ENDPOINT_ID,
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
            YANDEX_DOUBLE_RELAY_BUTTON_1_ENDPOINT_ID: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            # Button 2
            YANDEX_DOUBLE_RELAY_BUTTON_2_ENDPOINT_ID: {
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

    device_automation_triggers = {
        (SHORT_PRESS, YANDEX_DOUBLE_RELAY_BUTTON_1_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_RELAY_BUTTON_1_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_DOUBLE_RELAY_BUTTON_1_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_RELAY_BUTTON_1_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_DOUBLE_RELAY_BUTTON_1_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_RELAY_BUTTON_1_ENDPOINT_ID,
        },
        (SHORT_PRESS, YANDEX_DOUBLE_RELAY_BUTTON_2_NAME): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_RELAY_BUTTON_2_ENDPOINT_ID,
        },
        (DOUBLE_PRESS, YANDEX_DOUBLE_RELAY_BUTTON_2_NAME): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_RELAY_BUTTON_2_ENDPOINT_ID,
        },
        (LONG_PRESS, YANDEX_DOUBLE_RELAY_BUTTON_2_NAME): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: YANDEX_DOUBLE_RELAY_BUTTON_2_ENDPOINT_ID,
        },
    }
