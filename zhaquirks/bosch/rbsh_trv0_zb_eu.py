"""Device handler for Bosch RBSH-TRV0-ZB-EU thermostat."""

from typing import Any, Final

from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    Thermostat,
    UserInterface,
)
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

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

BOSCH_MANUFACTURER_CODE = 0x1209


class BoschOperatingMode(t.enum8):
    """Bosch operating mode attribute values."""

    Schedule = 0x00
    Manual = 0x01
    Eco = 0x02
    Away = 0x03
    Holiday = 0x04
    Pause = 0x05


class BoschRemoteTemperatureSource(t.enum8):
    """Source used for thermostat temperature regulation."""

    Internal = 0x00
    External = 0x01


class BoschValveAdaptStatus(t.enum8):
    """Bosch valve adapt status attribute values."""

    Unknown = 0x00
    ReadyToCalibrate = 0x01
    CalibrationInProgress = 0x02
    Error = 0x03
    Success = 0x04
    FixMotorStarted = 0x05
    FixMotorFailed = 0x06
    FixMotorSuccessful = 0x07


class BoschRestartReason(t.enum8):
    """Reason for the last thermostat restart."""

    cold_start = 0x00
    warm_start = 0x01
    firmware_installed = 0x02


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
    BoschOperatingMode.Eco: Thermostat.SystemMode.Heat,
    BoschOperatingMode.Away: Thermostat.SystemMode.Heat,
    BoschOperatingMode.Holiday: Thermostat.SystemMode.Heat,
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


def _write_succeeded(
    result: list[list[foundation.WriteAttributesStatusRecord]],
) -> bool:
    """Return whether every returned attribute write succeeded."""

    records = [record for response in result for record in response]
    return bool(records) and all(
        record.status == foundation.Status.SUCCESS for record in records
    )


def get_attribute_id_or_name(
    attribute: ZCLAttributeDef, attributes: dict[str | int, Any] | list[int | str]
) -> int | str | None:
    """Return the attribute id/name when the id/name of the attribute is in the attributes list or None otherwise."""

    if attribute.id in attributes:
        return attribute.id
    elif attribute.name in attributes:
        return attribute.name
    else:
        return None


