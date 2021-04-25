"""Module to handle quirks of the  Fanfoss thermostat.

manufacturer specific attributes to control displaying and specific configuration.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
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
from zhaquirks.danfoss import DANFOSS


class DanfossThermostatCluster(CustomCluster, Thermostat):
    """Danfoss custom cluster."""

    manufacturer_attributes = {
        0x4000: ("etrv_open_windows_detection", t.enum8),
        0x4003: ("external_open_windows_detected", t.Bool),
        0x4010: ("exercise_day_of_week", t.enum8),
        0x4011: ("exercise_trigger_time", t.uint16_t),
        0x4012: ("mounting_mode_active", t.Bool),
        0x4013: ("mounting_mode_control", t.Bool),
        0x4014: ("orientation", t.Bool),
        0x4015: ("external_measured_room_sensor", t.int16s),
        0x4016: ("radiator_overed", t.Bool),
        0x4020: ("control_algorithm_scale_factor", t.uint8_t),
        0x4030: ("heat_available", t.Bool),
        0x4031: ("heat_supply_request", t.Bool),
        0x4032: ("load_balancing_enable", t.Bool),
        0x404A: ("load_estimate_radiator", t.uint16_t),
        0x404B: ("regulation_setPoint_offset", t.int8s),
        0x404C: ("adaptation_run_control", t.enum8),
        0x404D: ("adaptation_run_status", t.bitmap8),
        0x404E: ("adaptation_run_settings", t.bitmap8),
        0x404F: ("preheat_status", t.Bool),
        0x4050: ("preheat_time", t.uint32_t),
        0x4051: ("window_open_feature_on_off", t.Bool),
        0xFFFD: ("cluster_revision", t.uint16_t),
    }


class DanfossUserInterfaceCluster(CustomCluster, UserInterface):
    """Danfoss custom cluster."""

    manufacturer_attributes = {
        0x4000: ("viewing_direction", t.enum8),
        0xFFFD: ("cluster_revision", t.uint16_t),
    }


class DanfossDiagnosticCluster(CustomCluster, Diagnostic):
    """Danfoss custom cluster."""

    manufacturer_attributes = {
        0x4000: ("sw_error_code", t.bitmap16),
        0x4001: ("wake_time_avg", t.uint32_t),
        0x4002: ("wake_time max duration", t.uint32_t),
        0x4003: ("wake_time min duration", t.uint32_t),
        0x4004: ("sleep_Postponed_count_avg", t.uint32_t),
        0x4005: ("sleep_Postponed_count_max", t.uint32_t),
        0x4006: ("sleep_Postponed_count_min", t.uint32_t),
        0x4010: ("motor_step_counter", t.uint32_t),
        0xFFFD: ("cluster_revision", t.uint16_t),
    }


class DanfossThermostat(CustomDevice):
    """DanfossThermostat custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 1, 3, 10,32, 513, 516, 1026, 2821]
        # output_clusters=[0, 25]>
        MODELS_INFO: [(DANFOSS, "eTRV0100")],
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
