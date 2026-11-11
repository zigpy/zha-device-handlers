"""Device handler for Bosch RBSH-TRV0-ZB-EU thermostat."""

from typing import Any, Final

from zha.application.platforms.number import BoschThermostatLocalTempCalibration
from zha.application.platforms.sensor import SetpointChangeSource
from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    Thermostat,
    UserInterface,
)
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityFilter,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

# Bosch manufacturer code, sent with all manufacturer specific requests.
BOSCH_MANUFACTURER_CODE = 0x1209

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

# Error state bitmap, bit n set means error E(n+1).
ERROR_STATE_ATTR_ID = 0x5000

# Set by the TRV when it requests a valve adaptation (e.g. after an update).
AUTOMATIC_VALVE_ADAPT_ATTR_ID = 0x5010

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

"""Valve adapt status values in which a valve adaptation can be started."""
VALVE_ADAPT_STARTABLE = (
    BoschValveAdaptStatus.ReadyToCalibrate,
    BoschValveAdaptStatus.Error,
)

"""Battery alarm state bits 0-3, 10-13 and 20-23: low battery on any source."""
BATTERY_LOW_MASK = 0x00F03C0F


def format_error_state(value: int) -> str:
    """Return "ok" or the active error codes, e.g. "E01 - E03"."""

    errors = [f"E{bit + 1:02d}" for bit in range(8) if value & (1 << bit)]
    return " - ".join(errors) if errors else "ok"


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

        error_state: Final = ZCLAttributeDef(
            id=ERROR_STATE_ATTR_ID,
            type=t.bitmap8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

        automatic_valve_adapt: Final = ZCLAttributeDef(
            id=AUTOMATIC_VALVE_ADAPT_ATTR_ID,
            type=t.uint8_t,
            zcl_type=DataTypeId.enum8,
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(Thermostat.ServerCommandDefs):
        """Bosch thermostat manufacturer specific server commands."""

        calibrate_valve: Final = ZCLCommandDef(
            id=CALIBRATE_VALVE_CMD_ID,
            schema={},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    # Progress of the valve adaptation requested by the TRV: whether the
    # calibration command was sent, is still being sent, and whether the TRV
    # has run an adaptation since. A valve that keeps failing is not adapted
    # again on every status report.
    _valve_adapt_sent: bool = False
    _valve_adapt_sending: bool = False
    _valve_adapt_ran: bool = False

    def _update_attribute(
        self, attrid: int | t.uint16_t | foundation.ZCLAttributeDef, value: Any
    ) -> None:
        """Track the valve adaptation requested by the TRV."""

        super()._update_attribute(attrid, value)

        if isinstance(attrid, foundation.ZCLAttributeDef):
            attrid = attrid.id

        if attrid == AUTOMATIC_VALVE_ADAPT_ATTR_ID:
            if not value:
                self._reset_valve_adaptation()
                return
            ignored = False
        elif attrid == VALVE_ADAPT_STATUS_ATTR_ID:
            if value == BoschValveAdaptStatus.Success:
                self._reset_valve_adaptation()
                return
            if value == BoschValveAdaptStatus.CalibrationInProgress:
                self._valve_adapt_ran = True
                return
            # still ready to calibrate after the command: the TRV ignored it
            ignored = value == BoschValveAdaptStatus.ReadyToCalibrate
        else:
            return

        self._check_valve_adaptation(ignored)

    def _reset_valve_adaptation(self) -> None:
        """Forget the adaptation, the next request starts from scratch."""

        self._valve_adapt_sent = False
        self._valve_adapt_ran = False

    def _check_valve_adaptation(self, ignored: bool) -> None:
        """Start the requested valve adaptation if the TRV allows it.

        The command is sent again only when the TRV reports ready to calibrate
        again without having run an adaptation, i.e. it ignored the command.
        After a run, or an error right after the command, it is not.
        """

        if (
            self.get(self.AttributeDefs.automatic_valve_adapt.name)
            and self.get(self.AttributeDefs.valve_adapt_status.name)
            in VALVE_ADAPT_STARTABLE
            and not self._valve_adapt_sending
            and not self._valve_adapt_ran
            and (not self._valve_adapt_sent or ignored)
        ):
            self._valve_adapt_sent = True
            self._valve_adapt_sending = True
            self.create_catching_task(self._start_valve_adaptation())

    async def _start_valve_adaptation(self) -> None:
        """Send the calibration command, allow a retry if it was not delivered."""

        try:
            await self.calibrate_valve()
        except (TimeoutError, ZigbeeException):
            self._valve_adapt_sent = False
            raise
        finally:
            self._valve_adapt_sending = False

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

        if system_mode_value is not None:
            """Write operating_mode (from system_mode value)."""
            new_operating_mode_value = SYSTEM_MODE_TO_OPERATING_MODE_MAP[
                system_mode_value
            ]
            result += await super().write_attributes(
                {operating_mode_attr.id: new_operating_mode_value}, **kwargs
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

            self._update_attribute(SYSTEM_MODE_ATTR.id, new_system_mode_value)
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
            # Usable values range from 5-30
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
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        translation_key="window_open",
        fallback_name="Window open",
    )
    # Remote temperature: must be resent at least every 30 minutes, the TRV
    # falls back to its internal sensor otherwise.
    .number(
        BoschThermostatCluster.AttributeDefs.remote_temperature.name,
        BoschThermostatCluster.cluster_id,
        min_value=0,
        max_value=35,
        step=0.1,
        multiplier=0.01,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="remote_temperature",
        fallback_name="Remote temperature",
    )
    # Local temperature offset: replaces the default ZHA entity, which is not
    # created as long as the attribute was never read.
    .removes_entity(
        EntityFilter(
            entity_cls=BoschThermostatLocalTempCalibration,
            endpoint_id=1,
            cluster_id=Thermostat.cluster_id,
        )
    )
    .number(
        Thermostat.AttributeDefs.local_temperature_calibration.name,
        BoschThermostatCluster.cluster_id,
        min_value=-5,
        max_value=5,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        mode="box",
        multiplier=0.1,
        attribute_initialized_from_cache=False,
        unique_id_suffix=f"{Thermostat.cluster_id}-local_temperature_calibration",
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    # Setpoint change source: replaces the default ZHA sensor, which does not
    # configure reporting.
    .removes_entity(
        EntityFilter(
            entity_cls=SetpointChangeSource,
            endpoint_id=1,
            cluster_id=Thermostat.cluster_id,
        )
    )
    .enum(
        Thermostat.AttributeDefs.setpoint_change_source.name,
        Thermostat.SetpointChangeSource,
        BoschThermostatCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        unique_id_suffix=f"{Thermostat.cluster_id}-setpoint_change_source",
        translation_key="setpoint_change_source",
        fallback_name="Setpoint change source",
    )
    # Error state: "ok" or the active error codes.
    .sensor(
        BoschThermostatCluster.AttributeDefs.error_state.name,
        BoschThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=format_error_state,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        translation_key="error_status",
        fallback_name="Error status",
    )
    # Valve adaptation requested by the TRV, started automatically.
    .binary_sensor(
        BoschThermostatCluster.AttributeDefs.automatic_valve_adapt.name,
        BoschThermostatCluster.cluster_id,
        attribute_converter=bool,
        attribute_initialized_from_cache=False,
        translation_key="automatic_valve_adapt",
        fallback_name="Automatic valve adaptation requested",
    )
    # Low battery.
    .binary_sensor(
        PowerConfiguration.AttributeDefs.battery_alarm_state.name,
        PowerConfiguration.cluster_id,
        device_class=BinarySensorDeviceClass.BATTERY,
        attribute_converter=lambda value: bool(value & BATTERY_LOW_MASK),
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        translation_key="battery_low",
        fallback_name="Battery low",
    )
    # Child lock: an on/off switch next to the multi-level default select,
    # disabled by default so existing setups keep using the select.
    .switch(
        UserInterface.AttributeDefs.keypad_lockout.name,
        BoschUserInterfaceCluster.cluster_id,
        reporting_config=BOSCH_ATTR_REPORT_CONFIG,
        initially_disabled=True,
        translation_key="child_lock",
        fallback_name="Child lock",
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
