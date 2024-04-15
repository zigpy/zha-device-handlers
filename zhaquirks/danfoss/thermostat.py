"""Module to handle quirks of the Danfoss thermostat.

Manufacturer specific attributes to control displaying and specific configuration.

ZCL attributes supported:
    0x0201 - ThermostatProgrammingOperationMode (0x0025):
        Danfoss writes in a presentation document that it implemented a preheat function with the second bit,
        but this is contradicted by a detailed and up-to-date document.
    all    - ClusterRevision (0xFFFD)

    0x0201 - PIHeatingDemand (0x0008),
    0x0201 - MinHeatSetpointLimit (0x0015)
    0x0201 - MaxHeatSetpointLimit (0x0016)
    0x0201 - SetpointChangeSource (0x0030)
    0x0201 - AbsMinHeatSetpointLimit (0x0003)=5
    0x0201 - AbsMaxHeatSetpointLimit (0x0004)=35
    0x0201 - StartOfWeek (0x0020)=Monday
    0x0201 - NumberOfWeeklyTransitions (0x0021)=42
    0x0201 - NumberOfDailyTransitions (0x0022)=6
    0x0204 - KeypadLockout (0x0001)

ZCL commands supported:
    0x0201 - SetWeeklySchedule (0x01)
    0x0201 - GetWeeklySchedule (0x02)
    0x0201 - ClearWeeklySchedule (0x03)

Broken ZCL attributes:
    0x0204 - TemperatureDisplayMode (0x0000): Writing doesn't seem to do anything
"""
from collections.abc import Callable
from datetime import UTC, datetime
import time
from typing import Any

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.quirk_ids import DANFOSS_ALLY_THERMOSTAT

DANFOSS = "Danfoss"
HIVE = DANFOSS
POPP = "D5X84YU"

occupied_heating_setpoint = Thermostat.AttributeDefs.occupied_heating_setpoint
system_mode = Thermostat.AttributeDefs.system_mode
min_heat_setpoint_limit = Thermostat.AttributeDefs.min_heat_setpoint_limit


class DanfossViewingDirectionEnum(types.enum8):
    """Default (button above screen when looking at it) or Inverted (button below screen when looking at it)."""

    Default = 0x00
    Inverted = 0x01


class DanfossAdaptationRunControlEnum(types.enum8):
    """Initiate or Cancel adaptation run."""

    Nothing = 0x00  # not documented in all documentation, but in some places and seems to work
    Initiate = 0x01
    Cancel = 0x02


class DanfossExerciseDayOfTheWeekEnum(types.enum8):
    """Day of the week."""

    Sunday = 0
    Monday = 1
    Tuesday = 2
    Wednesday = 3
    Thursday = 4
    Friday = 5
    Saturday = 6
    Undefined = 7


class DanfossOpenWindowDetectionEnum(types.enum8):
    """Danfoss open window detection judgments."""

    Quarantine = 0x00
    Closed = 0x01
    Maybe = 0x02
    Open = 0x03
    External = 0x04


class DanfossSoftwareErrorCodeBitmap(types.bitmap16):
    """Danfoss software error code bitmap."""

    Top_pcb_sensor_error = 0x0001
    Side_pcb_sensor_error = 0x0002
    Non_volatile_memory_error = 0x0004
    Unknown_hw_error = 0x0008
    # 0x0010 = N/A
    Motor_error = 0x0020
    # 0x0040 = N/A
    Invalid_internal_communication = 0x0080
    # 0x0100 = N/A
    Invalid_clock_information = 0x0200
    # 0x0400 = N/A
    Radio_communication_error = 0x0800
    Encoder_jammed = 0x1000
    Low_battery = 0x2000
    Critical_low_battery = 0x4000
    # 0x8000 = Reserved


class DanfossAdaptationRunStatusBitmap(types.bitmap8):
    """Danfoss Adaptation run status bitmap."""

    In_progress = 0x0001
    Valve_characteristic_found = 0x0002
    Valve_characteristic_lost = 0x0004


class DanfossAdaptationRunSettingsBitmap(types.bitmap8):
    """Danfoss Adaptation run settings bitmap."""

    Disabled = 0x00  # Undocumented, but seems to work
    Enabled = 0x01


