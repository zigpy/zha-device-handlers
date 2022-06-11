"""Map from manufacturer to standard clusters for thermostatic valves."""
import logging

import zigpy.profiles.zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufClusterAttributes,
    TuyaThermostat,
    TuyaThermostatCluster,
    TuyaUserInterfaceCluster,
)

# from https://github.com/Koenkk/zigbee-herdsman-converters/pull/1694/
HAOZEE_SCHEDULE_WORKDAYS_AM_ATTR = (
    0x0077  # schedule for workdays [8, 0, 20, 8, 1, 15, 11, 30, 15]
)
HAOZEE_SCHEDULE_WORKDAYS_PM_ATTR = (
    0x0078  # schedule for workdays [13, 30, 15, 17, 0, 15, 150, 0, 15]
)
HAOZEE_SCHEDULE_WEEKEND_AM_ATTR = (
    0x0079  # schedule for weekend [6, 0, 20, 8, 0, 15, 11, 30, 15]
)
HAOZEE_SCHEDULE_WEEKEND_PM_ATTR = (
    0x007A  # schedule for weekend [13, 30, 15, 17, 0, 15, 22, 0, 15]
)

HAOZEE_HEATING_ENABLED_ATTR = 0x0166  # [0] idle [1] heating
HAOZEE_MAX_TEMP_PROTECTION_ENABLED_ATTR = (
    0x016A  # minimal temp protection [0] disabled [1] enabled
)
HAOZEE_MIN_TEMP_PROTECTION_ENABLED_ATTR = (
    0x016B  # maximal temp protection [0] disabled [1] enabled
)
HAOZEE_ENABLED_ATTR = 0x017D  # device status [0] disabled [1] enabled
HAOZEE_CHILD_LOCK_ATTR = 0x0181  # [0] unlocked [1] child-locked
HAOZEE_EXT_TEMP_ATTR = 0x0267  # external NTC sensor temp (decidegree)
HAOZEE_AWAY_DAYS_ATTR = 0x0268  # away mode duration (days)
HAOZEE_AWAY_TEMP_ATTR = 0x0269  # away mode temperature (decidegree)
HAOZEE_TEMP_CALIBRATION_ATTR = 0x026D  # temperature calibration (decidegree)
HAOZEE_TEMP_HYSTERESIS_ATTR = 0x026E  # temperature hysteresis (decidegree)
HAOZEE_TEMP_PROTECT_HYSTERESIS_ATTR = (
    0x026F  # temperature hysteresis for protection (decidegree)
)
HAOZEE_MAX_PROTECT_TEMP_ATTR = (
    0x0270  # maximal temp for protection trigger (decidegree)
)
HAOZEE_MIN_PROTECT_TEMP_ATTR = (
    0x0271  # minimal temp for protection trigger (decidegree)
)
HAOZEE_MAX_TEMP_LIMIT_ATTR = 0x0272  # maximum limit of temperature setting (decidegree)
HAOZEE_MIN_TEMP_LIMIT_ATTR = 0x0273  # minimum limit of temperature setting (decidegree)
HAOZEE_TARGET_TEMP_ATTR = 0x027E  # target temperature (decidegree)
HAOZEE_CURRENT_ROOM_TEMP_ATTR = (
    0x027F  # temperature reported by MCU. Depends on sensor type. (decidegree)
)
HAOZEE_SENSOR_TYPE_ATTR = 0x0474  # sensor type [0] internal [1] external [2] both
HAOZEE_POWERON_BEHAVIOR_ATTR = 0x0475  # poweron behavior [0] restore [1] off [2] on
HAOZEE_WEEKFORMAT = 0x0476  # [0] 5+2 [1] 6+1 [2] 7 (days)

HAOZEE_CURRENT_MODE_ATTR = 0x0480  # [0] manual [1] auto [2] away
HAOZEE_FAULT_ATTR = 0x0582  # Known fault codes: [4] E2 external sensor error

# Unknown DP - descaling on/off, window detection, window detection settings

_LOGGER = logging.getLogger(__name__)


