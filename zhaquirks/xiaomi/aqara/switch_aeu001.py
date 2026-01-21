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
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    ATTR_ID,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    PRESS_TYPE,
    SHORT_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
)

# Press type mapping from device values to human-readable strings
PRESS_TYPES = {0: "hold", 1: "single", 2: "double"}
STATUS_TYPE_ATTR = 0x0055  # decimal = 85


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster for button events."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            # Map value to press type
            self._current_state = PRESS_TYPES.get(value)
            if self._current_state:
                # Generate event with format: "{endpoint_id}_{press_type}"
                event_args = {
                    ENDPOINT_ID: self.endpoint.endpoint_id,
                    PRESS_TYPE: self._current_state,
                    ATTR_ID: attrid,
                    VALUE: value,
                }
                action = f"{self.endpoint.endpoint_id}_{self._current_state}"
                self.listener_event(ZHA_SEND_EVENT, action, event_args)
                # Update attribute 0 for display in Home Assistant
                super()._update_attribute(0, action)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster for Aqara Display Switch."""

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

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        # Switch configuration
        startup_on_off: Final = ZCLAttributeDef(
            id=0x0517, type=t.uint8_t, is_manufacturer_specific=True
        )
        button_operation_mode: Final = ZCLAttributeDef(
            id=0x0269, type=t.uint8_t, is_manufacturer_specific=True
        )
        button_relay: Final = ZCLAttributeDef(
            id=0x0235, type=t.uint8_t, is_manufacturer_specific=True
        )
        button_layout: Final = ZCLAttributeDef(
            id=0x0300, type=t.uint8_t, is_manufacturer_specific=True
        )

        # Display configuration
        theme: Final = ZCLAttributeDef(
            id=0x0215, type=t.uint8_t, is_manufacturer_specific=True
        )
        show_mode: Final = ZCLAttributeDef(
            id=0x026A, type=t.uint8_t, is_manufacturer_specific=True
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
            id=0x0214, type=t.uint8_t, is_manufacturer_specific=True
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
            id=0x0268, type=t.uint8_t, is_manufacturer_specific=True
        )

        # Other features
        elder_mode: Final = ZCLAttributeDef(
            id=0x0217, type=t.uint8_t, is_manufacturer_specific=True
        )
        double_tap_override: Final = ZCLAttributeDef(
            id=0x0236, type=t.uint8_t, is_manufacturer_specific=True
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
    .replaces(OppleCluster, cluster_id=0xFCC0)
    # Endpoint 2: Secondary switch
    .adds(Identify, endpoint_id=2)
    .adds(Groups, endpoint_id=2)
    .adds(Scenes, endpoint_id=2)
    .adds(OnOff, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(OppleCluster, cluster_id=0xFCC0, endpoint_id=2)
    # Endpoint 3: Button 1 (decoupled mode)
    .adds(Identify, endpoint_id=3)
    .adds(Groups, endpoint_id=3)
    .adds(Scenes, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .replaces(OppleCluster, cluster_id=0xFCC0, endpoint_id=3)
    # Endpoint 4: Button 2 (decoupled mode)
    .adds(Identify, endpoint_id=4)
    .adds(Groups, endpoint_id=4)
    .adds(Scenes, endpoint_id=4)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(OppleCluster, cluster_id=0xFCC0, endpoint_id=4)
    # Endpoint 21: Analog input
    .replaces(AnalogInputCluster, endpoint_id=21)
    # Device automation triggers for all button events
    .device_automation_triggers(
        {
            # Button 1 (Endpoint 1)
            (SHORT_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: "1_single",
            },
            (DOUBLE_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: "1_double",
            },
            (LONG_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: "1_hold",
            },
            # Button 2 (Endpoint 2)
            (SHORT_PRESS, BUTTON_2): {
                ENDPOINT_ID: 2,
                COMMAND: "2_single",
            },
            (DOUBLE_PRESS, BUTTON_2): {
                ENDPOINT_ID: 2,
                COMMAND: "2_double",
            },
            (LONG_PRESS, BUTTON_2): {
                ENDPOINT_ID: 2,
                COMMAND: "2_hold",
            },
            # Button 3 (Endpoint 3 - decoupled mode)
            (SHORT_PRESS, BUTTON_3): {
                ENDPOINT_ID: 3,
                COMMAND: "3_single",
            },
            (DOUBLE_PRESS, BUTTON_3): {
                ENDPOINT_ID: 3,
                COMMAND: "3_double",
            },
            (LONG_PRESS, BUTTON_3): {
                ENDPOINT_ID: 3,
                COMMAND: "3_hold",
            },
            # Button 4 (Endpoint 4 - decoupled mode)
            (SHORT_PRESS, BUTTON_4): {
                ENDPOINT_ID: 4,
                COMMAND: "4_single",
            },
            (DOUBLE_PRESS, BUTTON_4): {
                ENDPOINT_ID: 4,
                COMMAND: "4_double",
            },
            (LONG_PRESS, BUTTON_4): {
                ENDPOINT_ID: 4,
                COMMAND: "4_hold",
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
        OppleCluster.Theme,
        OppleCluster.cluster_id,
        translation_key="theme",
        fallback_name="Display theme",
    )
    .enum(
        OppleCluster.AttributeDefs.show_mode.name,
        OppleCluster.ShowMode,
        OppleCluster.cluster_id,
        translation_key="show_mode",
        fallback_name="Button display mode",
    )
    .enum(
        OppleCluster.AttributeDefs.screensaver_style.name,
        OppleCluster.ScreensaverStyle,
        OppleCluster.cluster_id,
        translation_key="screensaver_style",
        fallback_name="Screensaver style",
    )
    .enum(
        OppleCluster.AttributeDefs.proximity_sensitivity.name,
        OppleCluster.ProximitySensitivity,
        OppleCluster.cluster_id,
        translation_key="proximity_sensitivity",
        fallback_name="Proximity sensitivity",
    )
    .enum(
        OppleCluster.AttributeDefs.startup_on_off.name,
        OppleCluster.StartupOnOff,
        OppleCluster.cluster_id,
        translation_key="startup_on_off",
        fallback_name="Power-on behavior",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        OppleCluster.ButtonOperationMode,
        OppleCluster.cluster_id,
        translation_key="button_operation_mode",
        fallback_name="Button operation mode",
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