class DanfossSetpointCommandEnum(types.enum8):
    """Set behaviour to change the setpoint."""

    Schedule = 0  # relatively slow
    User_interaction = 1  # aggressive change
    Preheat = 2  # invisible to user


class DanfossPreheatCommandEnum(types.enum8):
    """Set behaviour of preheat command.

    Only one option available, but other values are possible in the future.
    """

    Force = 0


class CustomizedStandardCluster(CustomCluster):
    """Danfoss customized standard clusters by adding custom attributes.

    Danfoss doesn't allow all standard attributes when manufacturer specific is requested.
    Therefore, this subclass separates manufacturer specific and standard attributes for Zigbee commands allowing
    manufacturer specific to be passed for specific attributes, but not for standard attributes.
    """

    @staticmethod
    def combine_results(*result_lists):
        """Combine results from 1 or more result lists from zigbee commands."""
        success_global = []
        failure_global = []
        for result in result_lists:
            if len(result) == 1:
                success_global.extend(result[0])
            elif len(result) == 2:
                success_global.extend(result[0])
                failure_global.extend(result[1])

        if failure_global:
            return [success_global, failure_global]
        else:
            return [success_global]

    async def split_command(
        self,
        records: list[Any],
        func: Callable,
        extract_attrid: Callable[[Any], int],
        *args,
        **kwargs,
    ):
        """Split execution of command in one for manufacturer specific and one for standard attributes."""
        records_specific = [
            e
            for e in records
            if self.attributes[extract_attrid(e)].is_manufacturer_specific
        ]
        records_standard = [
            e
            for e in records
            if not self.attributes[extract_attrid(e)].is_manufacturer_specific
        ]

        result_specific = (
            await func(records_specific, *args, **kwargs) if records_specific else []
        )

        result_standard = (
            await func(records_standard, *args, **kwargs) if records_standard else []
        )

        return self.combine_results(result_specific, result_standard)

    async def _configure_reporting(self, records, *args, **kwargs):
        """Configure reporting ZCL foundation command."""
        return await self.split_command(
            records, super()._configure_reporting, lambda x: x.attrid, *args, **kwargs
        )

    async def _read_attributes(self, attr_ids, *args, **kwargs):
        """Read attributes ZCL foundation command."""
        return await self.split_command(
            attr_ids, super()._read_attributes, lambda x: x, *args, **kwargs
        )


