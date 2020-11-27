"""Map from manufacturer to standard clusters for thermostatic valves."""
import logging

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Ota, Scenes, Time

from . import (
    TuyaManufClusterAttributes,
    TuyaPowerConfigurationCluster,
    TuyaThermostat,
    TuyaThermostatCluster,
    TuyaUserInterfaceCluster,
)
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

# info from https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/common.js#L113
# and https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L362
SITERWELL_CHILD_LOCK_ATTR = 0x0107  # [0] unlocked [1] child-locked
SITERWELL_WINDOW_DETECT_ATTR = 0x0112  # [0] inactive [1] active
SITERWELL_VALVE_DETECT_ATTR = 0x0114  # [0] do not report [1] report
SITERWELL_VALVE_STATE_ATTR = 0x026D  # [0,0,0,55] opening percentage
SITERWELL_TARGET_TEMP_ATTR = 0x0202  # [0,0,0,210] target room temp (decidegree)
SITERWELL_TEMPERATURE_ATTR = 0x0203  # [0,0,0,200] current room temp (decidegree)
SITERWELL_BATTERY_ATTR = 0x0215  # [0,0,0,98] battery charge
SITERWELL_MODE_ATTR = 0x0404  # [0] off [1] scheduled [2] manual

_LOGGER = logging.getLogger(__name__)


class SiterwellManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some thermostatic valves."""

    manufacturer_attributes = {
        SITERWELL_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t),
        SITERWELL_WINDOW_DETECT_ATTR: ("window_detection", t.uint8_t),
        SITERWELL_VALVE_DETECT_ATTR: ("valve_detect", t.uint8_t),
        SITERWELL_VALVE_STATE_ATTR: ("valve_state", t.uint32_t),
        SITERWELL_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t),
        SITERWELL_TEMPERATURE_ATTR: ("temperature", t.uint32_t),
        SITERWELL_BATTERY_ATTR: ("battery", t.uint32_t),
        SITERWELL_MODE_ATTR: ("mode", t.uint8_t),
    }

    TEMPERATURE_ATTRS = {
        SITERWELL_TEMPERATURE_ATTR: "local_temp",
        SITERWELL_TARGET_TEMP_ATTR: "occupied_heating_setpoint",
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid in self.TEMPERATURE_ATTRS:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                self.TEMPERATURE_ATTRS[attrid],
                value * 10,  # decidegree to centidegree
            )
        elif attrid == SITERWELL_MODE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("mode_change", value)
            self.endpoint.device.thermostat_bus.listener_event(
                "state_change", value > 0
            )
        elif attrid == SITERWELL_VALVE_STATE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("state_change", value)
        elif attrid == SITERWELL_CHILD_LOCK_ATTR:
            mode = 1 if value else 0
            self.endpoint.device.ui_bus.listener_event("child_lock_change", mode)
        elif attrid == SITERWELL_BATTERY_ATTR:
            self.endpoint.device.battery_bus.listener_event("battery_change", value)


class SiterwellThermostat(TuyaThermostatCluster):
    """Thermostat cluster for some thermostatic valves."""

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to decidegree
            return {SITERWELL_TARGET_TEMP_ATTR: round(value / 10)}
        if attribute in ("system_mode", "programing_oper_mode"):
            if attribute == "system_mode":
                system_mode = value
                oper_mode = self._attr_cache.get(
                    self.attridx["programing_oper_mode"],
                    self.ProgrammingOperationMode.Simple,
                )
            else:
                system_mode = self._attr_cache.get(
                    self.attridx["system_mode"], self.SystemMode.Heat
                )
                oper_mode = value
            if system_mode == self.SystemMode.Off:
                return {SITERWELL_MODE_ATTR: 0}
            if system_mode == self.SystemMode.Heat:
                if oper_mode == self.ProgrammingOperationMode.Schedule_programming_mode:
                    return {SITERWELL_MODE_ATTR: 1}
                if oper_mode == self.ProgrammingOperationMode.Simple:
                    return {SITERWELL_MODE_ATTR: 2}
                self.error("Unsupported value for ProgrammingOperationMode")
            else:
                self.error("Unsupported value for SystemMode")

    def mode_change(self, value):
        """System Mode change."""
        if value == 0:
            self._update_attribute(self.attridx["system_mode"], self.SystemMode.Off)
            return

        if value == 1:
            mode = self.ProgrammingOperationMode.Schedule_programming_mode
        else:
            mode = self.ProgrammingOperationMode.Simple

        self._update_attribute(self.attridx["system_mode"], self.SystemMode.Heat)
        self._update_attribute(self.attridx["programing_oper_mode"], mode)


class SiterwellUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = SITERWELL_CHILD_LOCK_ATTR


class SiterwellGS361(TuyaThermostat):
    """SiterwellGS361 Thermostatic radiator valve and clones."""

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_jeaxp72v", "eaxp72v"), ("_TYST11_kfvq6avy", "fvq6avy")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
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
                    Identify.cluster_id,
                    SiterwellManufCluster,
                    SiterwellThermostat,
                    SiterwellUserInterface,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }


class MoesHY368(TuyaThermostat):
    """MoesHY368 Thermostatic radiator valve."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [("_TZE200_ckud7u2l", "TS0601")],
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
                    SiterwellManufCluster,
                    SiterwellThermostat,
                    SiterwellUserInterface,
                    TuyaPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
