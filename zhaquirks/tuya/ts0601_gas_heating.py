"""HC-T020-ZIGBEE Gas Heater Thermostat. Heavily based on HCT020 (ts0601_electric_heating.py)"""
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

HCT020_TARGET_TEMP_ATTR = 0x0210  # [0,0,0,21] target room temp (degree)
HCT020_TEMPERATURE_ATTR = 0x0218  # [0,0,0,20] current room temp (degree)
HCT020_MANUAL_MODE_ATTR = 0x0402  # [1] false [0] true /!\ inverted
HCT020_ENABLED_ATTR = 0x0101  # [0] off [1] on
HCT020_RUNNING_MODE_ATTR = 0x0403  # [1] idle [0] heating /!\ inverted
HCT020_CHILD_LOCK_ATTR = 0x0128  # [0] unlocked [1] child-locked
"""
TODO(admantivm) Interpret and map these other attributes reported by the device

attribute - sample data (wrapped)

0x001e - [6, 0, 0, 20, 8, 0, 0, 15, 11, 30, 0, 15, 13, 30, 0, 15, 17, 0, 0, 22,
          22, 0, 0, 15, 6, 0, 0, 20, 22, 0, 0, 1 5] - schedule?
0x0104 - [0]
0x0213 - [0, 0, 0, 35]
0x021a - [0, 0, 0, 5]
0x021b - [255, 255, 255, 253]
0x022a - [0, 0, 0, 0]
0x0417 - [0]
0x0429 - [0]
0x042b - [2]
0x052d - [2]
"""


_LOGGER = logging.getLogger(__name__)


class HCT020ManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of HC-T020 gas heating thermostats."""

    attributes = {
        HCT020_TARGET_TEMP_ATTR: ("target_temperature", t.uint32_t, True),
        HCT020_TEMPERATURE_ATTR: ("temperature", t.uint32_t, True),
        HCT020_MANUAL_MODE_ATTR: ("manual_mode", t.uint8_t, True),
        HCT020_ENABLED_ATTR: ("enabled", t.uint8_t, True),
        HCT020_RUNNING_MODE_ATTR: ("running_mode", t.uint8_t, True),
        HCT020_CHILD_LOCK_ATTR: ("child_lock", t.uint8_t, True),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == HCT020_TARGET_TEMP_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "occupied_heating_setpoint",
                value * 100,  # degree to centidegree
            )
        elif attrid == HCT020_TEMPERATURE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "local_temperature",
                value * 100,  # degree to centidegree
            )
        elif attrid == HCT020_MANUAL_MODE_ATTR:
            if value == 0:  # value is inverted
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "manual"
                )
        elif attrid == HCT020_ENABLED_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("enabled_change", value)
        elif attrid == HCT020_RUNNING_MODE_ATTR:
            # value is inverted
            self.endpoint.device.thermostat_bus.listener_event(
                "state_change", 1 - value
            )
        elif attrid == HCT020_CHILD_LOCK_ATTR:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)


class HCT020Thermostat(TuyaThermostatCluster):
    """Thermostat cluster for some electric heating controllers."""

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to degree
            return {HCT020_TARGET_TEMP_ATTR: round(value / 100)}
        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {HCT020_ENABLED_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {HCT020_ENABLED_ATTR: 1}
            self.error("Unsupported value for SystemMode")
        elif attribute == "programing_oper_mode":
            # values are inverted
            if value == self.ProgrammingOperationMode.Simple:
                return {HCT020_MANUAL_MODE_ATTR: 0}
            if value == self.ProgrammingOperationMode.Schedule_programming_mode:
                return {HCT020_MANUAL_MODE_ATTR: 1}
            self.error("Unsupported value for ProgrammingOperationMode")

        return super().map_attribute(attribute, value)

    def program_change(self, mode):
        """Programming mode change."""
        if mode == "manual":
            value = self.ProgrammingOperationMode.Simple
        else:
            value = self.ProgrammingOperationMode.Schedule_programming_mode

        self._update_attribute(
            self.attributes_by_name["programing_oper_mode"].id, value
        )

    def enabled_change(self, value):
        """System mode change."""
        if value == 0:
            mode = self.SystemMode.Off
        else:
            mode = self.SystemMode.Heat
        self._update_attribute(self.attributes_by_name["system_mode"].id, mode)


class HCT020UserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = HCT020_CHILD_LOCK_ATTR


class HCT020(TuyaThermostat):
    """Tuya thermostat for Tuya HC-T020-ZIGBEE gas heating thermostat."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184],
        #  output_clusters=[10, 25]
        MODELS_INFO: [
            ("_TZE200_ztvwu4nk", "TS0601"),
        ],
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
                    HCT020ManufCluster,
                    HCT020Thermostat,
                    HCT020UserInterface,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
