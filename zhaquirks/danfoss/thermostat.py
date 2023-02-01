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
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.danfoss import DANFOSS, HIVE, POPP

MANUFACTURER = 0x1246

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
}
# ZCL Attributes Supported: pi_heating_demand (0x0008)

# reading mandatory ZCL attribute 0xFFFD results in UNSUPPORTED_ATTRIBUTE
# ZCL Commands Supported: SetWeeklySchedule (0x01), GetWeeklySchedule (0x02), ClearWeeklySchedule (0x03)

# Danfos says they support the following, but Popp eT093WRO responds with UNSUPPORTED_ATTRIBUTE
#    0x0003, 0x0004, 0x0015, 0x0016, 0x0025, 0x0030, 0x0020, 0x0021, 0x0022

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


async def read_attributes(dest, source, dictionary):
    """Automatically reads attributes from source cluster and stores them in the dest cluster."""
    response = {}
    step = 14  # The device doesn't respond to more than 14 per request it seems

    # read from source
    for a in range(0, len(dictionary) + step, step):
        subset = list(dictionary.keys())[a : a + step]
        if subset:
            response.update(
                (await source.read_attributes(subset, manufacturer=MANUFACTURER))[0]
            )

    # store all of them in dest
    for attrid, value in response.items():
        dest.update_attribute(attrid, value)


class DanfossTRVCluster(CustomCluster, ManufacturerSpecificCluster):
    """Danfoss custom TRV cluster."""

    cluster_id = 0xFC03
    ep_attribute = "danfoss_trv_cluster"

    attributes = ManufacturerSpecificCluster.attributes.copy()
    attributes.update(danfoss_thermostat_attr)

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes to thermostat cluster."""
        return await self.endpoint.thermostat.write_attributes(attributes, manufacturer)

    async def bind(self):
        """Read attributes before ZHA binds, this makes sure the entity is created."""
        await read_attributes(self, self.endpoint.thermostat, danfoss_thermostat_attr)

        return await super().bind()


class DanfossTRVInterfaceCluster(CustomCluster, ManufacturerSpecificCluster):
    """Danfoss custom interface cluster."""

    cluster_id = 0xFC04
    ep_attribute = "danfoss_trv_interface_cluster"

    attributes = ManufacturerSpecificCluster.attributes.copy()
    attributes.update(danfoss_interface_attr)

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes to thermostat user interface cluster."""

        return await self.endpoint.thermostat_ui.write_attributes(
            attributes, manufacturer
        )

    async def bind(self):
        """Read attributes before ZHA binds, this makes sure the entity is created."""
        await read_attributes(self, self.endpoint.thermostat_ui, danfoss_interface_attr)

        return await super().bind()


class DanfossTRVDiagnosticCluster(CustomCluster, ManufacturerSpecificCluster):
    """Danfoss custom diagnostic cluster."""

    cluster_id = 0xFC05
    ep_attribute = "danfoss_trv_diagnostic_cluster"

    attributes = ManufacturerSpecificCluster.attributes.copy()
    attributes.update(danfoss_diagnostic_attr)

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes to diagnostic cluster."""
        return await self.endpoint.diagnostic.write_attributes(attributes, manufacturer)

    async def bind(self):
        """Read attributes before ZHA binds, this makes sure the entity is created."""
        await read_attributes(self, self.endpoint.diagnostic, danfoss_diagnostic_attr)

        return await super().bind()


class DanfossThermostatCluster(CustomCluster, Thermostat):
    """Danfoss cluster for ZCL attributes and forwarding proprietary the attributes."""

    server_commands = Thermostat.server_commands.copy()
    server_commands = {
        0x40: foundation.ZCLCommandDef(
            "setpoint_command",
            # Types
            # 0: Schedule (relatively slow)
            # 1: User Interaction (aggressive change)
            # 2: Preheat (invisible to user)
            {"type": t.enum8, "heating_setpoint": t.int16s},
            is_manufacturer_specific=True,
        ),
        # for synchronizing multiple TRVs preheating
        0x42: foundation.ZCLCommandDef(
            "preheat_command",
            # Force: 0 means force, other values for future needs
            {"force": t.enum8, "timestamp": t.uint32_t},
            is_manufacturer_specific=True,
        ),
    }

    attributes = Thermostat.attributes.copy()
    attributes.update(danfoss_thermostat_attr)

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
        elif "system_mode" in attributes and attributes["system_mode"] == 0:
            # Thermostatic Radiator Valves often cannot be turned off to prevent damage during frost
            # just turn setpoint down to minimum of 5 degrees celsius
            await self.setpoint_command(0x01, 500, manufacturer=manufacturer)

        return write_res

    def _update_attribute(self, attrid, value):
        """Update attributes of TRV cluster."""
        if attrid in {a for (a, *_) in danfoss_thermostat_attr.values()}:
            self.endpoint.danfoss_trv_cluster.update_attribute(attrid, value)

        # update local either way
        super()._update_attribute(attrid, value)


class DanfossUserInterfaceCluster(CustomCluster, UserInterface):
    """Danfoss cluster for ZCL attributes and forwarding proprietary the attributes."""

    attributes = UserInterface.attributes.copy()
    attributes.update(danfoss_interface_attr)

    def _update_attribute(self, attrid, value):
        """Update attributes of TRV interface cluster."""
        if attrid in {a for (a, *_) in danfoss_interface_attr.values()}:
            self.endpoint.danfoss_trv_interface_cluster.update_attribute(attrid, value)

        # update local either way
        super()._update_attribute(attrid, value)


class DanfossDiagnosticCluster(CustomCluster, Diagnostic):
    """Danfoss cluster for ZCL attributes and forwarding proprietary the attributes."""

    attributes = Diagnostic.attributes.copy()
    attributes.update(danfoss_diagnostic_attr)

    def _update_attribute(self, attrid, value):
        """Update attributes or TRV diagnostic cluster."""
        if attrid in {a for (a, *_) in danfoss_diagnostic_attr.values()}:
            self.endpoint.danfoss_trv_diagnostic_cluster.update_attribute(attrid, value)

        # update local either way
        super()._update_attribute(attrid, value)


class DanfossThermostat(CustomDevice):
    """DanfossThermostat custom device."""

    signature = {
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
