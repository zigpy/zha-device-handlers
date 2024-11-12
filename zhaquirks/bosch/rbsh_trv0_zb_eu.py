"""Device handler for Bosch RBSH-TRV0-ZB-EU thermostat."""

from typing import Any, Final, Optional, Union

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
from zigpy.zcl.foundation import Direction, ZCLAttributeDef, ZCLCommandDef

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

"""Bosch display orientation enum to uint8_t mapping."""
DISPLAY_ORIENTATION_ENUM_TO_INT_MAP = {
    BoschDisplayOrientation.Normal: 0x00,
    BoschDisplayOrientation.Flipped: 0x01,
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
            type=t.enum8,
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
            direction=Direction.Client_to_Server,
            is_manufacturer_specific=True,
        )

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """system_mode special handling.

        - turn off by setting operating_mode to Pause
        - turn on by setting operating_mode to Manual
        - add new system_mode value to the internal zigpy Cluster cache
        """

        operating_mode_attr = self.AttributeDefs.operating_mode

        result = []
        remaining_attributes = attributes.copy()
        system_mode_value = None
        operating_mode_value = None

        """Check if SYSTEM_MODE_ATTR is being written (can be numeric or string):
            - do not write it to the device since it is not supported
            - keep the value to be converted to the supported operating_mode
        """
        if SYSTEM_MODE_ATTR.id in attributes:
            remaining_attributes.pop(SYSTEM_MODE_ATTR.id)
            system_mode_value = attributes.get(SYSTEM_MODE_ATTR.id)
        elif SYSTEM_MODE_ATTR.name in attributes:
            remaining_attributes.pop(SYSTEM_MODE_ATTR.name)
            system_mode_value = attributes.get(SYSTEM_MODE_ATTR.name)

        """Check if operating_mode_attr is being written (can be numeric or string).
            - ignore incoming operating_mode when system_mode is also written
            - system_mode has priority and its value would be converted to operating_mode
            - add resulting system_mode to the internal zigpy Cluster cache
        """
        operating_mode_attribute_id = None
        if operating_mode_attr.id in attributes:
            operating_mode_attribute_id = operating_mode_attr.id
        elif operating_mode_attr.name in attributes:
            operating_mode_attribute_id = operating_mode_attr.name

        if operating_mode_attribute_id is not None:
            if system_mode_value is not None:
                operating_mode_value = remaining_attributes.pop(
                    operating_mode_attribute_id
                )
            else:
                operating_mode_value = attributes.get(operating_mode_attribute_id)

        if system_mode_value is not None:
            """Write operating_mode (from system_mode value)."""
            new_operating_mode_value = SYSTEM_MODE_TO_OPERATING_MODE_MAP[
                system_mode_value
            ]
            result += await super().write_attributes(
                {operating_mode_attr.id: new_operating_mode_value}, manufacturer
            )
            self._update_attribute(SYSTEM_MODE_ATTR.id, system_mode_value)
        elif operating_mode_value is not None:
            new_system_mode_value = OPERATING_MODE_TO_SYSTEM_MODE_MAP[
                operating_mode_value
            ]

            if new_system_mode_value == Thermostat.SystemMode.Heat:
                """Heating or cooling? Depends on both operating_mode and ctrl_sequence_of_operation."""
                ctrl_sequence_of_oper_attr = (
                    Thermostat.AttributeDefs.ctrl_sequence_of_oper
                )
                successful_r, failed_r = await super().read_attributes(
                    [ctrl_sequence_of_oper_attr.name], True, False, manufacturer
                )
                if ctrl_sequence_of_oper_attr.name in successful_r:
                    ctrl_sequence_of_oper_value = successful_r.pop(
                        ctrl_sequence_of_oper_attr.name
                    )
                    if (
                        ctrl_sequence_of_oper_value
                        == BoschControlSequenceOfOperation.Cooling
                    ):
                        new_system_mode_value = Thermostat.SystemMode.Cool

            self._update_attribute(SYSTEM_MODE_ATTR.id, new_system_mode_value)
        else:
            """Sync system_mode with ctrl_sequence_of_oper."""
            ctrl_sequence_of_oper_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper

            ctrl_sequence_of_oper_value = None
            if ctrl_sequence_of_oper_attr.id in attributes:
                ctrl_sequence_of_oper_value = attributes.get(
                    ctrl_sequence_of_oper_attr.id
                )
            elif ctrl_sequence_of_oper_attr.name in attributes:
                ctrl_sequence_of_oper_value = attributes.get(
                    ctrl_sequence_of_oper_attr.name
                )

            if ctrl_sequence_of_oper_value is not None:
                successful_r, failed_r = await super().read_attributes(
                    [operating_mode_attr.name], True, False, manufacturer
                )
                if operating_mode_attr.name in successful_r:
                    operating_mode_attr_value = successful_r.pop(
                        operating_mode_attr.name
                    )
                    if operating_mode_attr_value == BoschOperatingMode.Manual:
                        new_system_mode_value = Thermostat.SystemMode.Heat
                        if (
                            ctrl_sequence_of_oper_value
                            == BoschControlSequenceOfOperation.Cooling
                        ):
                            new_system_mode_value = Thermostat.SystemMode.Cool

                        self._update_attribute(
                            SYSTEM_MODE_ATTR.id, new_system_mode_value
                        )

        """Write the remaining attributes to thermostat cluster."""
        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, manufacturer)
        return result

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
    ):
        """system_mode special handling.

        - read and convert operating_mode to system_mode.
        """

        operating_mode_attr = self.AttributeDefs.operating_mode

        successful_r, failed_r = {}, {}
        remaining_attributes = attributes.copy()
        system_mode_attribute_id = None

        """Check if SYSTEM_MODE_ATTR is being read (can be numeric or string)."""
        if SYSTEM_MODE_ATTR.id in attributes:
            system_mode_attribute_id = SYSTEM_MODE_ATTR.id
        elif SYSTEM_MODE_ATTR.name in attributes:
            system_mode_attribute_id = SYSTEM_MODE_ATTR.name

        """Read operating_mode instead and convert it to system_mode."""
        if system_mode_attribute_id is not None:
            remaining_attributes.remove(system_mode_attribute_id)

            ctrl_sequence_of_oper_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper

            successful_r, failed_r = await super().read_attributes(
                [operating_mode_attr.name, ctrl_sequence_of_oper_attr.name],
                allow_cache,
                only_cache,
                manufacturer,
            )
            if operating_mode_attr.name in successful_r:
                operating_mode_value = successful_r.pop(operating_mode_attr.name)
                system_mode_value = OPERATING_MODE_TO_SYSTEM_MODE_MAP[
                    operating_mode_value
                ]

                """Heating or cooling? Depends on both operating_mode and ctrl_sequence_of_operation."""
                if ctrl_sequence_of_oper_attr.name in successful_r:
                    ctrl_sequence_of_oper_value = successful_r.pop(
                        ctrl_sequence_of_oper_attr.name
                    )
                    if (
                        ctrl_sequence_of_oper_value
                        == BoschControlSequenceOfOperation.Cooling
                        and system_mode_value == Thermostat.SystemMode.Heat
                    ):
                        system_mode_value = Thermostat.SystemMode.Cool

                successful_r[system_mode_attribute_id] = system_mode_value
                self._update_attribute(SYSTEM_MODE_ATTR.id, system_mode_value)

        """Read remaining attributes from thermostat cluster."""
        if remaining_attributes:
            remaining_result = await super().read_attributes(
                remaining_attributes, allow_cache, only_cache, manufacturer
            )

            successful_r.update(remaining_result[0])
            failed_r.update(remaining_result[1])

        return successful_r, failed_r

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """system_mode special handling.

        - ignore updates of system_mode coming from device (TRV incorrectly
          reports being in Heat mode, even when turned off).
        """

        """Pass-through anything that is not related to attributes reporting."""
        if hdr.command_id != foundation.GeneralCommand.Report_Attributes:
            return super().handle_cluster_general_request(
                hdr, args, dst_addressing=dst_addressing
            )

        """Pass-through reports of all attributes, except for system_mode."""
        has_system_mode_report = False
        for attr in args.attribute_reports:
            if attr.attrid == SYSTEM_MODE_ATTR.id:
                has_system_mode_report = True
                break

        if not has_system_mode_report:
            return super().handle_cluster_general_request(
                hdr, args, dst_addressing=dst_addressing
            )
        else:
            update_attributes = [
                attr
                for attr in args.attribute_reports
                if attr.attrid != SYSTEM_MODE_ATTR.id
            ]
            if len(update_attributes) > 0:
                msg = foundation.GENERAL_COMMANDS[
                    foundation.GeneralCommand.Report_Attributes
                ].schema(attribute_reports=update_attributes)
                return super().handle_cluster_general_request(
                    hdr, msg, dst_addressing=dst_addressing
                )


