"""Device handler for Bosch RBSH-RTH0-ZB-EU thermostat."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import PERCENTAGE, EntityType, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.hvac import TemperatureDisplayMode, Thermostat, UserInterface
from zigpy.zcl.foundation import ZCLAttributeDef

"""Bosch specific thermostat attribute ids."""

# Mode of operation with values BoschOperatingMode.
OPERATING_MODE_ATTR_ID = 0x4007

# Valve duty cycle: 0% - 100%.
VALVE_DUTY_CYCLE_ATTR_ID = 0x4020

# Valve state (relay on/off).
VALVE_STATE_ATTR_ID = 0x4022

# Window open switch (changes to a lower target temperature when on).
WINDOW_OPEN_ATTR_ID = 0x4042

# Boost heating preset mode.
BOOST_HEATING_ATTR_ID = 0x4043

# Outdoor temperature (writing to this adds it to the corner of the screen).
OUTDOOR_TEMP_ATTR_ID = 0x4051

# External sensor (S1/S2 10K NTC) temperature.
EXTERNAL_SENSOR_TEMP_ATTR_ID = 0x4052

# Actuator type setting (NO/NC).
ACTUATOR_TYPE_ATTR_ID = 0x4060

# External sensor connection config.
SENSOR_CONNECTION_ATTR_ID = 0x4062

"""
There are some more undocumented attributes that have not been figured out what they do.

0x4023: Valid range 0-7
0x4024: Valid range 0-23
0x4025: Valid range 0-100
0x4050: Valid range 5-10
0x405b: Valid range 0-255
0x4063: Valid range 0-3 (turns on display when changed, probably the UFH/Boiler/Radiator setting, but the values are unknown)
"""

"""Bosch specific user interface attribute ids."""

# Valve status LED config.
VALVE_STATUS_LED_ATTR_ID = 0x4033

# Display on-time (5s - 30s).
SCREEN_TIMEOUT_ATTR_ID = 0x403A

# Display brightness (0 - 10).
SCREEN_BRIGHTNESS_ATTR_ID = 0x403B

"""
More undocumented and unknown attributes in the UserInterface cluster.