class HY08WEManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some thermostatic valves."""

    # Important! This device uses offset from 2000 year for UTC time and offset from 1970 for local time
    set_time_offset = 2000
    set_time_local_offset = 1970

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            HAOZEE_HEATING_ENABLED_ATTR: ("heating_enabled", t.uint8_t),
            HAOZEE_MAX_TEMP_PROTECTION_ENABLED_ATTR: (
                "max_temp_protection_enabled",
                t.uint8_t,
            ),
            HAOZEE_MIN_TEMP_PROTECTION_ENABLED_ATTR: (
                "min_temp_protection_enabled",
                t.uint8_t,
            ),
            HAOZEE_ENABLED_ATTR: ("enabled", t.uint8_t),
            HAOZEE_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
            HAOZEE_EXT_TEMP_ATTR: ("external_temperature", t.uint32_t),
            HAOZEE_AWAY_DAYS_ATTR: ("away_duration_days", t.uint32_t),
            HAOZEE_AWAY_TEMP_ATTR: ("away_mode_temperature", t.uint32_t),
            HAOZEE_TEMP_CALIBRATION_ATTR: ("temperature_calibration", t.int32s),
            HAOZEE_TEMP_HYSTERESIS_ATTR: ("hysterisis_temperature", t.uint32_t),
            HAOZEE_TEMP_PROTECT_HYSTERESIS_ATTR: (
                "hysterisis_protection_temperature",
                t.uint32_t,
            ),
            HAOZEE_MAX_PROTECT_TEMP_ATTR: ("max_protection_temperature", t.uint32_t),
            HAOZEE_MIN_PROTECT_TEMP_ATTR: ("min_protection_temperature", t.uint32_t),
            HAOZEE_MAX_TEMP_LIMIT_ATTR: ("max_temperature", t.uint32_t),
            HAOZEE_MIN_TEMP_LIMIT_ATTR: ("min_temperature", t.uint32_t),
            HAOZEE_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t),
            HAOZEE_CURRENT_ROOM_TEMP_ATTR: ("internal_temperature", t.uint32_t),
            HAOZEE_SENSOR_TYPE_ATTR: ("sensor_settings", t.uint8_t),
            HAOZEE_POWERON_BEHAVIOR_ATTR: ("poweron_behavior", t.uint8_t),
            HAOZEE_WEEKFORMAT: ("week_format", t.uint8_t),
            HAOZEE_CURRENT_MODE_ATTR: ("mode", t.uint8_t),
            HAOZEE_FAULT_ATTR: ("fault", t.uint8_t),
        }
    )

    DIRECT_MAPPED_ATTRS = {
        HAOZEE_CURRENT_ROOM_TEMP_ATTR: ("local_temp", lambda value: value * 10),
        HAOZEE_TARGET_TEMP_ATTR: (
            "occupied_heating_setpoint",
            lambda value: value * 10,
        ),
        HAOZEE_AWAY_TEMP_ATTR: (
            "unoccupied_heating_setpoint",
            lambda value: value * 100,
        ),
        HAOZEE_TEMP_CALIBRATION_ATTR: (
            "local_temperature_calibration",
            lambda value: value * 10,
        ),
        HAOZEE_MIN_TEMP_LIMIT_ATTR: (
            "min_heat_setpoint_limit",
            lambda value: value * 100,
        ),
        HAOZEE_MAX_TEMP_LIMIT_ATTR: (
            "max_heat_setpoint_limit",
            lambda value: value * 100,
        ),
        HAOZEE_AWAY_DAYS_ATTR: ("unoccupied_duration_days", None),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid in self.DIRECT_MAPPED_ATTRS:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                self.DIRECT_MAPPED_ATTRS[attrid][0],
                value
                if self.DIRECT_MAPPED_ATTRS[attrid][1] is None
                else self.DIRECT_MAPPED_ATTRS[attrid][1](
                    value
                ),  # decidegree to centidegree
            )
        elif attrid == HAOZEE_ENABLED_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("enabled_change", value)
        elif attrid == HAOZEE_HEATING_ENABLED_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("state_change", value)
        elif attrid == HAOZEE_CURRENT_MODE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
        elif attrid == HAOZEE_CHILD_LOCK_ATTR:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)


class HY08WEThermostat(TuyaThermostatCluster):
    """Thermostat cluster for some thermostatic valves."""

    DIRECT_MAPPING_ATTRS = {
        "occupied_heating_setpoint": (
            HAOZEE_TARGET_TEMP_ATTR,
            lambda value: round(value / 10),
        ),
        "unoccupied_heating_setpoint": (
            HAOZEE_AWAY_TEMP_ATTR,
            lambda value: round(value / 100),
        ),
        "min_heat_setpoint_limit": (
            HAOZEE_MIN_TEMP_LIMIT_ATTR,
            lambda value: round(value / 100),
        ),
        "max_heat_setpoint_limit": (
            HAOZEE_MAX_TEMP_LIMIT_ATTR,
            lambda value: round(value / 100),
        ),
        "local_temperature_calibration": (
            HAOZEE_TEMP_CALIBRATION_ATTR,
            lambda value: round(value / 10),
        ),
    }

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute in self.DIRECT_MAPPING_ATTRS:
            return {
                self.DIRECT_MAPPING_ATTRS[attribute][0]: value
                if self.DIRECT_MAPPING_ATTRS[attribute][1] is None
                else self.DIRECT_MAPPING_ATTRS[attribute][1](value)
            }

        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {HAOZEE_ENABLED_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {HAOZEE_ENABLED_ATTR: 1}
            self.error("Unsupported value for SystemMode")

        if attribute == "programing_oper_mode":
            if value == self.ProgrammingOperationMode.Simple:
                return {HAOZEE_CURRENT_MODE_ATTR: 0}
            if value == self.ProgrammingOperationMode.Schedule_programming_mode:
                return {HAOZEE_CURRENT_MODE_ATTR: 1}
            if value == self.ProgrammingOperationMode.Economy_mode:
                return {HAOZEE_CURRENT_MODE_ATTR: 2}
            self.error("Unsupported value for ProgrammingOperationMode")

    def mode_change(self, value):
        """System Mode change."""
        occupancy = self.Occupancy.Occupied
        if value == 0:
            prog_mode = self.ProgrammingOperationMode.Simple
        elif value == 1:
            prog_mode = self.ProgrammingOperationMode.Schedule_programming_mode
        elif value == 2:
            prog_mode = self.ProgrammingOperationMode.Simple
            occupancy = self.Occupancy.Unoccupied
        self._update_attribute(self.attridx["programing_oper_mode"], prog_mode)
        self._update_attribute(self.attridx["occupancy"], occupancy)

    def enabled_change(self, value):
        """System mode change."""
        if value == 0:
            mode = self.SystemMode.Off
        else:
            mode = self.SystemMode.Heat
        self._update_attribute(self.attridx["system_mode"], mode)


class HY08WEUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = HAOZEE_CHILD_LOCK_ATTR


class HY08WE(TuyaThermostat):
    """Haozee HY08WE Thermostatic radiator valve."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184],
        #  output_clusters=[25, 10]
        MODELS_INFO: [("_TZE200_znzs7yaw", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    HY08WEManufCluster,
                    HY08WEThermostat,
                    HY08WEUserInterface,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        }
    }