class BoschUserInterfaceCluster(CustomCluster, UserInterface):
    """Bosch UserInterface cluster."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Bosch user interface manufacturer specific attributes."""

        display_orientation: Final = ZCLAttributeDef(
            id=SCREEN_ORIENTATION_ATTR_ID,
            # To be matched to BoschDisplayOrientation enum.
            type=t.uint8_t,
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

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """display_orientation special handling.

        - convert from enum to uint8_t
        """
        display_orientation_attr = self.AttributeDefs.display_orientation

        remaining_attributes = attributes.copy()
        display_orientation_attribute_id = None

        """Check if display_orientation is being written (can be numeric or string)."""
        if display_orientation_attr.id in attributes:
            display_orientation_attribute_id = display_orientation_attr.id
        elif display_orientation_attr.name in attributes:
            display_orientation_attribute_id = display_orientation_attr.name

        if display_orientation_attribute_id is not None:
            display_orientation_value = remaining_attributes.pop(
                display_orientation_attribute_id
            )
            new_display_orientation_value = DISPLAY_ORIENTATION_ENUM_TO_INT_MAP[
                display_orientation_value
            ]
            remaining_attributes[display_orientation_attribute_id] = (
                new_display_orientation_value
            )

        return await super().write_attributes(remaining_attributes, manufacturer)


(
    QuirkBuilder("BOSCH", "RBSH-TRV0-ZB-EU")
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
        fallback_name="Boost",
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
    # Local temperature calibration.
    .number(
        Thermostat.AttributeDefs.local_temperature_calibration.name,
        BoschThermostatCluster.cluster_id,
        min_value=-5,
        max_value=5,
        step=0.1,
        multiplier=0.1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature offset",
    )
    .add_to_registry()
)
