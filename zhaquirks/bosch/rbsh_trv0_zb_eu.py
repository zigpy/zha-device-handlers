"""Device handler for Bosch RBSH-TRV0-ZB-EU thermostat."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    Thermostat,
    UserInterface,
)
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef, ZCLCommandDef

"""Bosch specific thermostat attribute ids."""

# Mode of operation with values BoschOperatingMode.
OPERATING_MODE_ATTR_ID = 0x4007

# Valve position: 0% - 100%
VALVE_POSITION_ATTR_ID = 0x4020

# Valve adaptation status.
VALVE_ADAPT_STATUS_ATTR_ID = 0x4022

# Remote measured temperature.
REMOTE_TEMPERATURE_ATTR_ID = 0x4040

# Window open switch (changes to a lower target temperature when on).
WINDOW_OPEN_ATTR_ID = 0x4042

# Boost heating preset mode.
BOOST_HEATING_ATTR_ID = 0x4043

"""Bosch specific user interface attribute ids."""

# Display orientation with values BoschDisplayOrientation.
SCREEN_ORIENTATION_ATTR_ID = 0x400B

# Displayed temperature with values BoschDisplayedTemperature.
DISPLAY_MODE_ATTR_ID = 0x4039

# Display on-time (5s - 30s).
SCREEN_TIMEOUT_ATTR_ID = 0x403A

# Display brightness (0 - 10).
SCREEN_BRIGHTNESS_ATTR_ID = 0x403B

# Control sequence of operation (heating/cooling)
CTRL_SEQUENCE_OF_OPERATION_ID = Thermostat.AttributeDefs.ctrl_sequence_of_oper.id

"""Bosch specific commands."""

# Trigger valve calibration.
CALIBRATE_VALVE_CMD_ID = 0x41


class BoschOperatingMode(t.enum8):
    """Bosch operating mode attribute values."""

    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05


class BoschValveAdaptStatus(t.enum8):
    """Bosch valve adapt status attribute values."""

    Unknown = 0x00
    ReadyToCalibrate = 0x01
    CalibrationInProgress = 0x02
    Error = 0x03
    Success = 0x04


class State(t.enum8):
    """Binary attribute (window open) value."""

    Off = 0x00
    On = 0x01


class BoschDisplayOrientation(t.enum8):
    """Bosch display orientation attribute values."""

    Normal = 0x00
    Flipped = 0x01


class BoschDisplayedTemperature(t.enum8):
    """Bosch displayed temperature attribute values."""

    Target = 0x00
    Measured = 0x01


class BoschControlSequenceOfOperation(t.enum8):
    """Supported ControlSequenceOfOperation modes."""

    Cooling = ControlSequenceOfOperation.Cooling_Only
    Heating = ControlSequenceOfOperation.Heating_Only


"""HA thermostat attribute that needs special handling in the Bosch thermostat entity."""
SYSTEM_MODE_ATTR = Thermostat.AttributeDefs.system_mode

"""Bosch operating mode to HA system mode mapping."""
OPERATING_MODE_TO_SYSTEM_MODE_MAP = {
    BoschOperatingMode.Schedule: Thermostat.SystemMode.Auto,
    BoschOperatingMode.Manual: Thermostat.SystemMode.Heat,
    BoschOperatingMode.Pause: Thermostat.SystemMode.Off,
}

"""HA system mode to Bosch operating mode mapping."""
SYSTEM_MODE_TO_OPERATING_MODE_MAP = {
    Thermostat.SystemMode.Off: BoschOperatingMode.Pause,
    Thermostat.SystemMode.Heat: BoschOperatingMode.Manual,
    Thermostat.SystemMode.Cool: BoschOperatingMode.Manual,
    Thermostat.SystemMode.Auto: BoschOperatingMode.Schedule,
}

"""Bosch Attributes Reporting Configuration"""
BOSCH_ATTR_REPORT_CONFIG = ReportingConfig(
    min_interval=10, max_interval=10800, reportable_change=1
)


class BoschThermostatCluster(CustomCluster, Thermostat):
    """Bosch thermostat cluster."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Bosch thermostat manufacturer specific attributes."""

        operating_mode: Final = ZCLAttributeDef(
            id=OPERATING_MODE_ATTR_ID,
            type=BoschOperatingMode,
            is_manufacturer_specific=True,
        )

        pi_heating_demand: Final = ZCLAttributeDef(
            id=VALVE_POSITION_ATTR_ID,
            # Values range from 0-100
            type=t.uint8_t,
            zcl_type=DataTypeId.enum8,
            is_manufacturer_specific=True,
        )

        valve_adapt_status: Final = ZCLAttributeDef(
            id=VALVE_ADAPT_STATUS_ATTR_ID,
            type=BoschValveAdaptStatus,
            is_manufacturer_specific=True,
        )

        window_open: Final = ZCLAttributeDef(
            id=WINDOW_OPEN_ATTR_ID, type=State, is_manufacturer_specific=True
        )

        boost_heating: Final = ZCLAttributeDef(
            id=BOOST_HEATING_ATTR_ID, type=State, is_manufacturer_specific=True
        )

        remote_temperature: Final = ZCLAttributeDef(
            id=REMOTE_TEMPERATURE_ATTR_ID, type=t.int16s, is_manufacturer_specific=True
        )

    class ServerCommandDefs(Thermostat.ServerCommandDefs):
        """Bosch thermostat manufacturer specific server commands."""

        calibrate_valve: Final = ZCLCommandDef(
            id=CALIBRATE_VALVE_CMD_ID,
            schema={},
            is_manufacturer_specific=True,
        )

    async def write_attribute_override_system_mode(
        self, value: Thermostat.SystemMode
    ) -> foundation.WriteAttributesResponse:
        """Write system_mode by converting to operating_mode."""
        new_operating_mode_value = SYSTEM_MODE_TO_OPERATING_MODE_MAP[value]
        return await super().write_attributes(
            {self.AttributeDefs.operating_mode: new_operating_mode_value}
        )

    async def read_attribute_override_system_mode(self) -> Thermostat.SystemMode:
        """Read system_mode by converting operating_mode."""
        successful_r, failed_r = await super().read_attributes(
            [
                self.AttributeDefs.operating_mode,
                Thermostat.AttributeDefs.ctrl_sequence_of_oper,
            ],
        )

        operating_mode_value = successful_r[self.AttributeDefs.operating_mode]
        system_mode_value = OPERATING_MODE_TO_SYSTEM_MODE_MAP[operating_mode_value]

        if Thermostat.AttributeDefs.ctrl_sequence_of_oper in successful_r:
            ctrl_sequence_of_oper_value = successful_r[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper
            ]
            if (
                ctrl_sequence_of_oper_value == BoschControlSequenceOfOperation.Cooling
                and system_mode_value == Thermostat.SystemMode.Heat
            ):
                system_mode_value = Thermostat.SystemMode.Cool

        return system_mode_value

    def report_attribute_override_system_mode(
        self, value: Thermostat.SystemMode
    ) -> Thermostat.SystemMode | None:
        """Ignore system_mode reports from device.

        TRV incorrectly reports being in Heat mode, even when turned off.
        """
        return None