class DanfossThermostatCluster(CustomizedStandardCluster, Thermostat):
    """Danfoss cluster for standard and proprietary danfoss attributes."""

    class ServerCommandDefs(Thermostat.ServerCommandDefs):
        """Server Command Definitions."""

        setpoint_command = ZCLCommandDef(
            id=0x40,
            schema={
                "type": DanfossSetpointCommandEnum,
                "heating_setpoint": types.int16s,
            },
            is_manufacturer_specific=True,
        )

        preheat_command = ZCLCommandDef(
            id=0x42,
            schema={"force": DanfossPreheatCommandEnum, "timestamp": types.uint32_t},
            is_manufacturer_specific=True,
        )

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute Definitions."""

        open_window_detection = ZCLAttributeDef(  # etrv_open_window_detection
            id=0x4000,
            type=DanfossOpenWindowDetectionEnum,
            access="rp",
            is_manufacturer_specific=True,
        )
        external_open_window_detected = ZCLAttributeDef(
            id=0x4003, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting
        exercise_day_of_week = ZCLAttributeDef(
            id=0x4010,
            type=DanfossExerciseDayOfTheWeekEnum,
            access="rw",
            is_manufacturer_specific=True,
        )
        exercise_trigger_time = ZCLAttributeDef(
            id=0x4011, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        mounting_mode_active = ZCLAttributeDef(
            id=0x4012, type=types.Bool, access="rp", is_manufacturer_specific=True
        )
        mounting_mode_control = ZCLAttributeDef(
            id=0x4013, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting
        orientation = ZCLAttributeDef(  # etrv_orientation (Horizontal = False and Vertical = True)
            id=0x4014, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting
        external_measured_room_sensor = ZCLAttributeDef(
            id=0x4015, type=types.int16s, access="rw", is_manufacturer_specific=True
        )
        radiator_covered = ZCLAttributeDef(
            id=0x4016, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting
        control_algorithm_scale_factor = (
            ZCLAttributeDef(  # values in [0x01, 0x0A] and disabled by 0x1X
                id=0x4020,
                type=types.uint8_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        )  # non-configurable reporting
        heat_available = ZCLAttributeDef(
            id=0x4030, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting
        heat_required = ZCLAttributeDef(  # heat_supply_request
            id=0x4031, type=types.Bool, access="rp", is_manufacturer_specific=True
        )
        load_balancing_enable = ZCLAttributeDef(
            id=0x4032, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting
        load_room_mean = ZCLAttributeDef(  # load_radiator_room_mean
            id=0x4040, type=types.int16s, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting (according to the documentation, you cannot read it, but it works anyway)
        load_estimate = ZCLAttributeDef(  # load_estimate_on_this_radiator
            id=0x404A, type=types.int16s, access="rp", is_manufacturer_specific=True
        )
        regulation_setpoint_offset = ZCLAttributeDef(
            id=0x404B, type=types.int8s, access="rw", is_manufacturer_specific=True
        )
        adaptation_run_control = ZCLAttributeDef(
            id=0x404C,
            type=DanfossAdaptationRunControlEnum,
            access="rw",
            is_manufacturer_specific=True,
        )  # non-configurable reporting
        adaptation_run_status = ZCLAttributeDef(
            id=0x404D,
            type=DanfossAdaptationRunStatusBitmap,
            access="rp",
            is_manufacturer_specific=True,
        )
        adaptation_run_settings = ZCLAttributeDef(
            id=0x404E,
            type=DanfossAdaptationRunSettingsBitmap,
            access="rw",
            is_manufacturer_specific=True,
        )
        preheat_status = ZCLAttributeDef(
            id=0x404F, type=types.Bool, access="rp", is_manufacturer_specific=True
        )
        preheat_time = ZCLAttributeDef(
            id=0x4050, type=types.uint32_t, access="rp", is_manufacturer_specific=True
        )
        window_open_feature = ZCLAttributeDef(  # window_open_feature_on_off
            id=0x4051, type=types.Bool, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting

    async def write_attributes(self, attributes, manufacturer=None):
        """There are 2 types of setpoint changes: Fast and Slow.

        Fast is used for immediate changes; this is done using a command (setpoint_command).
        Slow is used for scheduled changes; this is done using an attribute (occupied_heating_setpoint).
        In case of a change on occupied_heating_setpoint, a setpoint_command is used.

        Thermostatic radiator valves from Danfoss cannot be turned off to prevent damage during frost.
        This is emulated by setting setpoint to the minimum setpoint.
        """

        fast_setpoint_change = None

        if occupied_heating_setpoint.name in attributes:
            # Store setpoint for use in command
            fast_setpoint_change = attributes[occupied_heating_setpoint.name]

        if attributes.get(system_mode.name) == system_mode.type.Off:
            # Just turn setpoint down to minimum temperature using fast_setpoint_change
            fast_setpoint_change = self._attr_cache[min_heat_setpoint_limit.id]
            attributes[occupied_heating_setpoint.name] = fast_setpoint_change
            attributes[system_mode.name] = system_mode.type.Heat

        # Attributes cannot be empty, because write_res cannot be empty, but it can contain unrequested items
        write_res = await super().write_attributes(
            attributes, manufacturer=manufacturer
        )

        if fast_setpoint_change is not None:
            # On Danfoss a fast setpoint change is done through a command
            await self.setpoint_command(
                DanfossSetpointCommandEnum.User_interaction,
                fast_setpoint_change,
                manufacturer=manufacturer,
            )

        return write_res

    async def bind(self):
        """According to the documentation of Zigbee2MQTT there is a bug in the Danfoss firmware with the time.

        It doesn't request it, so it has to be fed the correct time.
        """
        await self.endpoint.time.write_time()

        return await super().bind()


class DanfossUserInterfaceCluster(CustomizedStandardCluster, UserInterface):
    """Danfoss cluster for standard and proprietary danfoss attributes."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute Definitions."""

        viewing_direction = ZCLAttributeDef(
            id=0x4000,
            type=DanfossViewingDirectionEnum,
            access="rw",
            is_manufacturer_specific=True,
        )  # non-configurable reporting


