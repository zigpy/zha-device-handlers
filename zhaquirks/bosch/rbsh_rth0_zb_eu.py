"""Device handler for Bosch RBSH-RTH0-ZB-EU thermostat."""


from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import add_to_registry_v2
import zigpy.types as t
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    Thermostat,
    UserInterface,
)
from zigpy.zcl.foundation import ZCLAttributeDef

"""Bosch specific thermostat attribute ids."""

# Mode of operation with values BoschOperatingMode.
OPERATING_MODE_ATTR_ID = 0x4007

# Valve position: 0% - 100%
VALVE_POSITION_ATTR_ID = 0x4020

# Window open switch (changes to a lower target temperature when on).
WINDOW_OPEN_ATTR_ID = 0x4042

# Boost preset mode.
BOOST_ATTR_ID = 0x4043

"""Bosch specific user interface attribute ids."""

# Display on-time (5s - 30s).
SCREEN_TIMEOUT_ATTR_ID = 0x403A

# Display brightness (0 - 10).
SCREEN_BRIGHTNESS_ATTR_ID = 0x403B

# Control sequence of operation (heating/cooling)
CTRL_SEQUENCE_OF_OPERATION_ID = 0x001B

class BoschOperatingMode(t.enum8):
    """Bosh operating mode attribute values."""

    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05


class State(t.enum8):
    """Binary attribute (window open) value."""

    Off = 0x00
    On = 0x01


class BoschControlSequenceOfOperation(t.enum8):
    """Supported ControlSequenceOfOperation modes."""

    Cooling = ControlSequenceOfOperation.Cooling_Only
    Heating = ControlSequenceOfOperation.Heating_Only


class BoschThermostatCluster(CustomCluster, Thermostat):
    """Bosch thermostat cluster."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Bosch thermostat manufacturer specific attributes."""

        operating_mode = ZCLAttributeDef(
            id=OPERATING_MODE_ATTR_ID,
            type=BoschOperatingMode,
            is_manufacturer_specific=True,
        )

        pi_heating_demand = ZCLAttributeDef(
            id=VALVE_POSITION_ATTR_ID,
            # Values range from 0-100
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        window_open = ZCLAttributeDef(
            id=WINDOW_OPEN_ATTR_ID,
            type=State,
            is_manufacturer_specific=True,
        )

        boost = ZCLAttributeDef(
            id=BOOST_ATTR_ID,
            type=State,
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


(
    add_to_registry_v2("Bosch", "RBSH-RTH0-ZB-EU")
    .replaces(BoschThermostatCluster)
    .replaces(BoschUserInterfaceCluster)
    # Operating mode: controlled automatically through Thermostat.system_mode (HAVC mode).
    .enum(
        BoschThermostatCluster.AttributeDefs.operating_mode.name,
        BoschOperatingMode,
        BoschThermostatCluster.cluster_id,
        translation_key="operating_mode",
    )
    # Fast heating/boost.
    .switch(
        BoschThermostatCluster.AttributeDefs.boost.name,
        BoschThermostatCluster.cluster_id,
        translation_key="boost",
    )
    # Window open switch: manually set or through an automation.
    .switch(
        BoschThermostatCluster.AttributeDefs.window_open.name,
        BoschThermostatCluster.cluster_id,
        translation_key="window_open",
    )
    # Display time-out.
    .number(
        BoschUserInterfaceCluster.AttributeDefs.display_on_time.name,
        BoschUserInterfaceCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=1,
        translation_key="display_on_time",
    )
    # Display brightness.
    .number(
        BoschUserInterfaceCluster.AttributeDefs.display_brightness.name,
        BoschUserInterfaceCluster.cluster_id,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="display_brightness",
    )
    # Heating vs Cooling.
    .enum(
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.name,
        BoschControlSequenceOfOperation,
        BoschThermostatCluster.cluster_id,
        translation_key="ctrl_sequence_of_oper",
    )
)
