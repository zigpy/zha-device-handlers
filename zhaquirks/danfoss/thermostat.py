"""Module to handle quirks of the Danfoss thermostat.

manufacturer specific attributes to control displaying and specific configuration.

ZCL Attributes Supported:
    0x0201 - 0x0025: programing_oper_mode  # Danfoss deviated from the spec
    all - 0xFFFD: cluster_revision

    0x0201 - pi_heating_demand (0x0008),
    0x0201 - min_heat_setpoint_limit (0x0015)
    0x0201 - max_heat_setpoint_limit (0x0016)
    0x0201 - setpoint_change_source (0x0030)
    0x0201 - abs_min_heat_setpoint_limit (0x0003)=5
    0x0201 - abs_max_heat_setpoint_limit (0x0004)=35
    0x0201 - start_of_week (0x0020)=Monday
    0x0201 - number_of_weekly_transitions (0x0021)=42
    0x0201 - number_of_daily_transitions (0x0022)=6
    0x0204: keypad_lockout (0x0001)

ZCL Commands Supported:
    0x0201 - SetWeeklySchedule (0x01)
    0x0201 - GetWeeklySchedule (0x02)
    0x0201 - ClearWeeklySchedule (0x03)

Broken ZCL Attributes:
    0x0204 - 0x0000: Writing doesn't seem to do anything
"""


from datetime import datetime

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.types import uint16_t
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

DANFOSS = "Danfoss"
HIVE = DANFOSS
POPP = "D5X84YU"

OCCUPIED_HEATING_SETPOINT_NAME = "occupied_heating_setpoint"
SYSTEM_MODE_NAME = "system_mode"

OCCUPIED_HEATING_SETPOINT_THERM_ID = uint16_t(0x0012)
SETPOINT_CHANGE_THERM_ID = uint16_t(0x0012)
MIN_HEAT_SETPOINT_LIMIT_THERM_ID = uint16_t(0x0015)

SETPOINT_COMMAND_AGGRESSIVE_VAL = 0x01

SYSTEM_MODE_THERM_OFF_VAL = 0x00
SYSTEM_MODE_THERM_ON_VAL = 0x04


class DanfossOperationModeEnum(t.bitmap8):
    """Nonstandard implementation of Programming Operation Mode from Danfoss.
    The official specification still works: 0x0 or 0x1, but Danfoss added a preheat bit
    """

    Manual = 0b00000000
    Schedule = 0b00000001
    Manual_Preheat = 0b00000010
    Schedule_Preheat = 0b00000011


class CustomizedStandardCluster(CustomCluster):
    """Danfoss customized standard clusters by adding custom attributes
    Danfoss doesn't allow standard attributes when manufacturer specific is requested

    Therefore, this subclass separates manufacturer specific and standard attributes before
    Zigbee commands allowing manufacturer specific to be passed
    """

    @staticmethod
    def combine_results(*result_lists):
        result_global = [[], []]
        for result in result_lists:
            if len(result) == 1:
                result_global[0].extend(result[0])
            elif len(result) == 2:
                result_global[0].extend(result[0])
                result_global[1].extend(result[1])

        return result_global

    async def _configure_reporting(self, records, *args, **kwargs):
        """Configure reporting ZCL foundation command."""
        records_specific = [
            e for e in records if self.attributes[e.attrid].is_manufacturer_specific
        ]
        records_standard = [
            e for e in records if not self.attributes[e.attrid].is_manufacturer_specific
        ]

        result_specific = await super()._configure_reporting(
            records_specific, *args, **kwargs
        )
        result_standard = await super()._configure_reporting(
            records_standard, *args, **kwargs
        )

        return self.combine_results(result_specific, result_standard)

    async def _read_attributes(self, attr_ids, *args, **kwargs):
        """Read attributes ZCL foundation command."""

        attr_ids_specific = [
            e for e in attr_ids if self.attributes[e].is_manufacturer_specific
        ]
        attr_ids_standard = [
            e for e in attr_ids if not self.attributes[e].is_manufacturer_specific
        ]

        result_specific = await super()._read_attributes(
            attr_ids_specific, *args, **kwargs
        )
        result_standard = await super()._read_attributes(
            attr_ids_standard, *args, **kwargs
        )
        return self.combine_results(result_specific, result_standard)


