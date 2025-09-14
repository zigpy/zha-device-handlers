"""Device handler for Bosch RBSH-RTH0-ZB-EU thermostat."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.hvac import TemperatureDisplayMode, Thermostat, UserInterface
from zigpy.zcl.foundation import ZCLAttributeDef

"""Bosch specific thermostat attribute ids."""

# Mode of operation with values BoschOperatingMode.
OPERATING_MODE_ATTR_ID = 0x4007

# Valve duty cycle: 0% - 100%
VALVE_DUTY_CYCLE_ATTR_ID = 0x4020

# Window open switch (changes to a lower target temperature when on).
WINDOW_OPEN_ATTR_ID = 0x4042

# Boost heating preset mode.
BOOST_HEATING_ATTR_ID = 0x4043

"""Bosch specific user interface attribute ids."""

# Display on-time (5s - 30s).
SCREEN_TIMEOUT_ATTR_ID = 0x403A

# Display brightness (0 - 10).
SCREEN_BRIGHTNESS_ATTR_ID = 0x403B


class BoschOperatingMode(t.enum8):
    """Bosch operating mode attribute values."""

    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05


class State(t.enum8):
    """Binary attribute (window open) value."""

    Off = 0x00
    On = 0x01


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
    # Operating mode - On/Pause automatically from HVAC mode, Schedule/Manual configured here.
    .enum(
        BoschThermostatCluster.AttributeDefs.operating_mode.name,
        BoschOperatingMode,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    # Temperature display type.
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
    .add_to_registry()
)
