"""Map from manufacturer to standard clusters for electric heating thermostats."""
import logging

from zigpy.profiles import zha
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

# info from https://github.com/zigpy/zha-device-handlers/pull/538#issuecomment-723334124
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L239
# and https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/common.js#L113
MOESBHT_TARGET_TEMP_ATTR = 0x0210  # [0,0,0,21] target room temp (degree)
MOESBHT_TEMPERATURE_ATTR = 0x0218  # [0,0,0,200] current room temp (decidegree)
MOESBHT_SCHEDULE_MODE_ATTR = 0x0403  # [1] false [0] true   /!\ inverted
MOESBHT_MANUAL_MODE_ATTR = 0x0402  # [1] false [0] true /!\ inverted
MOESBHT_ENABLED_ATTR = 0x0101  # [0] off [1] on
MOESBHT_RUNNING_MODE_ATTR = 0x0424  # [1] idle [0] heating /!\ inverted
MOESBHT_CHILD_LOCK_ATTR = 0x0128  # [0] unlocked [1] child-locked

_LOGGER = logging.getLogger(__name__)


class MoesBHTManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some electric heating thermostats."""

    manufacturer_attributes = {
        MOESBHT_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t),
        MOESBHT_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        MOESBHT_SCHEDULE_MODE_ATTR: ("schedule_mode", t.uint8_t),
        MOESBHT_MANUAL_MODE_ATTR: ("manual_mode", t.uint8_t),
        MOESBHT_ENABLED_ATTR: ("enabled", t.uint8_t),
        MOESBHT_RUNNING_MODE_ATTR: ("running_mode", t.uint8_t),
        MOESBHT_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MOESBHT_TARGET_TEMP_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "occupied_heating_setpoint",
                value * 100,  # degree to centidegree
            )
        elif attrid == MOESBHT_TEMPERATURE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "local_temp",
                value * 10,  # decidegree to centidegree
            )
        elif attrid == MOESBHT_SCHEDULE_MODE_ATTR:
            if value == 0:  # value is inverted
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "scheduled"
                )
        elif attrid == MOESBHT_MANUAL_MODE_ATTR:
            if value == 0:  # value is inverted
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "manual"
                )
        elif attrid == MOESBHT_ENABLED_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("enabled_change", value)
        elif attrid == MOESBHT_RUNNING_MODE_ATTR:
            # value is inverted
            self.endpoint.device.thermostat_bus.listener_event(
                "state_change", 1 - value
            )
        elif attrid == MOESBHT_CHILD_LOCK_ATTR:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)


class MoesBHTThermostat(TuyaThermostatCluster):
    """Thermostat cluster for some electric heating controllers."""

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to degree
            return {MOESBHT_TARGET_TEMP_ATTR: round(value / 100)}
        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {MOESBHT_ENABLED_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {MOESBHT_ENABLED_ATTR: 1}
            self.error("Unsupported value for SystemMode")
        elif attribute == "programing_oper_mode":
            # values are inverted
            if value == self.ProgrammingOperationMode.Simple:
                return {MOESBHT_MANUAL_MODE_ATTR: 0, MOESBHT_SCHEDULE_MODE_ATTR: 1}
            if value == self.ProgrammingOperationMode.Schedule_programming_mode:
                return {MOESBHT_MANUAL_MODE_ATTR: 1, MOESBHT_SCHEDULE_MODE_ATTR: 0}
            self.error("Unsupported value for ProgrammingOperationMode")

        return super().map_attribute(attribute, value)

    def program_change(self, mode):
        """Programming mode change."""
        if mode == "manual":
            value = self.ProgrammingOperationMode.Simple
        else:
            value = self.ProgrammingOperationMode.Schedule_programming_mode

        self._update_attribute(self.attridx["programing_oper_mode"], value)

    def enabled_change(self, value):
        """System mode change."""
        if value == 0:
            mode = self.SystemMode.Off
        else:
            mode = self.SystemMode.Heat
        self._update_attribute(self.attridx["system_mode"], mode)


class MoesBHTUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = MOESBHT_CHILD_LOCK_ATTR


class MoesBHT(TuyaThermostat):
    """Moes BHT-002GCLZB Thermostatic radiator valve."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184],
        #  output_clusters=[10, 25]
        MODELS_INFO: [("_TZE200_aoclfnxz", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesBHTManufCluster,
                    MoesBHTThermostat,
                    MoesBHTUserInterface,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