class DanfossThermostatCluster(CustomizedStandardCluster, Thermostat):
    """Danfoss cluster for standard and proprietary danfoss attributes"""

    class ServerCommandDefs(Thermostat.ServerCommandDefs):
        setpoint_command = ZCLCommandDef(
            id=0x40,
            # Types
            # 0: Schedule (relatively slow)
            # 1: User Interaction (aggressive change)
            # 2: Preheat (invisible to user)
            schema={"type": t.enum8, "heating_setpoint": t.int16s},
            is_manufacturer_specific=True,
        )

        # for synchronizing multiple TRVs preheating
        preheat_command = ZCLCommandDef(
            id=0x42,
            # Force: 0 means force, other values for future needs
            schema={"force": t.enum8, "timestamp": t.uint32_t},
            is_manufacturer_specific=True,
        )

    class AttributeDefs(Thermostat.AttributeDefs):
        open_window_detection = ZCLAttributeDef(
            id=0x4000, type=t.enum8, access="rp", is_manufacturer_specific=True
        )
        external_open_window_detected = ZCLAttributeDef(
            id=0x4003, type=t.Bool, access="rpw", is_manufacturer_specific=True
        )
        window_open_feature = ZCLAttributeDef(
            id=0x4051, type=t.Bool, access="rpw", is_manufacturer_specific=True
        )
        exercise_day_of_week = ZCLAttributeDef(
            id=0x4010, type=t.enum8, access="rpw", is_manufacturer_specific=True
        )
        exercise_trigger_time = ZCLAttributeDef(
            id=0x4011, type=t.uint16_t, access="rpw", is_manufacturer_specific=True
        )
        mounting_mode_active = ZCLAttributeDef(
            id=0x4012, type=t.Bool, access="rp", is_manufacturer_specific=True
        )
        mounting_mode_control = ZCLAttributeDef(
            id=0x4013, type=t.Bool, access="rpw", is_manufacturer_specific=True
        )
        orientation = ZCLAttributeDef(
            id=0x4014, type=t.enum8, access="rpw", is_manufacturer_specific=True
        )
        external_measured_room_sensor = ZCLAttributeDef(
            id=0x4015, type=t.int16s, access="rpw", is_manufacturer_specific=True
        )
        radiator_covered = ZCLAttributeDef(
            id=0x4016, type=t.Bool, access="rpw", is_manufacturer_specific=True
        )
        heat_available = ZCLAttributeDef(
            id=0x4030, type=t.Bool, access="rpw", is_manufacturer_specific=True
        )
        heat_required = ZCLAttributeDef(
            id=0x4031, type=t.Bool, access="rp", is_manufacturer_specific=True
        )
        load_balancing_enable = ZCLAttributeDef(
            id=0x4032, type=t.Bool, access="rpw", is_manufacturer_specific=True
        )
        load_room_mean = ZCLAttributeDef(
            id=0x4040, type=t.int16s, access="rpw", is_manufacturer_specific=True
        )
        load_estimate = ZCLAttributeDef(
            id=0x404A, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        control_algorithm_scale_factor = ZCLAttributeDef(
            id=0x4020, type=t.uint8_t, access="rpw", is_manufacturer_specific=True
        )
        regulation_setpoint_offset = ZCLAttributeDef(
            id=0x404B, type=t.int8s, access="rpw", is_manufacturer_specific=True
        )
        adaptation_run_control = ZCLAttributeDef(
            id=0x404C, type=t.enum8, access="rw", is_manufacturer_specific=True
        )
        adaptation_run_status = ZCLAttributeDef(
            id=0x404D, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        adaptation_run_settings = ZCLAttributeDef(
            id=0x404E, type=t.bitmap8, access="rw", is_manufacturer_specific=True
        )
        preheat_status = ZCLAttributeDef(
            id=0x404F, type=t.Bool, access="rp", is_manufacturer_specific=True
        )
        preheat_time = ZCLAttributeDef(
            id=0x4050, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )

        programing_oper_mode = ZCLAttributeDef(
            id=0x0025,
            type=DanfossOperationModeEnum,
            access="rpw",
            is_manufacturer_specific=True,
        )  # Danfoss deviated from the spec

    async def write_attributes(self, attributes, manufacturer=None):
        """There are 2 types of setpoint changes:
            Fast and Slow
            Fast is used for immediate changes; this is done using a command (setpoint_command)
            Slow is used for scheduled changes; this is done using an attribute (occupied_heating_setpoint)

        system mode=off is not implemented on Danfoss; this is emulated by setting setpoint to the minimum setpoint
        In case of a change on occupied_heating_setpoint or system mode=off, a fast setpoint change is done
        """

        fast_setpoint_change = None

        if OCCUPIED_HEATING_SETPOINT_NAME in attributes:
            # On Danfoss an immediate setpoint change is done through a command
            # store for later in fast_setpoint_change and remove from attributes
            fast_setpoint_change = attributes[OCCUPIED_HEATING_SETPOINT_NAME]

        # if: system_mode = off
        if attributes.get(SYSTEM_MODE_NAME) == SYSTEM_MODE_THERM_OFF_VAL:
            # Thermostatic Radiator Valves from Danfoss cannot be turned off to prevent damage during frost
            # just turn setpoint down to minimum temperature using fast_setpoint_change
            fast_setpoint_change = self._attr_cache[MIN_HEAT_SETPOINT_LIMIT_THERM_ID]
            attributes[OCCUPIED_HEATING_SETPOINT_NAME] = fast_setpoint_change

            # Danfoss doesn't accept off, therefore set to On
            attributes[SYSTEM_MODE_NAME] = SYSTEM_MODE_THERM_ON_VAL

        # attributes cannot be empty, because write_res cannot be empty, but it can contain unrequested items
        write_res = await super().write_attributes(
            attributes, manufacturer=manufacturer
        )

        if fast_setpoint_change is not None:
            # On Danfoss a fast setpoint change is done through a command
            await self.setpoint_command(
                SETPOINT_COMMAND_AGGRESSIVE_VAL,
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
    """Danfoss cluster for standard and proprietary danfoss attributes"""

    class AttributeDefs(UserInterface.AttributeDefs):
        viewing_direction = ZCLAttributeDef(
            id=0x4000, type=t.enum8, access="rpw", is_manufacturer_specific=True
        )


class DanfossDiagnosticCluster(CustomizedStandardCluster, Diagnostic):
    """Danfoss cluster for standard and proprietary danfoss attributes"""

    class AttributeDefs(Diagnostic.AttributeDefs):
        sw_error_code = ZCLAttributeDef(
            id=0x4000, type=t.bitmap16, access="rp", is_manufacturer_specific=True
        )
        wake_time_avg = ZCLAttributeDef(
            id=0x4001, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        wake_time_max_duration = ZCLAttributeDef(
            id=0x4002, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        wake_time_min_duration = ZCLAttributeDef(
            id=0x4003, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        sleep_postponed_count_avg = ZCLAttributeDef(
            id=0x4004, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        sleep_postponed_count_max = ZCLAttributeDef(
            id=0x4005, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        sleep_postponed_count_min = ZCLAttributeDef(
            id=0x4006, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        motor_step_counter = ZCLAttributeDef(
            id=0x4010, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )


class DanfossTimeCluster(CustomizedStandardCluster, Time):
    """Danfoss cluster for fixing the time."""

    async def write_time(self):
        epoch = datetime(2000, 1, 1, 0, 0, 0, 0)
        current_time = (datetime.utcnow() - epoch).total_seconds()

        time_zone = (
            datetime.fromtimestamp(86400) - datetime.utcfromtimestamp(86400)
        ).total_seconds()

        await self.write_attributes(
            {
                "time": current_time,
                "time_status": 0b00000010,  # only bit 1 can be written
                "time_zone": time_zone,
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
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
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
                    Basic,
                    PowerConfiguration,
                    Identify,
                    DanfossTimeCluster,
                    PollControl,
                    DanfossThermostatCluster,
                    DanfossUserInterfaceCluster,
                    DanfossDiagnosticCluster,
                ],
                OUTPUT_CLUSTERS: [Basic, Ota],
            }
        }
    }