class DanfossDiagnosticCluster(CustomizedStandardCluster, Diagnostic):
    """Danfoss cluster for standard and proprietary danfoss attributes."""

    class AttributeDefs(Diagnostic.AttributeDefs):
        """Attribute Definitions."""

        sw_error_code = ZCLAttributeDef(
            id=0x4000,
            type=DanfossSoftwareErrorCodeBitmap,
            access="rpw",
            is_manufacturer_specific=True,
        )
        wake_time_avg = ZCLAttributeDef(
            id=0x4001, type=types.uint32_t, access="r", is_manufacturer_specific=True
        )
        wake_time_max_duration = ZCLAttributeDef(
            id=0x4002, type=types.uint32_t, access="r", is_manufacturer_specific=True
        )
        wake_time_min_duration = ZCLAttributeDef(
            id=0x4003, type=types.uint32_t, access="r", is_manufacturer_specific=True
        )
        sleep_postponed_count_avg = ZCLAttributeDef(
            id=0x4004, type=types.uint32_t, access="r", is_manufacturer_specific=True
        )
        sleep_postponed_count_max = ZCLAttributeDef(
            id=0x4005, type=types.uint32_t, access="r", is_manufacturer_specific=True
        )
        sleep_postponed_count_min = ZCLAttributeDef(
            id=0x4006, type=types.uint32_t, access="r", is_manufacturer_specific=True
        )
        motor_step_counter = ZCLAttributeDef(
            id=0x4010, type=types.uint32_t, access="rp", is_manufacturer_specific=True
        )

        data_logger = ZCLAttributeDef(
            id=0x4020,
            type=types.LimitedLVBytes(50),
            access="rpw",
            is_manufacturer_specific=True,
        )
        control_diagnostics = ZCLAttributeDef(
            id=0x4021,
            type=types.LimitedLVBytes(30),
            access="rp",
            is_manufacturer_specific=True,
        )
        control_diagnostics_frequency = ZCLAttributeDef(
            id=0x4022, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )  # non-configurable reporting


class DanfossTimeCluster(CustomizedStandardCluster, Time):
    """Danfoss cluster for fixing the time."""

    async def write_time(self):
        """Write time info to Time Cluster.

        It supports adjusting for daylight saving time, but this is not trivial to retrieve with the modules:
            zoneinfo, datetime or time
        """
        epoch = datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=UTC)
        current_time = (datetime.now(UTC) - epoch).total_seconds()

        await self.write_attributes(
            {
                "time": current_time,
                "time_status": 0b00000010,  # only bit 1 can be set
                "time_zone": time.timezone
            }
        )

    async def bind(self):
        """According to the documentation of Zigbee2MQTT there is a bug in the Danfoss firmware with the time.

        It doesn't request it, so it has to be fed the correct time.
        """
        result = await super().bind()
        await self.write_time()
        return result


class DanfossThermostat(CustomDevice):
    """DanfossThermostat custom device."""

    quirk_id = DANFOSS_ALLY_THERMOSTAT

    manufacturer_code = 0x1246

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 1, 3, 10, 32, 513, 516, 1026, 2821]
        # output_clusters=[0, 25]>
        MODELS_INFO: [
            (DANFOSS, "eTRV0100"),
            (DANFOSS, "eTRV0101"),
            (DANFOSS, "eTRV0103"),
            (POPP, "eT093WRO"),
            (POPP, "eT093WRG"),
            (HIVE, "TRV001"),
            (HIVE, "TRV003"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Time.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    DanfossTimeCluster,
                    DanfossThermostatCluster,
                    DanfossUserInterfaceCluster,
                    DanfossDiagnosticCluster,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id],
            }
        }
    }