class BoschUserInterfaceCluster(CustomCluster, UserInterface):
    """Bosch UserInterface cluster."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Bosch user interface manufacturer specific attributes."""

        display_orientation: Final = ZCLAttributeDef(
            id=SCREEN_ORIENTATION_ATTR_ID,
            type=BoschDisplayOrientation,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )

        display_on_time: Final = ZCLAttributeDef(
            id=SCREEN_TIMEOUT_ATTR_ID,
            # Usable values range from 5-30
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        display_brightness: Final = ZCLAttributeDef(
            id=SCREEN_BRIGHTNESS_ATTR_ID,
            # Values range from 0-10
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        displayed_temperature: Final = ZCLAttributeDef(
            id=DISPLAY_MODE_ATTR_ID,
            type=BoschDisplayedTemperature,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("BOSCH", "RBSH-TRV0-ZB-EU")
    .applies_to("BOSCH", "RBSH-TRV1-ZB-EU")
    .replaces(BoschThermostatCluster)
    .replaces(BoschUserInterfaceCluster)
    # Operating mode - read-only: controlled automatically through Thermostat.system_mode (HAVC mode).
    .enum(
        BoschThermostatCluster.AttributeDefs.operating_mode.name,
        BoschOperatingMode,
        BoschThermostatCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    # Valve adapt status - read-only.
    .enum(
        BoschThermostatCluster.AttributeDefs.valve_adapt_status.name,
        BoschValveAdaptStatus,
        BoschThermostatCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        translation_key="valve_adapt_status",
        fallback_name="Valve adaptation status",
    )
    # Fast heating/boost.
    .switch(
        BoschThermostatCluster.AttributeDefs.boost_heating.name,
        BoschThermostatCluster.cluster_id,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
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
    # Remote temperature.
    .number(
        BoschThermostatCluster.AttributeDefs.remote_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        fallback_name="Remote temperature",
    )
    # Valve calibration.
    .command_button(
        BoschThermostatCluster.ServerCommandDefs.calibrate_valve.name,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="calibrate_valve",
        fallback_name="Calibrate valve",
    )
    # Display temperature.
    .enum(
        BoschUserInterfaceCluster.AttributeDefs.displayed_temperature.name,
        BoschDisplayedTemperature,
        BoschUserInterfaceCluster.cluster_id,
        translation_key="displayed_temperature",
        fallback_name="Displayed temperature",
    )
    # Display orientation.
    .enum(
        BoschUserInterfaceCluster.AttributeDefs.display_orientation.name,
        BoschDisplayOrientation,
        BoschUserInterfaceCluster.cluster_id,
        translation_key="display_orientation",
        fallback_name="Display orientation",
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
    # Heating vs Cooling.
    .enum(
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.name,
        BoschControlSequenceOfOperation,
        BoschThermostatCluster.cluster_id,
        translation_key="ctrl_sequence_of_oper",
        fallback_name="Control sequence",
    )
    .add_to_registry()
)