class BoschThermostatCluster(CustomCluster, Thermostat):
    """Bosch thermostat cluster."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Bosch thermostat manufacturer specific attributes."""

        operating_mode: Final = ZCLAttributeDef(
            id=OPERATING_MODE_ATTR_ID,
            type=BoschOperatingMode,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        pi_heating_demand: Final = ZCLAttributeDef(
            id=VALVE_POSITION_ATTR_ID,
            # Values range from 0-100
            type=t.uint8_t,
            zcl_type=DataTypeId.enum8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        valve_adapt_status: Final = ZCLAttributeDef(
            id=VALVE_ADAPT_STATUS_ATTR_ID,
            type=BoschValveAdaptStatus,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        window_open: Final = ZCLAttributeDef(
            id=WINDOW_OPEN_ATTR_ID,
            type=State,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        boost_heating: Final = ZCLAttributeDef(
            id=BOOST_HEATING_ATTR_ID,
            type=State,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        remote_temperature: Final = ZCLAttributeDef(
            id=REMOTE_TEMPERATURE_ATTR_ID,
            type=t.int16s,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        eco_temperature: Final = ZCLAttributeDef(
            id=0x4008, type=t.uint16_t, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        away_temperature: Final = ZCLAttributeDef(
            id=0x4009, type=t.uint16_t, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        holiday_temperature: Final = ZCLAttributeDef(
            id=0x400A, type=t.uint16_t, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        anti_freeze_enabled: Final = ZCLAttributeDef(
            id=0x400E, type=t.Bool, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        anti_freeze_temperature: Final = ZCLAttributeDef(
            id=0x400F, type=t.uint16_t, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        decalcification_day: Final = ZCLAttributeDef(
            id=0x4023, type=t.enum8, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        decalcification_hour: Final = ZCLAttributeDef(
            id=0x4024, type=t.enum8, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        remote_temperature_source: Final = ZCLAttributeDef(
            id=0x4041,
            type=BoschRemoteTemperatureSource,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        window_open_temperature: Final = ZCLAttributeDef(
            id=0x4050, type=t.enum8, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        error_state: Final = ZCLAttributeDef(
            id=0x5000, type=t.bitmap8, manufacturer_code=BOSCH_MANUFACTURER_CODE
        )

        restart_reason: Final = ZCLAttributeDef(
            id=0x5010,
            type=BoschRestartReason,
            access="r",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(Thermostat.ServerCommandDefs):
        """Bosch thermostat manufacturer specific server commands."""

        calibrate_valve: Final = ZCLCommandDef(
            id=CALIBRATE_VALVE_CMD_ID,
            schema={},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Only start valve calibration when the valve is ready for it."""
        if self.server_commands[command_id].id != CALIBRATE_VALVE_CMD_ID:
            return await super().command(command_id, *args, **kwargs)

        valve_status_attr = self.AttributeDefs.valve_adapt_status
        success, _ = await self.read_attributes([valve_status_attr.name])
        valve_status = success.get(valve_status_attr.name)
        if valve_status is None:
            raise ZigbeeException(
                "Valve calibration not started: valve status could not be read"
            )
        valve_status = BoschValveAdaptStatus(valve_status)
        if valve_status != BoschValveAdaptStatus.ReadyToCalibrate:
            raise ZigbeeException(
                "Valve calibration not started: valve status is "
                f"{valve_status.name}, not {BoschValveAdaptStatus.ReadyToCalibrate.name}"
            )

        result = await super().command(command_id, *args, **kwargs)
        status = getattr(result, "status", foundation.Status.SUCCESS)
        if status != foundation.Status.SUCCESS:
            raise ZigbeeException(
                f"Valve calibration rejected by device: {foundation.Status(status).name}"
            )
        return result

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
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
        system_mode_attribute_id = get_attribute_id_or_name(
            SYSTEM_MODE_ATTR, attributes
        )
        if system_mode_attribute_id is not None:
            remaining_attributes.pop(system_mode_attribute_id)
            system_mode_value = attributes.get(system_mode_attribute_id)

        """Check if operating_mode_attr is being written (can be numeric or string).
            - ignore incoming operating_mode when system_mode is also written
            - system_mode has priority and its value would be converted to operating_mode
            - add resulting system_mode to the internal zigpy Cluster cache
        """
        operating_mode_attribute_id = get_attribute_id_or_name(
            operating_mode_attr, attributes
        )
        if operating_mode_attribute_id is not None:
            if system_mode_value is not None:
                operating_mode_value = remaining_attributes.pop(
                    operating_mode_attribute_id
                )
            else:
                operating_mode_value = attributes.get(operating_mode_attribute_id)

        new_system_mode_value = None
        if system_mode_value is not None:
            """Write operating_mode (from system_mode value)."""
            new_operating_mode_value = SYSTEM_MODE_TO_OPERATING_MODE_MAP.get(
                system_mode_value
            )
            if new_operating_mode_value is None:
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.INVALID_VALUE,
                            attrid=SYSTEM_MODE_ATTR.id,
                        )
                    ]
                ]
            result += await super().write_attributes(
                {operating_mode_attr.id: new_operating_mode_value}, **kwargs
            )
            if _write_succeeded(result):
                self._update_attribute(operating_mode_attr.id, new_operating_mode_value)
                self._update_attribute(SYSTEM_MODE_ATTR.id, system_mode_value)
        elif operating_mode_value is not None:
            new_system_mode_value = OPERATING_MODE_TO_SYSTEM_MODE_MAP.get(
                operating_mode_value
            )
            if new_system_mode_value is None:
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.INVALID_VALUE,
                            attrid=operating_mode_attr.id,
                        )
                    ]
                ]

            if new_system_mode_value == Thermostat.SystemMode.Heat:
                """Heating or cooling? Depends on both operating_mode and ctrl_sequence_of_operation."""
                ctrl_sequence_of_oper_attr = (
                    Thermostat.AttributeDefs.ctrl_sequence_of_oper
                )
                successful_r, failed_r = await super().read_attributes(
                    [ctrl_sequence_of_oper_attr.name],
                    allow_cache=True,
                    only_cache=False,
                    **kwargs,
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

        else:
            """Sync system_mode with ctrl_sequence_of_oper."""
            ctrl_sequence_of_oper_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper

            ctrl_sequence_of_oper_attribute_id = get_attribute_id_or_name(
                ctrl_sequence_of_oper_attr, attributes
            )
            if ctrl_sequence_of_oper_attribute_id is not None:
                ctrl_sequence_of_oper_value = attributes.get(
                    ctrl_sequence_of_oper_attribute_id
                )
                if ctrl_sequence_of_oper_value is not None:
                    successful_r, failed_r = await super().read_attributes(
                        [operating_mode_attr.name],
                        allow_cache=True,
                        only_cache=False,
                        **kwargs,
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
            result += await super().write_attributes(remaining_attributes, **kwargs)
        if (
            system_mode_value is None
            and operating_mode_value is not None
            and _write_succeeded(result)
        ):
            self._update_attribute(operating_mode_attr.id, operating_mode_value)
            if new_system_mode_value is not None:
                self._update_attribute(SYSTEM_MODE_ATTR.id, new_system_mode_value)
        return result

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        **kwargs,
    ) -> Any:
        """system_mode special handling.

        - read and convert operating_mode to system_mode.
        """

        operating_mode_attr = self.AttributeDefs.operating_mode

        successful_r, failed_r = {}, {}
        remaining_attributes = attributes.copy()

        """Check if SYSTEM_MODE_ATTR is being read (can be numeric or string)."""
        system_mode_attribute_id = get_attribute_id_or_name(
            SYSTEM_MODE_ATTR, attributes
        )
        if system_mode_attribute_id is not None:
            """Read operating_mode instead and convert it to system_mode."""

            remaining_attributes.remove(system_mode_attribute_id)

            ctrl_sequence_of_oper_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper

            successful_r, failed_r = await super().read_attributes(
                [operating_mode_attr.name, ctrl_sequence_of_oper_attr.name],
                **kwargs,
            )
            if operating_mode_attr.name in successful_r:
                operating_mode_value = successful_r.pop(operating_mode_attr.name)
                system_mode_value = OPERATING_MODE_TO_SYSTEM_MODE_MAP.get(
                    operating_mode_value
                )

                """Heating or cooling? Depends on both operating_mode and ctrl_sequence_of_operation."""
                if (
                    system_mode_value is not None
                    and ctrl_sequence_of_oper_attr.name in successful_r
                ):
                    ctrl_sequence_of_oper_value = successful_r.pop(
                        ctrl_sequence_of_oper_attr.name
                    )
                    if (
                        ctrl_sequence_of_oper_value
                        == BoschControlSequenceOfOperation.Cooling
                        and system_mode_value == Thermostat.SystemMode.Heat
                    ):
                        system_mode_value = Thermostat.SystemMode.Cool

                if system_mode_value is None:
                    failed_r[system_mode_attribute_id] = foundation.Status.INVALID_VALUE
                else:
                    successful_r[system_mode_attribute_id] = system_mode_value
                    self._update_attribute(SYSTEM_MODE_ATTR.id, system_mode_value)

        """Read remaining attributes from thermostat cluster."""
        if remaining_attributes:
            remaining_result = await super().read_attributes(
                remaining_attributes, **kwargs
            )

            successful_r.update(remaining_result[0])
            failed_r.update(remaining_result[1])

        return successful_r, failed_r

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
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
            # Process even when no attributes remain, to send any requested
            # default response
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
            type=BoschDisplayOrientation,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        display_on_time: Final = ZCLAttributeDef(
            id=SCREEN_TIMEOUT_ATTR_ID,
            # Seconds, values range from 1-255
            type=t.enum8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        display_brightness: Final = ZCLAttributeDef(
            id=SCREEN_BRIGHTNESS_ATTR_ID,
            # Values range from 0-10
            type=t.enum8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        displayed_temperature: Final = ZCLAttributeDef(
            id=DISPLAY_MODE_ATTR_ID,
            type=BoschDisplayedTemperature,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        light_ring_on_temperature_change: Final = ZCLAttributeDef(
            id=0x4031,
            type=t.enum8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
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
        attribute_initialized_from_cache=False,
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    .enum(
        BoschThermostatCluster.AttributeDefs.remote_temperature_source.name,
        BoschRemoteTemperatureSource,
        BoschThermostatCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="remote_temperature_source",
        fallback_name="Remote temperature source",
    )
    .sensor(
        BoschThermostatCluster.AttributeDefs.error_state.name,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        attribute_initialized_from_cache=False,
        translation_key="error_status",
        fallback_name="Error status",
    )
    .enum(
        BoschThermostatCluster.AttributeDefs.restart_reason.name,
        BoschRestartReason,
        BoschThermostatCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="restart_reason",
        fallback_name="Restart reason",
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
        min_value=-80,
        max_value=80,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="external_temperature_sensor_value",
        fallback_name="External temperature sensor value",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.eco_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="eco_temperature",
        fallback_name="Eco temperature",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.away_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="away_preset_temperature",
        fallback_name="Away preset temperature",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.holiday_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    .switch(
        BoschThermostatCluster.AttributeDefs.anti_freeze_enabled.name,
        BoschThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.anti_freeze_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=5,
        max_value=30,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.decalcification_day.name,
        BoschThermostatCluster.cluster_id,
        min_value=0,
        max_value=6,
        step=1,
        attribute_initialized_from_cache=False,
        translation_key="decalcification_day",
        fallback_name="Decalcification day",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.decalcification_hour.name,
        BoschThermostatCluster.cluster_id,
        min_value=0,
        max_value=23,
        step=1,
        attribute_initialized_from_cache=False,
        translation_key="decalcification_hour",
        fallback_name="Decalcification hour",
    )
    .number(
        BoschThermostatCluster.AttributeDefs.window_open_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=5,
        max_value=10,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        attribute_initialized_from_cache=False,
        translation_key="window_open_temperature",
        fallback_name="Window open temperature",
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
        attribute_initialized_from_cache=False,
        translation_key="displayed_temperature",
        fallback_name="Displayed temperature",
    )
    # Display orientation.
    .enum(
        BoschUserInterfaceCluster.AttributeDefs.display_orientation.name,
        BoschDisplayOrientation,
        BoschUserInterfaceCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="display_orientation",
        fallback_name="Display orientation",
    )
    # Display time-out. The device accepts 1, but the display stays on for
    # roughly the configured value minus one second, so 1 is never visible.
    .number(
        BoschUserInterfaceCluster.AttributeDefs.display_on_time.name,
        BoschUserInterfaceCluster.cluster_id,
        min_value=2,
        max_value=255,
        step=1,
        attribute_initialized_from_cache=False,
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
        attribute_initialized_from_cache=False,
        translation_key="display_brightness",
        fallback_name="Display brightness",
    )
    .switch(
        BoschUserInterfaceCluster.AttributeDefs.light_ring_on_temperature_change.name,
        BoschUserInterfaceCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="light_ring_on_temperature_change",
        fallback_name="Light ring on temperature change",
    )
    # Heating vs Cooling.
    .enum(
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.name,
        BoschControlSequenceOfOperation,
        BoschThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="ctrl_sequence_of_oper",
        fallback_name="Control sequence",
    )
    .add_to_registry()
)
