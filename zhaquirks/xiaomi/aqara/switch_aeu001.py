"""Aqara Display Switch V1 EU (lumi.switch.aeu001)."""

import struct
from typing import Any, Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.zcl.clusters.general import Groups, Identify, MultistateInput, OnOff, Scenes
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

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
    """Button layout assignment enum (only used when button_operation_mode = WirelessButton)."""

    Button1 = 0x01
    Button2 = 0x02
    Button3 = 0x04
    Button4 = 0x08


class WeatherCondition(t.enum8):
    """Weather condition codes for the display screensaver."""

    Sunny = 0x00
    Clear = 0x01
    Fair = 0x03
    Cloudy = 0x04
    PartlyCloudy = 0x05
    MostlyCloudy = 0x07
    Overcast = 0x09
    LightRain = 0x0D
    ModerateRain = 0x0E
    Storm = 0x10
    HeavyStorm = 0x11
    SevereStorm = 0x12
    FreezingRain = 0x13
    Sleet = 0x14
    SnowFlurry = 0x15
    LightSnow = 0x16
    ModerateSnow = 0x17
    HeavySnow = 0x18
    Snowstorm = 0x19
    Foggy = 0x1E
    Windy = 0x20
    Blustery = 0x21
    Hurricane = 0x22
    TropicalStorm = 0x23
    Tornado = 0x24
    Unknown = 0x25


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

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
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
        # weather_data and color_button are complex byte arrays with device-specific
        # encoding. They are defined for attribute discovery but not exposed as
        # Home Assistant entities since their format is not fully documented.
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

        # Weather display attributes (write-only, used with screensaver_style=WeatherConditions)
        # These are virtual attributes that encode data into weather_data packets.
        weather_condition: Final = ZCLAttributeDef(
            id=0xFFF0,  # Virtual ID (not a real device attribute)
            type=WeatherCondition,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )
        weather_temperature: Final = ZCLAttributeDef(
            id=0xFFF1,  # Virtual ID (not a real device attribute)
            type=t.int16s,  # Temperature in Celsius (e.g., -10 to 50)
            is_manufacturer_specific=True,
        )

    def __init__(self, *args, **kwargs):
        """Initialize the cluster with instance-level weather sequence counter."""
        super().__init__(*args, **kwargs)
        self._weather_seq = 0

    def _get_ieee_bytes(self) -> bytes:
        """Extract last 6 bytes of device IEEE address for weather packets."""
        ieee = self.endpoint.device.ieee
        # IEEE address is 8 bytes, we need the last 6
        ieee_bytes = ieee.serialize()
        return ieee_bytes[2:8]  # Skip first 2 bytes

    def _build_weather_packet(self, msg_type: tuple[int, int], payload: bytes) -> bytes:
        """Build a weather data packet for the display.

        Packet format (22 bytes):
        - Header: 0xAA 0x71 0x13 0x44 (4 bytes)
        - Sequence: 1 byte (incrementing counter)
        - Checksum: 1 byte (0x8E - sequence)
        - Type marker: 0x08 0x41 0x10 (3 bytes)
        - Reserved: 0x00 0x00 (2 bytes)
        - IEEE address: 6 bytes (last 6 bytes of device address)
        - Message type: 2 bytes (e.g., 0x0D 0x02 for condition)
        - Data marker: 0x00 0x55 (2 bytes)
        - Payload: 4 bytes
        """
        # Increment and wrap sequence counter
        self._weather_seq = (self._weather_seq + 1) & 0xFF
        seq = self._weather_seq
        checksum = (0x8E - seq) & 0xFF

        ieee_bytes = self._get_ieee_bytes()

        packet = (
            bytes(
                [
                    0xAA,
                    0x71,
                    0x13,
                    0x44,  # Header
                    seq,  # Sequence number
                    checksum,  # Checksum (seq + checksum = 0x8E)
                    0x08,
                    0x41,
                    0x10,  # Type marker (Octet String, Length 16)
                    0x00,
                    0x00,  # Reserved
                ]
            )
            + ieee_bytes
            + bytes(
                [
                    msg_type[0],
                    msg_type[1],  # Message type
                    0x00,
                    0x55,  # Data marker
                ]
            )
            + payload
        )

        return packet

    def _build_condition_packet(self, condition_code: int) -> bytes:
        """Build weather condition packet (message type 0x0D, 0x02)."""
        payload = bytes([0x00, 0x00, 0x00, condition_code])
        return self._build_weather_packet((0x0D, 0x02), payload)

    def _build_null_packet(self) -> bytes:
        """Build null packet required after some weather conditions (message type 0x00, 0x06)."""
        payload = bytes([0x00, 0x00, 0x00, 0x00])
        return self._build_weather_packet((0x00, 0x06), payload)

    def _build_temperature_packet(self, temperature: float) -> bytes:
        """Build weather temperature packet (message type 0x00, 0x04)."""
        # Convert temperature to IEEE 754 single-precision float (big-endian)
        payload = struct.pack(">f", temperature)
        return self._build_weather_packet((0x00, 0x04), payload)

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Override write_attributes to handle weather virtual attributes."""
        # Check for weather virtual attributes
        weather_condition_id = self.AttributeDefs.weather_condition.id
        weather_temperature_id = self.AttributeDefs.weather_temperature.id
        weather_data_id = self.AttributeDefs.weather_data.id

        # Process weather_condition
        if weather_condition_id in attributes or "weather_condition" in attributes:
            value = attributes.pop(weather_condition_id, None) or attributes.pop(
                "weather_condition", None
            )
            if value is not None:
                # Convert enum value if needed
                if isinstance(value, WeatherCondition):
                    condition_code = value.value
                elif isinstance(value, int):
                    condition_code = value
                else:
                    # Try to look up by name
                    try:
                        condition_code = WeatherCondition[value].value
                    except KeyError as exc:
                        raise ValueError(
                            f"Invalid weather condition: {value!r}"
                        ) from exc

                # Build and send condition packet
                condition_packet = self._build_condition_packet(condition_code)
                await super().write_attributes(
                    {weather_data_id: condition_packet}, manufacturer=manufacturer
                )

                # Send null packet (required for some conditions like fog)
                null_packet = self._build_null_packet()
                await super().write_attributes(
                    {weather_data_id: null_packet}, manufacturer=manufacturer
                )

        # Process weather_temperature
        if weather_temperature_id in attributes or "weather_temperature" in attributes:
            value = attributes.pop(weather_temperature_id, None) or attributes.pop(
                "weather_temperature", None
            )
            if value is not None:
                temperature = float(value)
                temp_packet = self._build_temperature_packet(temperature)
                await super().write_attributes(
                    {weather_data_id: temp_packet}, manufacturer=manufacturer
                )

        # Process remaining attributes normally
        if attributes:
            return await super().write_attributes(attributes, manufacturer=manufacturer)

        return [0]  # Success


(
    QuirkBuilder("Aqara", "lumi.switch.aeu001")
    # Endpoint 1: Primary switch with metering
    .replaces(BasicCluster)
    .adds(Identify)
    .adds(Groups)
    .adds(Scenes)
    .adds(OnOff)
    .replaces(MultistateInputCluster)
    .replaces(MeteringCluster)
    .replaces(ElectricalMeasurementCluster)
    .replaces(OppleCluster)
    # Endpoint 2: Secondary switch
    .adds(Identify, endpoint_id=2)
    .adds(Groups, endpoint_id=2)
    .adds(Scenes, endpoint_id=2)
    .adds(OnOff, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(OppleCluster, endpoint_id=2)
    # Endpoint 3: Button 1 (decoupled mode)
    .adds(Identify, endpoint_id=3)
    .adds(Groups, endpoint_id=3)
    .adds(Scenes, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .replaces(OppleCluster, endpoint_id=3)
    # Endpoint 4: Button 2 (decoupled mode)
    .adds(Identify, endpoint_id=4)
    .adds(Groups, endpoint_id=4)
    .adds(Scenes, endpoint_id=4)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(OppleCluster, endpoint_id=4)
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
        translation_key="startup_on_off_1",
        fallback_name="Switch 1 power-on behavior",
    )
    .enum(
        OppleCluster.AttributeDefs.startup_on_off.name,
        StartupOnOff,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="startup_on_off_2",
        fallback_name="Switch 2 power-on behavior",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="button_operation_mode_1",
        fallback_name="Button 1 operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="button_operation_mode_2",
        fallback_name="Button 2 operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=3,
        translation_key="button_operation_mode_3",
        fallback_name="Button 3 operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.button_operation_mode.name,
        ButtonOperationMode,
        OppleCluster.cluster_id,
        endpoint_id=4,
        translation_key="button_operation_mode_4",
        fallback_name="Button 4 operation mode",
    )
    # Button relay assignment (which relay each button controls)
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="button_relay_1",
        fallback_name="Button 1 relay",
    )
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="button_relay_2",
        fallback_name="Button 2 relay",
    )
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=3,
        translation_key="button_relay_3",
        fallback_name="Button 3 relay",
    )
    .enum(
        OppleCluster.AttributeDefs.button_relay.name,
        ButtonRelay,
        OppleCluster.cluster_id,
        endpoint_id=4,
        translation_key="button_relay_4",
        fallback_name="Button 4 relay",
    )
    # Button layout assignment (what each button position shows)
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=1,
        translation_key="button_layout_1",
        fallback_name="Button 1 layout",
    )
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=2,
        translation_key="button_layout_2",
        fallback_name="Button 2 layout",
    )
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=3,
        translation_key="button_layout_3",
        fallback_name="Button 3 layout",
    )
    .enum(
        OppleCluster.AttributeDefs.button_layout.name,
        ButtonLayout,
        OppleCluster.cluster_id,
        endpoint_id=4,
        translation_key="button_layout_4",
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
#
# The device uses DIFFERENT attributes depending on the button's operation mode:
#   - Switch mode (button_operation_mode = ControlRelay): use switch_name/switch_icon
#   - Button mode (button_operation_mode = WirelessButton): use button_name/button_icon
#
# service: zha.set_zigbee_cluster_attribute
# data:
#   ieee: "your:device:ieee:address"
#   endpoint_id: 1        # Display position 1-4
#   cluster_id: 64704     # 0xFCC0
#   cluster_type: in
#   attribute: 0x026F     # switch_icon (0x026F) or switch_name (0x026E) for switch mode
#                         # button_icon (0x026C) or button_name (0x026B) for button mode
#   value: "light_bulb"   # Icon name or custom text label
#   manufacturer: 4447    # 0x115F (Aqara)
#
#
# Example service calls to set weather display (for screensaver_style = WeatherConditions):
#
# Set weather condition:
# service: zha.set_zigbee_cluster_attribute
# data:
#   ieee: "your:device:ieee:address"
#   endpoint_id: 1
#   cluster_id: 64704     # 0xFCC0
#   cluster_type: in
#   attribute: 0xFFF0     # weather_condition (virtual attribute)
#   value: 4              # WeatherCondition enum value (see below)
#   manufacturer: 4447    # 0x115F (Aqara)
#
# Set weather temperature:
# service: zha.set_zigbee_cluster_attribute
# data:
#   ieee: "your:device:ieee:address"
#   endpoint_id: 1
#   cluster_id: 64704     # 0xFCC0
#   cluster_type: in
#   attribute: 0xFFF1     # weather_temperature (virtual attribute)
#   value: 22             # Temperature in Celsius
#   manufacturer: 4447    # 0x115F (Aqara)
#
# WeatherCondition values:
#   Sunny=0, Clear=1, Fair=3, Cloudy=4, PartlyCloudy=5, MostlyCloudy=7,
#   Overcast=9, LightRain=13, ModerateRain=14, Storm=16, HeavyStorm=17,
#   SevereStorm=18, FreezingRain=19, Sleet=20, SnowFlurry=21, LightSnow=22,
#   ModerateSnow=23, HeavySnow=24, Snowstorm=25, Foggy=30, Windy=32,
#   Blustery=33, Hurricane=34, TropicalStorm=35, Tornado=36, Unknown=37
