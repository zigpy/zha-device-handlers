"""Module to handle quirks of the Danfoss thermostat.

manufacturer specific attributes to control displaying and specific configuration.

manufacturer_code = 0x1246
"""
from typing import Callable, Tuple, Union

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
from zigpy.zcl.foundation import ZCLCommandDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.danfoss import DANFOSS, HIVE, POPP


class DanfossOperationModeEnum(t.bitmap8):
    """Nonstandard implementation of Programming Operation Mode from Danfoss.
    The official specification still works: 0x0 or 0x1, but Danfoss added a preheat bit
    """

    Manual = 0b00000000
    Schedule = 0b00000001
    Manual_Preheat = 0b00000010
    Schedule_Preheat = 0b00000011


OCCUPIED_HEATING_SETPOINT_NAME = "occupied_heating_setpoint"
SYSTEM_MODE_NAME = "system_mode"

OCCUPIED_HEATING_SETPOINT_THERM_ID = uint16_t(0x0012)
SETPOINT_CHANGE_THERM_ID = uint16_t(0x0012)
MIN_HEAT_SETPOINT_LIMIT_THERM_ID = uint16_t(0x0015)

SETPOINT_COMMAND_AGGRESSIVE_VAL = 0x01

SYSTEM_MODE_THERM_OFF_VAL = 0x00

# 0x0201
danfoss_thermostat_attr = {
    0x4000: ("open_window_detection", t.enum8, "rp"),
    0x4003: ("external_open_window_detected", t.Bool, "rpw"),
    0x4051: ("window_open_feature", t.Bool, "rpw"),
    0x4010: ("exercise_day_of_week", t.enum8, "rpw"),
    0x4011: ("exercise_trigger_time", t.uint16_t, "rpw"),
    0x4012: ("mounting_mode_active", t.Bool, "rp"),
    0x4013: ("mounting_mode_control", t.Bool, "rpw"),  # undocumented
    0x4014: ("orientation", t.enum8, "rpw"),
    0x4015: ("external_measured_room_sensor", t.int16s, "rpw"),
    0x4016: ("radiator_covered", t.Bool, "rpw"),
    0x4030: ("heat_available", t.Bool, "rpw"),  # undocumented
    0x4031: ("heat_required", t.Bool, "rp"),  # undocumented
    0x4032: ("load_balancing_enable", t.Bool, "rpw"),
    0x4040: ("load_room_mean", t.int16s, "rpw"),
    0x404A: ("load_estimate", t.int16s, "rp"),
    0x4020: ("control_algorithm_scale_factor", t.uint8_t, "rpw"),
    0x404B: ("regulation_setpoint_offset", t.int8s, "rpw"),
    0x404C: ("adaptation_run_control", t.enum8, "rw"),
    0x404D: ("adaptation_run_status", t.bitmap8, "rp"),
    0x404E: ("adaptation_run_settings", t.bitmap8, "rw"),
    0x404F: ("preheat_status", t.Bool, "rp"),
    0x4050: ("preheat_time", t.uint32_t, "rp"),
    0x0025: ("programing_oper_mode", DanfossOperationModeEnum, "rpw"),  # Danfoss deviated from the spec
}
# ZCL Attributes Supported:
#   pi_heating_demand (0x0008),
#   min_heat_setpoint_limit (0x0015)
#   max_heat_setpoint_limit (0x0016)
#   setpoint_change_source (0x0030)
# hardcoded:
#   abs_min_heat_setpoint_limit (0x0003)=5
#   abs_max_heat_setpoint_limit (0x0004)=35
#   start_of_week (0x0020)=Monday
#   number_of_weekly_transitions (0x0021)=42
#   number_of_daily_transitions (0x0022)=6

zcl_attr = {
    0xFFFD: ("cluster_revision", t.uint16_t, "r"),
}

# ZCL Commands Supported: SetWeeklySchedule (0x01), GetWeeklySchedule (0x02), ClearWeeklySchedule (0x03)

