"""Support for YNDX-00531 and YNDX-00532 one-gang and two-gang wired switches."""

from typing import Any, Final

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, Identify, OnOff
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
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
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

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes using commands because manufacturer-specific attribute writing is unsupported by Yandex devices."""

        result = []
        remaining_attributes = attributes.copy()

        if "switch_mode" in attributes:
            remaining_attributes.pop("switch_mode")
            result += await self.command(0x01, attributes.get("switch_mode"))
        if 0x0001 in attributes:
            remaining_attributes.pop(0x0001)
            result += await self.command(0x01, attributes.get(0x0001))
        if "power_type" in attributes:
            remaining_attributes.pop("power_type")
            result += await self.command(0x03, attributes.get("power_type"))
        if 0x0003 in attributes:
            remaining_attributes.pop(0x0003)
            result += await self.command(0x03, attributes.get(0x0003))

        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, manufacturer)

        return result


(
    QuirkBuilder(YANDEX, "YNDX-00531")
    .replaces(YandexSwitchClusterWired, endpoint_id=1)
    .adds_endpoint(
        endpoint_id=2,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH,
    )
    .adds(Basic, endpoint_id=2, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=2, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=2, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=2, cluster_type=ClusterType.Client)
    .adds_endpoint(
        endpoint_id=3,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH,
    )
    .adds(Basic, endpoint_id=3, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=3, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=3, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=3, cluster_type=ClusterType.Client)
    .device_automation_triggers(
        {
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
    )
    .enum(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.power_type.name,
        enum_class=YandexType_PowerType,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        translation_key="power_type",
        fallback_name="Power type",
    )
    .enum(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.switch_mode.name,
        enum_class=YandexType_SwitchMode,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        translation_key="switch_mode",
        fallback_name="Switch mode",
    )
    .switch(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.led_indicator.name,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED indicator",
        off_value=YandexType_LedIndicator.Disabled,
        on_value=YandexType_LedIndicator.Enabled,
    )
    .add_to_registry()
)

(
    QuirkBuilder(YANDEX, "YNDX-00532")
    .replaces(YandexSwitchClusterWired, endpoint_id=1)
    .replaces(YandexSwitchClusterWired, endpoint_id=2)
    .adds_endpoint(
        endpoint_id=3,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH,
    )
    .adds(Basic, endpoint_id=3, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=3, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=3, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=3, cluster_type=ClusterType.Client)
    .adds_endpoint(
        endpoint_id=4,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH,
    )
    .adds(Basic, endpoint_id=4, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=4, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=4, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=4, cluster_type=ClusterType.Client)
    .adds_endpoint(
        endpoint_id=5,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH,
    )
    .adds(Basic, endpoint_id=5, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=5, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=5, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=5, cluster_type=ClusterType.Client)
    .adds_endpoint(
        endpoint_id=6,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH,
    )
    .adds(Basic, endpoint_id=6, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=6, cluster_type=ClusterType.Server)
    .adds(Identify, endpoint_id=6, cluster_type=ClusterType.Client)
    .adds(OnOff, endpoint_id=6, cluster_type=ClusterType.Client)
    .device_automation_triggers(
        {
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
    )
    .enum(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.power_type.name,
        enum_class=YandexType_PowerType,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        translation_key="power_type",
        fallback_name="Power type",
    )
    .enum(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.switch_mode.name,
        enum_class=YandexType_SwitchMode,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        endpoint_id=1,
        translation_key="switch_mode",
        fallback_name="Switch mode",
    )
    .enum(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.switch_mode.name,
        enum_class=YandexType_SwitchMode,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        endpoint_id=2,
        translation_key="switch_mode",
        fallback_name="Switch mode",
    )
    .switch(
        attribute_name=YandexSwitchClusterWired.AttributeDefs.led_indicator.name,
        cluster_id=YandexSwitchClusterWired.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED indicator",
        off_value=YandexType_LedIndicator.Disabled,
        on_value=YandexType_LedIndicator.Enabled,
    )
    .add_to_registry()
)
