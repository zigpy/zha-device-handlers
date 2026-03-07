"""Support for YNDX-00531 and YNDX-00532 one-gang and two-gang wired switches."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
)

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
    YANDEX_MANUFACTURER_CODE_1,
    YandexType_LedIndicator,
    YandexType_PowerType,
    YandexType_SwitchMode,
)


class YandexSwitchClusterWired(CustomCluster):
    """Yandex switch cluster for YNDX-00531, YNDX-00532 wired switches."""

    cluster_id = 0xFC03
    manufacturer_id_override = YANDEX_MANUFACTURER_CODE_1

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_mode: Final = ZCLAttributeDef(
            id=0x0001,
            type=YandexType_SwitchMode,
            access="rw",
        )
        power_type: Final = ZCLAttributeDef(
            id=0x0003,
            type=YandexType_PowerType,
            access="rw",
        )
        led_indicator: Final = ZCLAttributeDef(
            id=0x0005,
            type=YandexType_LedIndicator,
            access="rw",
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        switch_mode: Final = ZCLCommandDef(
            id=0x01,
            schema={"value": YandexType_SwitchMode},
            direction=Direction.Client_to_Server,
            is_manufacturer_specific=True,
        )
        power_type: Final = ZCLCommandDef(
            id=0x03,
            schema={"value": YandexType_PowerType},
            direction=Direction.Client_to_Server,
            is_manufacturer_specific=True,
        )


class YandexOneGangWiredSwitch(CustomDevice):
    """YNDX-00531 one-gang wired switch."""

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
                    YandexSwitchClusterWired.cluster_id,
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
                    YandexSwitchClusterWired,
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

    device_automation_triggers = {
        (SHORT_PRESS, "Button (Down)"): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
        (DOUBLE_PRESS, "Button (Down)"): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
        (LONG_PRESS, "Button (Down)"): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
        (SHORT_PRESS, "Button (Up)"): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (DOUBLE_PRESS, "Button (Up)"): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (LONG_PRESS, "Button (Up)"): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
    }


class YandexTwoGangWiredSwitch(CustomDevice):
    """YNDX-00532 two-gang wired switch."""

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
                    YandexSwitchClusterWired.cluster_id,
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
                    YandexSwitchClusterWired.cluster_id,
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
                    YandexSwitchClusterWired,
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
                    YandexSwitchClusterWired,
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

    device_automation_triggers = {
        (SHORT_PRESS, "Button 1 (Down)"): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (DOUBLE_PRESS, "Button 1 (Down)"): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (LONG_PRESS, "Button 1 (Down)"): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (SHORT_PRESS, "Button 2 (Down)"): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 4,
        },
        (DOUBLE_PRESS, "Button 2 (Down)"): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 4,
        },
        (LONG_PRESS, "Button 2 (Down)"): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 4,
        },
        (SHORT_PRESS, "Button 1 (Up)"): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 5,
        },
        (DOUBLE_PRESS, "Button 1 (Up)"): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 5,
        },
        (LONG_PRESS, "Button 1 (Up)"): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 5,
        },
        (SHORT_PRESS, "Button 2 (Up)"): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 6,
        },
        (DOUBLE_PRESS, "Button 2 (Up)"): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 6,
        },
        (LONG_PRESS, "Button 2 (Up)"): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 6,
        },
    }