# 0x0204
danfoss_interface_attr = {
    0x4000: ("viewing_direction", t.enum8, "rpw"),
}

# Writing to mandatory ZCL attribute 0x0000 doesn't seem to do anything
# ZCL Attributes Supported: keypad_lockout (0x0001)

# 0x0b05
danfoss_diagnostic_attr = {
    0x4000: ("sw_error_code", t.bitmap16, "rp"),
    0x4001: ("wake_time_avg", t.uint32_t, "rp"),  # always 0?
    0x4002: ("wake_time_max_duration", t.uint32_t, "rp"),  # always 0?
    0x4003: ("wake_time_min_duration", t.uint32_t, "rp"),  # always 0?
    0x4004: ("sleep_postponed_count_avg", t.uint32_t, "rp"),  # always 0?
    0x4005: ("sleep_postponed_count_max", t.uint32_t, "rp"),  # always 0?
    0x4006: ("sleep_postponed_count_min", t.uint32_t, "rp"),  # always 0?
    0x4010: ("motor_step_counter", t.uint32_t, "rp"),
}

danfoss_thermostat_comm = {
    0x40: ZCLCommandDef(
        "setpoint_command",
        # Types
        # 0: Schedule (relatively slow)
        # 1: User Interaction (aggressive change)
        # 2: Preheat (invisible to user)
        {"type": t.enum8, "heating_setpoint": t.int16s},
        is_manufacturer_specific=True,
    ),
    # for synchronizing multiple TRVs preheating
    0x42: ZCLCommandDef(
        "preheat_command",
        # Force: 0 means force, other values for future needs
        {"force": t.enum8, "timestamp": t.uint32_t},
        is_manufacturer_specific=True,
    ),
}


def get_result_index(result: Tuple[list, list], attr_id: uint16_t) -> Union[int, None]:
    index = None
    for i in range(len(result[0])):
        if result[0][i].attrid == attr_id:
            index = i
            break
    return index


async def read_fakeattr(read_func: Callable, attributes, manufacturer,
                        attr_fake_id: uint16_t, attr_source_id: uint16_t):
    """
    First remove fake from attributes
    Then add source to attributes
    Request result
    Duplicate source in results and rename to fake
    Remove source from results
    """
    # store presence of requested attributes
    source_requested = attr_source_id in attributes
    fake_requested = attr_fake_id in attributes

    if fake_requested:
        # fake should not be present in attributes
        attributes.remove(attr_fake_id)
        if not source_requested:
            # if fake is requested, source should be requested
            attributes.append(attr_source_id)

    # Get result
    result = await read_func(attributes, manufacturer=manufacturer)

    # if fake is requested, use source to return that
    if fake_requested:
        index = get_result_index(result, attr_source_id)

        # if source is returned, copy source and change into fake and remove source from result if not requested
        if index is not None:
            attr_fake = result[0][index]
            attr_fake.attrid = attr_fake_id

            result[0].append(attr_fake)

            # remove source if not requested
            if not source_requested:
                result[0].pop(index)


class DanfossTRVCluster(CustomCluster):
    """Danfoss custom TRV cluster."""

    cluster_id = 0xFC03
    ep_attribute = "danfoss_trv_cluster"

    attributes = danfoss_thermostat_attr

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes to Thermostat cluster."""
        return await self.endpoint.thermostat.write_attributes(
            attributes, manufacturer=manufacturer
        )

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Read attributes from Thermostat cluster"""

        return await self.endpoint.thermostat.read_attributes_raw(
            attributes,
            manufacturer=manufacturer)


