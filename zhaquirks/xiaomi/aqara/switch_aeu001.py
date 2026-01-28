"""Aqara Display Switch V1 EU (lumi.switch.aeu001)."""

from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.zcl.clusters.general import (
    DeviceTemperature,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Scenes,
)
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    ENDPOINT_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
)

# Attribute for present_value in MultistateInput cluster
PRESENT_VALUE_ATTR = MultistateInput.AttributeDefs.present_value.id


class LVBytesString(t.LVBytes):
    """LVBytes type that accepts string input and encodes to UTF-8."""

    def __new__(cls, value=b""):
        """Create new instance, converting string to bytes if needed."""
        if isinstance(value, str):
            value = value.encode("utf-8")
        return super().__new__(cls, value)


class StartupOnOff(t.enum8):
    """Startup behavior enum."""

    On = 0x00
    RestorePrevious = 0x01
    Off = 0x02
    ReversePrevious = 0x03


class ButtonOperationMode(t.enum8):
    """Button operation mode enum."""

    Disabled = 0x00
    ControlRelay = 0x01
    Decoupled = 0x02
    WirelessButton = 0x04


class Theme(t.enum8):
    """Display theme enum."""

    Option1 = 0x00
    Option2 = 0x01


class ShowMode(t.enum8):
    """Button display mode enum."""

    IconAndText = 0x01
    IconOnly = 0x02
    TextOnly = 0x03


class ScreensaverStyle(t.enum8):
    """Screensaver style enum."""

    DigitalClock = 0x01
    WeatherConditions = 0x02
    IndoorEnvironment = 0x03


class ProximitySensitivity(t.enum8):
    """Proximity sensitivity enum."""

    Near = 0x01
    LessNear = 0x02
    Medium = 0x03
    LessFar = 0x04
    Far = 0x05


class ElderMode(t.enum8):
    """Elder mode enum (larger interface elements)."""

    Off = 0x03
    On = 0x05


class ButtonRelay(t.enum8):
    """Button relay assignment enum."""

    Relay1 = 0x01
    Relay2 = 0x02