0x4032: Valid range 0-15
0x406a: Valid range 0-255
0x406b: Valid range 0-255
0x406c: Valid range 0-255
0x406d: Valid range 0-255
"""


class BoschOperatingMode(t.enum8):
    """Bosch operating mode attribute values."""

    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05


class State(t.enum8):
    """Binary attribute (window open) value."""

    Off = 0x00
    On = 0x01


class BoschActuatorType(t.enum8):
    """Actuator type: Normally Open or Normally Closed."""

    NormallyClosed = 0x00
    NormallyOpen = 0x01


class BoschValveStatusLed(t.enum8):
    """Valve status LED (dot next to heat/cool icon) functionality."""

    AlwaysOff = 0x00
    Normal = 0x01
    AlwaysOn = 0x02


class BoschSensorConnection(t.enum8):
    """Sensor connection setting (for external 10K NTC sensor on S1/S2)."""

    NotUsed = 0x00
    WithoutRegulation = 0xB0
    WithRegulation = 0xB1


class BoschThermostatCluster(CustomCluster, Thermostat):
    """Bosch thermostat cluster."""

    # Works around an issue where ZHA thinks "Heating_Only" can't be changed
    # 0x06 is "centralite specific", but works perfectly for this thermostat as well
    _CONSTANT_ATTRIBUTES = {Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: 0x06}

    class AttributeDefs(Thermostat.AttributeDefs):
        """Bosch thermostat manufacturer specific attributes."""

        operating_mode = ZCLAttributeDef(
            id=OPERATING_MODE_ATTR_ID,
            type=BoschOperatingMode,
            is_manufacturer_specific=True,
        )

        valve_duty_cycle = ZCLAttributeDef(
            id=VALVE_DUTY_CYCLE_ATTR_ID,
            # Values range from 0-100
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        window_open = ZCLAttributeDef(
            id=WINDOW_OPEN_ATTR_ID,
            type=State,
            is_manufacturer_specific=True,
        )

        boost_heating = ZCLAttributeDef(
            id=BOOST_HEATING_ATTR_ID,
            type=State,
            is_manufacturer_specific=True,
        )

        temperature_display_mode = ZCLAttributeDef(
            id=0x0000,
            type=TemperatureDisplayMode,
            access="rw",
        )

        outdoor_temperature = ZCLAttributeDef(
            id=OUTDOOR_TEMP_ATTR_ID,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

        external_sensor_temperature = ZCLAttributeDef(
            id=EXTERNAL_SENSOR_TEMP_ATTR_ID,
            type=t.int16s,
            is_manufacturer_specific=True,
        )

        valve_state = ZCLAttributeDef(
            id=VALVE_STATE_ATTR_ID,
            type=State,
            is_manufacturer_specific=True,
        )

        actuator_type = ZCLAttributeDef(
            id=ACTUATOR_TYPE_ATTR_ID,
            type=BoschActuatorType,
            is_manufacturer_specific=True,
        )

        sensor_connection = ZCLAttributeDef(
            id=SENSOR_CONNECTION_ATTR_ID,
            type=BoschSensorConnection,
            is_manufacturer_specific=True,
        )


class BoschUserInterfaceCluster(CustomCluster, UserInterface):
    """Bosch UserInterface cluster."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Bosch user interface manufacturer specific attributes."""

        display_on_time = ZCLAttributeDef(
            id=SCREEN_TIMEOUT_ATTR_ID,
            # Usable values range from 5-30
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        display_brightness = ZCLAttributeDef(
            id=SCREEN_BRIGHTNESS_ATTR_ID,
            # Values range from 0-10
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        valve_status_led = ZCLAttributeDef(
            id=VALVE_STATUS_LED_ATTR_ID,
            type=BoschValveStatusLed,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Bosch", "RBSH-RTH0-ZB-EU")
    .applies_to("Bosch", "RBSH-RTH0-BAT-ZB-EU")
    .replaces(BoschThermostatCluster)
    .replaces(BoschUserInterfaceCluster)
    # Valve duty cycle, PWM controlled.
    .sensor(
        BoschThermostatCluster.AttributeDefs.valve_duty_cycle.name,
        BoschThermostatCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        translation_key="valve_duty_cycle",
        fallback_name="Valve duty cycle",
    )
    # Valve state (open/closed).
    .sensor(
        BoschThermostatCluster.AttributeDefs.valve_state.name,
        BoschThermostatCluster.cluster_id,
        translation_key="valve_state",
        fallback_name="Valve state",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
    )
    # External sensor temperature.
    # You CAN write to this, but it does not make any sense.
    .sensor(
        BoschThermostatCluster.AttributeDefs.external_sensor_temperature.name,
        BoschThermostatCluster.cluster_id,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="external_sensor_temperature",
        fallback_name="External sensor temperature",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=5
        ),
    )
    # Operating mode - On/Pause automatically from HVAC mode, Schedule/Manual configured here.
    .enum(
        BoschThermostatCluster.AttributeDefs.operating_mode.name,
        BoschOperatingMode,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    # Actuator type config.
    .enum(
        BoschThermostatCluster.AttributeDefs.actuator_type.name,
        BoschActuatorType,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="actuator_type",
        fallback_name="Actuator type",
    )
    # External sensor config.
    .enum(
        BoschThermostatCluster.AttributeDefs.sensor_connection.name,
        BoschSensorConnection,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="sensor_connection",
        fallback_name="Sensor connection",
    )
    # Temperature display mode.
    .enum(
        BoschUserInterfaceCluster.AttributeDefs.temperature_display_mode.name,
        TemperatureDisplayMode,
        BoschUserInterfaceCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
    )
    # Fast heating/boost - Only works with Heater type: Radiator.
    .switch(
        BoschThermostatCluster.AttributeDefs.boost_heating.name,
        BoschThermostatCluster.cluster_id,
        translation_key="boost_heating",
        fallback_name="Boost heating",
    )
    # Cooling setpoint limits.
    .number(
        BoschThermostatCluster.AttributeDefs.min_cool_setpoint_limit.name,
        BoschThermostatCluster.cluster_id,
        min_value=-500,
        max_value=3000,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="min_cool_setpoint_limit",
        fallback_name="Min cool setpoint limit",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.max_cool_setpoint_limit.name,
        BoschThermostatCluster.cluster_id,
        min_value=-500,
        max_value=3000,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="max_cool_setpoint_limit",
        fallback_name="Max cool setpoint limit",
    )
    # Window open switch: manually set or through an automation.
    .switch(
        BoschThermostatCluster.AttributeDefs.window_open.name,
        BoschThermostatCluster.cluster_id,
        translation_key="window_open",
        fallback_name="Window open",
    )
    # Display time-out.
    .number(
        BoschUserInterfaceCluster.AttributeDefs.display_on_time.name,
        BoschUserInterfaceCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=1,
        translation_key="display_on_time",
        fallback_name="Display on-time",
    )
    # Display brightness.
    .number(
        BoschUserInterfaceCluster.AttributeDefs.display_brightness.name,
        BoschUserInterfaceCluster.cluster_id,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="display_brightness",
        fallback_name="Display brightness",
    )
    # Valve status LED config.
    .enum(
        BoschUserInterfaceCluster.AttributeDefs.valve_status_led.name,
        BoschValveStatusLed,
        BoschUserInterfaceCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="valve_status_led",
        fallback_name="Valve status LED",
    )
    # Input for displaying outdoor temperature in the corner of the screen.
    .number(
        BoschThermostatCluster.AttributeDefs.outdoor_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=-32768,
        max_value=32767,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="outdoor_temperature",
        fallback_name="Outdoor temperature",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=5
        ),
    )
    .add_to_registry()
)