class DanfossTRVInterfaceCluster(CustomCluster):
    """Danfoss custom interface cluster."""

    cluster_id = 0xFC04
    ep_attribute = "danfoss_trv_interface_cluster"

    attributes = danfoss_interface_attr

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes to User Interface cluster."""
        return await self.endpoint.thermostat_ui.write_attributes(
            attributes, manufacturer=manufacturer
        )

    def read_attributes_raw(self, attributes, manufacturer=None):
        """Read in attributes from User Interface Cluster."""
        return self.endpoint.thermostat_ui.read_attributes_raw(
            attributes, manufacturer=manufacturer
        )


class DanfossTRVDiagnosticCluster(CustomCluster):
    """Danfoss custom diagnostic cluster."""

    cluster_id = 0xFC05
    ep_attribute = "danfoss_trv_diagnostic_cluster"

    attributes = danfoss_diagnostic_attr

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes to Diagnostic cluster."""
        return await self.endpoint.diagnostic.write_attributes(
            attributes, manufacturer=manufacturer
        )

    def read_attributes_raw(self, attributes, manufacturer=None):
        """Read in attributes from Diagnostic Cluster."""
        return self.endpoint.diagnostic.read_attributes_raw(
            attributes, manufacturer=manufacturer
        )


class DanfossThermostatCluster(CustomCluster, Thermostat):
    """Danfoss cluster for ZCL attributes and forwarding proprietary attributes."""

    server_commands = Thermostat.server_commands.copy()
    server_commands.update(danfoss_thermostat_comm)

    attributes = Thermostat.attributes.copy()
    attributes.update({**danfoss_thermostat_attr, **zcl_attr})

    async def write_attributes(self, attributes, manufacturer=None):
        """
        There are 2 types of setpoint changes:
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
            fast_setpoint_change = attributes[
                OCCUPIED_HEATING_SETPOINT_NAME
            ]

        # if: system_mode = off
        if attributes.get(SYSTEM_MODE_NAME) == SYSTEM_MODE_THERM_OFF_VAL:
            # Thermostatic Radiator Valves from Danfoss cannot be turned off to prevent damage during frost
            # just turn setpoint down to minimum temperature using fast_setpoint_change
            fast_setpoint_change = self._attr_cache[
                MIN_HEAT_SETPOINT_LIMIT_THERM_ID
            ]

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

    def _update_attribute(self, attrid, value):
        """Update attributes of TRV cluster."""
        super()._update_attribute(attrid, value)

        if attrid in danfoss_thermostat_attr:
            self.endpoint.danfoss_trv_cluster.update_attribute(attrid, value)


class DanfossUserInterfaceCluster(CustomCluster, UserInterface):
    """Danfoss cluster for ZCL attributes and forwarding proprietary attributes."""

    attributes = UserInterface.attributes.copy()
    attributes.update({**danfoss_interface_attr, **zcl_attr})

    def _update_attribute(self, attrid, value):
        """Update attributes of TRV interface cluster."""
        super()._update_attribute(attrid, value)

        if attrid in danfoss_interface_attr:
            self.endpoint.danfoss_trv_interface_cluster.update_attribute(attrid, value)


class DanfossDiagnosticCluster(CustomCluster, Diagnostic):
    """Danfoss cluster for ZCL attributes and forwarding proprietary attributes."""

    attributes = Diagnostic.attributes.copy()
    attributes.update({**danfoss_diagnostic_attr, **zcl_attr})

    def _update_attribute(self, attrid, value):
        """Update attributes or TRV diagnostic cluster."""
        super()._update_attribute(attrid, value)

        if attrid in danfoss_diagnostic_attr:
            self.endpoint.danfoss_trv_diagnostic_cluster.update_attribute(attrid, value)


class DanfossThermostat(CustomDevice):
    """DanfossThermostat custom device."""

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
                    Time,
                    PollControl,
                    DanfossThermostatCluster,
                    DanfossUserInterfaceCluster,
                    DanfossDiagnosticCluster,
                    DanfossTRVCluster,
                    DanfossTRVInterfaceCluster,
                    DanfossTRVDiagnosticCluster,
                ],
                OUTPUT_CLUSTERS: [Basic, Ota],
            }
        }
    }
