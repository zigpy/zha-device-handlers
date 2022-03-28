"""Module to handle quirks of the Danfoss thermostat.

manufacturer specific attributes to control displaying and specific configuration.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
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

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.danfoss import D5X84YU, DANFOSS


class DanfossThermostatCluster(CustomCluster, Thermostat):
    """Danfoss custom cluster."""

    server_commands = Thermostat.server_commands.copy()
    server_commands[0x40] = foundation.ZCLCommandDef(
        "setpoint_command",
        {"param1": t.enum8, "param2": t.int16s},
        is_manufacturer_specific=True,
    )

    attributes = Thermostat.attributes.copy()
    attributes.update(
        {
            0x4000: ("etrv_open_windows_detection", t.enum8, True),
            0x4003: ("external_open_windows_detected", t.Bool, True),
            0x4010: ("exercise_day_of_week", t.enum8, True),
            0x4011: ("exercise_trigger_time", t.uint16_t, True),
            0x4012: ("mounting_mode_active", t.Bool, True),
            0x4013: ("mounting_mode_control", t.Bool, True),
            0x4014: ("orientation", t.Bool, True),
            0x4015: ("external_measured_room_sensor", t.int16s, True),
            0x4016: ("radiator_covered", t.Bool, True),
            0x4020: ("control_algorithm_scale_factor", t.uint8_t, True),
            0x4030: ("heat_available", t.Bool, True),
            0x4031: ("heat_supply_request", t.Bool, True),
            0x4032: ("load_balancing_enable", t.Bool, True),
            0x4040: ("load_radiator_room_mean", t.uint16_t, True),
            0x404A: ("load_estimate_radiator", t.uint16_t, True),
            0x404B: ("regulation_setPoint_offset", t.int8s, True),
            0x404C: ("adaptation_run_control", t.enum8, True),
            0x404D: ("adaptation_run_status", t.bitmap8, True),
            0x404E: ("adaptation_run_settings", t.bitmap8, True),
            0x404F: ("preheat_status", t.Bool, True),
            0x4050: ("preheat_time", t.uint32_t, True),
            0x4051: ("window_open_feature_on_off", t.Bool, True),
            0xFFFD: ("cluster_revision", t.uint16_t, True),
        }
    )

    async def write_attributes(self, attributes, manufacturer=None):
        """Send SETPOINT_COMMAND after setpoint change."""

        write_res = await super().write_attributes(
            attributes, manufacturer=manufacturer
        )

        if "occupied_heating_setpoint" in attributes:
            self.debug(
                "sending setpoint command: %s", attributes["occupied_heating_setpoint"]
            )
            await self.setpoint_command(
                0x01, attributes["occupied_heating_setpoint"], manufacturer=manufacturer
            )

        return write_res


class DanfossUserInterfaceCluster(CustomCluster, UserInterface):
    """Danfoss custom cluster."""

    attributes = UserInterface.attributes.copy()
    attributes.update(
        {
            0x4000: ("viewing_direction", t.enum8, True),
        }
    )


class DanfossDiagnosticCluster(CustomCluster, Diagnostic):
    """Danfoss custom cluster."""

    attributes = Diagnostic.attributes.copy()
    attributes.update(
        {
            0x4000: ("sw_error_code", t.bitmap16, True),
            0x4001: ("wake_time_avg", t.uint32_t, True),
            0x4002: ("wake_time_max_duration", t.uint32_t, True),
            0x4003: ("wake_time_min_duration", t.uint32_t, True),
            0x4004: ("sleep_postponed_count_avg", t.uint32_t, True),
            0x4005: ("sleep_postponed_count_max", t.uint32_t, True),
            0x4006: ("sleep_postponed_count_min", t.uint32_t, True),
            0x4010: ("motor_step_counter", t.uint32_t, True),
        }
    )


class DanfossThermostat(CustomDevice):
    """DanfossThermostat custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 1, 3, 10,32, 513, 516, 1026, 2821]
        # output_clusters=[0, 25]>
        MODELS_INFO: [(DANFOSS, "eTRV0100"), (D5X84YU, "eT093WRO")],
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
                ],
                OUTPUT_CLUSTERS: [Basic, Ota],
            }
        }
    }
