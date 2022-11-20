"""Saswell (Tuya whitelabel) 88teujp thermostat valve quirk."""

import logging

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Ota, Scenes, Time
from zigpy.zcl.clusters.hvac import Thermostat

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
    TuyaPowerConfigurationCluster,
    TuyaThermostat,
    TuyaThermostatCluster,
)

_LOGGER = logging.getLogger(__name__)

SASSWEL_HEATING_SETPOINT_ATTR = 0x0267
SASSWEL_STATE_ATTR = 0x0165
SASSWEL_LOCAL_TEMP_ATTR = 0x0266
SASSWEL_BATTERY_LOW_ATTR = 0x0569
SASSWEL_SCHEDULE_ENABLE_ATTR = 0x016C

CTRL_SEQ_OF_OPER_ATTR = 0x001B

MIN_HEAT_SETPOINT_ATTR = 0x0015
MAX_HEAT_SETPOINT_ATTR = 0x0016


class ManufacturerThermostatCluster(TuyaManufClusterAttributes):
    """Tuya manufacturer specific cluster."""

    class State(t.enum8):
        """State option."""

        Off = 0x00
        On = 0x01

    class BatteryState(t.enum8):
        """Battery state option."""

        Normal = 0x00
        Low = 0x01

    class ScheduleState(t.enum8):
        """Schedule state option."""

        Disabled = 0x00
        Enabled = 0x01

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            SASSWEL_STATE_ATTR: ("state", State, True),
            SASSWEL_HEATING_SETPOINT_ATTR: ("heating_setpoint", t.uint32_t, True),
            SASSWEL_LOCAL_TEMP_ATTR: ("local_temperature", t.uint32_t, True),
            SASSWEL_BATTERY_LOW_ATTR: ("battery_state", BatteryState, True),
            SASSWEL_SCHEDULE_ENABLE_ATTR: ("schedule_enabled", ScheduleState, True),
        }
    )

    TEMPERATURE_ATTRS = {
        SASSWEL_HEATING_SETPOINT_ATTR: "occupied_heating_setpoint",
        SASSWEL_LOCAL_TEMP_ATTR: "local_temperature",
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid in self.TEMPERATURE_ATTRS:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                self.TEMPERATURE_ATTRS[attrid],
                value * 10,
            )
        elif attrid == SASSWEL_STATE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "system_mode_reported", value
            )
        elif attrid == SASSWEL_BATTERY_LOW_ATTR:
            # this device doesn't have battery level reporting, only battery low alert
            # when the alert is active (1) we report 0% and 100% otherwise (0)
            self.endpoint.device.battery_bus.listener_event(
                "battery_change", 0 if value == 1 else 100
            )


class ThermostatCluster(TuyaThermostatCluster):
    """Thermostat cluster."""

    cluster_id = Thermostat.cluster_id

    _CONSTANT_ATTRIBUTES = {
        MIN_HEAT_SETPOINT_ATTR: 500,
        MAX_HEAT_SETPOINT_ATTR: 3000,
        CTRL_SEQ_OF_OPER_ATTR: Thermostat.ControlSequenceOfOperation.Heating_Only,  # the device supports heating mode
    }

    def system_mode_reported(self, value):
        """Handle reported system mode."""
        if value == 1:
            self._update_attribute(
                self.attributes_by_name["system_mode"].id, Thermostat.SystemMode.Heat
            )
            self._update_attribute(
                self.attributes_by_name["running_mode"].id, Thermostat.RunningMode.Heat
            )
            _LOGGER.debug("reported system_mode: heat")
        else:
            self._update_attribute(
                self.attributes_by_name["system_mode"].id, Thermostat.SystemMode.Off
            )
            self._update_attribute(
                self.attributes_by_name["running_mode"].id, Thermostat.RunningMode.Off
            )
            _LOGGER.debug("reported system_mode: off")

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to decidegree
            return {SASSWEL_HEATING_SETPOINT_ATTR: round(value / 10)}

        if attribute == "system_mode":
            # this quirk does not support programmig modes so we force the schedule mode to be always off
            # more details: https://github.com/zigpy/zha-device-handlers/issues/1815
            if value == self.SystemMode.Off:
                return {SASSWEL_STATE_ATTR: 0, SASSWEL_SCHEDULE_ENABLE_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {SASSWEL_STATE_ATTR: 1, SASSWEL_SCHEDULE_ENABLE_ATTR: 0}


class Thermostat_TYST11_c88teujp(TuyaThermostat):
    """Saswell 88teujp thermostat valve."""

    signature = {
        MODELS_INFO: [
            ("_TYST11_KGbxAXL2", "GbxAXL2"),
            ("_TYST11_c88teujp", "88teujp"),
            ("_TYST11_azqp6ssj", "zqp6ssj"),
            ("_TYST11_yw7cahqs", "w7cahqs"),
            ("_TYST11_9gvruqf5", "gvruqf5"),
            ("_TYST11_zuhszj9s", "uhszj9s"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=0
            # input_clusters=[0, 3]
            # output_clusters=[3, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
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
                    TuyaPowerConfigurationCluster,
                    Identify.cluster_id,
                    ThermostatCluster,
                    ManufacturerThermostatCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }


class Thermostat_TZE200_c88teujp(TuyaThermostat):
    """Saswell 88teujp thermostat valve."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_c88teujp", "TS0601"),
            ("_TZE200_azqp6ssj", "TS0601"),
            ("_TZE200_yw7cahqs", "TS0601"),
            ("_TZE200_9gvruqf5", "TS0601"),
            ("_TZE200_zuhszj9s", "TS0601"),
            ("_TZE200_2ekuz3dz", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=0
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
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
                    TuyaPowerConfigurationCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    ThermostatCluster,
                    ManufacturerThermostatCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