class ButtonLayout(t.enum8):
    """Button layout assignment enum."""

    Empty = 0x00
    Switch1 = 0x01
    Switch2 = 0x02
    Button1 = 0x03
    Button2 = 0x04
    Button3 = 0x05
    Button4 = 0x06


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster for button events (single press only)."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == PRESENT_VALUE_ATTR and value == 1:
            # Single press detected (value=1)
            action = f"button_{self.endpoint.endpoint_id}_single"
            event_args = {
                "endpoint_id": self.endpoint.endpoint_id,
                "value": value,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster for Aqara Display Switch."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Switch configuration
        startup_on_off: Final = ZCLAttributeDef(
            id=0x0517,
            type=StartupOnOff,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        button_operation_mode: Final = ZCLAttributeDef(
            id=0x0269,
            type=ButtonOperationMode,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        button_relay: Final = ZCLAttributeDef(
            id=0x0235,
            type=ButtonRelay,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        button_layout: Final = ZCLAttributeDef(
            id=0x0300,
            type=ButtonLayout,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )

        # Display configuration
        theme: Final = ZCLAttributeDef(
            id=0x0215,
            type=Theme,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        show_mode: Final = ZCLAttributeDef(
            id=0x026A,
            type=ShowMode,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        display_brightness: Final = ZCLAttributeDef(
            id=0x0211, type=t.uint8_t, is_manufacturer_specific=True
        )
        standby_time: Final = ZCLAttributeDef(
            id=0x0216, type=t.uint32_t, is_manufacturer_specific=True
        )
        standby_screen_saver: Final = ZCLAttributeDef(
            id=0x0221, type=t.Bool, is_manufacturer_specific=True
        )
        standby_brightness: Final = ZCLAttributeDef(
            id=0x0222, type=t.uint8_t, is_manufacturer_specific=True
        )
        screensaver_style: Final = ZCLAttributeDef(
            id=0x0214,
            type=ScreensaverStyle,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        weather_data: Final = ZCLAttributeDef(
            id=0xFFF2, type=t.LVBytes, is_manufacturer_specific=True
        )
        color_button: Final = ZCLAttributeDef(
            id=0x0266, type=t.LVBytes, is_manufacturer_specific=True
        )

        # Proximity sensor
        proximity_activation: Final = ZCLAttributeDef(
            id=0x026D, type=t.uint8_t, is_manufacturer_specific=True
        )
        proximity_sensitivity: Final = ZCLAttributeDef(
            id=0x0268,
            type=ProximitySensitivity,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )

        # Other features
        elder_mode: Final = ZCLAttributeDef(
            id=0x0217,
            type=ElderMode,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        double_tap_override: Final = ZCLAttributeDef(
            id=0x0236, type=t.uint8_t, is_manufacturer_specific=True
        )

        # Button/Switch labels (writable via zha.set_zigbee_cluster_attribute service)
        button_name: Final = ZCLAttributeDef(
            id=0x026B, type=LVBytesString, is_manufacturer_specific=True
        )
        button_icon: Final = ZCLAttributeDef(
            id=0x026C, type=LVBytesString, is_manufacturer_specific=True
        )
        switch_name: Final = ZCLAttributeDef(
            id=0x026E, type=LVBytesString, is_manufacturer_specific=True
        )
        switch_icon: Final = ZCLAttributeDef(
            id=0x026F, type=LVBytesString, is_manufacturer_specific=True
        )


(
    QuirkBuilder("Aqara", "lumi.switch.aeu001")
    # Endpoint 1: Primary switch with metering
    .replaces(BasicCluster)
    .adds(DeviceTemperature)
    .adds(Identify)
    .adds(Groups)
    .adds(Scenes)
    .adds(OnOff)
    .replaces(MultistateInputCluster)
    .replaces(MeteringCluster)
    .replaces(ElectricalMeasurementCluster)
    .replaces(OppleCluster, cluster_id=OppleCluster.cluster_id)
    # Endpoint 2: Secondary switch
    .adds(Identify, endpoint_id=2)
    .adds(Groups, endpoint_id=2)
    .adds(Scenes, endpoint_id=2)
    .adds(OnOff, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(OppleCluster, cluster_id=OppleCluster.cluster_id, endpoint_id=2)
    # Endpoint 3: Button 1 (decoupled mode)
    .adds(Identify, endpoint_id=3)
    .adds(Groups, endpoint_id=3)
    .adds(Scenes, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .replaces(OppleCluster, cluster_id=OppleCluster.cluster_id, endpoint_id=3)
    # Endpoint 4: Button 2 (decoupled mode)
    .adds(Identify, endpoint_id=4)
    .adds(Groups, endpoint_id=4)
    .adds(Scenes, endpoint_id=4)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(OppleCluster, cluster_id=OppleCluster.cluster_id, endpoint_id=4)
    # Endpoint 21: Analog input
    .replaces(AnalogInputCluster, endpoint_id=21)
    # Device automation triggers for single press events
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: "button_1_single",
            },
            (SHORT_PRESS, BUTTON_2): {
                ENDPOINT_ID: 2,
                COMMAND: "button_2_single",
            },
            (SHORT_PRESS, BUTTON_3): {
                ENDPOINT_ID: 3,
                COMMAND: "button_3_single",
            },
            (SHORT_PRESS, BUTTON_4): {
                ENDPOINT_ID: 4,
                COMMAND: "button_4_single",
            },
        }
    )
    # Display configuration entities
    .number(
        OppleCluster.AttributeDefs.display_brightness.name,
        OppleCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="display_brightness",
        fallback_name="Display brightness",
    )
    .number(
        OppleCluster.AttributeDefs.standby_brightness.name,
        OppleCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="standby_brightness",
        fallback_name="Standby brightness",
    )
    .number(
        OppleCluster.AttributeDefs.standby_time.name,
        OppleCluster.cluster_id,
        min_value=5,
        max_value=65535,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="standby_time",
        fallback_name="Standby time",
    )
    .enum(
        OppleCluster.AttributeDefs.theme.name,
        Theme,
        OppleCluster.cluster_id,
        translation_key="theme",
        fallback_name="Display theme",
    )
    .enum(
        OppleCluster.AttributeDefs.show_mode.name,
        ShowMode,
        OppleCluster.cluster_id,
        translation_key="show_mode",
        fallback_name="Button display mode",
    )
    .enum(
        OppleCluster.AttributeDefs.screensaver_style.name,
        ScreensaverStyle,
        OppleCluster.cluster_id,
        translation_key="screensaver_style",
        fallback_name="Screensaver style",
    )
    .enum(
        OppleCluster.AttributeDefs.proximity_sensitivity.name,
        ProximitySensitivity,
        OppleCluster.cluster_id,
        translation_key="proximity_sensitivity",
        fallback_name="Proximity sensitivity",
    )
    .enum(
        OppleCluster.AttributeDefs.startup_on_off.name,
        StartupOnOff,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="startup_on_off",
        fallback_name="Switch 1 power-on behavior",
    )
    .enum(
        OppleCluster.AttributeDefs.startup_on_off.name,
        StartupOnOff,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="startup_on_off",
        fallback_name="Switch 2 power-on behavior",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="button_operation_mode",
        fallback_name="Button 1 operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="button_operation_mode",
        fallback_name="Button 2 operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=3,
        translation_key="button_operation_mode",
        fallback_name="Button 3 operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=4,
        translation_key="button_operation_mode",
        fallback_name="Button 4 operation mode",
    )
    # Button relay assignment (which relay each button controls)
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="button_relay",
        fallback_name="Button 1 relay",
    )
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="button_relay",
        fallback_name="Button 2 relay",
    )
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=3,
        translation_key="button_relay",
        fallback_name="Button 3 relay",
    )
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=4,
        translation_key="button_relay",
        fallback_name="Button 4 relay",
    )
    # Button layout assignment (what each button position shows)
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="button_layout",
        fallback_name="Button 1 layout",
    )
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="button_layout",
        fallback_name="Button 2 layout",
    )
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=3,
        translation_key="button_layout",
        fallback_name="Button 3 layout",
    )
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=4,
        translation_key="button_layout",
        fallback_name="Button 4 layout",
    )
    # Elder mode (larger interface elements)
    .enum(
        OppleCluster.AttributeDefs.elder_mode.name,
        ElderMode,
        OppleCluster.cluster_id,
        translation_key="elder_mode",
        fallback_name="Elder mode",
    )
    # Switch entities for boolean settings
    .switch(
        OppleCluster.AttributeDefs.standby_screen_saver.name,
        OppleCluster.cluster_id,
        translation_key="standby_screen_saver",
        fallback_name="Standby screensaver",
    )
    .switch(
        OppleCluster.AttributeDefs.proximity_activation.name,
        OppleCluster.cluster_id,
        translation_key="proximity_activation",
        fallback_name="Proximity wake",
    )
    .switch(
        OppleCluster.AttributeDefs.double_tap_override.name,
        OppleCluster.cluster_id,
        translation_key="double_tap_override",
        fallback_name="Double tap override",
    )
    .add_to_registry()
)


# Example service call to set button/switch names or icons:
# service: zha.set_zigbee_cluster_attribute
# data:
#   ieee: "your:device:ieee:address"
#   endpoint_id: 1        # 1-4 for buttons, 1-2 for switches
#   cluster_id: 64704     # 0xfcc0
#   cluster_type: in
#   attribute: 619        # button_name (619), button_icon (620), switch_name (622), switch_icon (623)
#   value: "My Label"
#   manufacturer: 4447    # 0x115f (Aqara)
