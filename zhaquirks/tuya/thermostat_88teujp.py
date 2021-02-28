"""Saswell (Tuya whitelabel) 88teujp thermostat valve quirk."""

import logging

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat

from . import TuyaManufClusterAttributes, TuyaThermostat, TuyaThermostatCluster
from .. import LocalDataCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)

OCCUPIED_HEATING_SETPOINT_REPORTED = "occupied_heating_setpoint_reported"
SYSTEM_MODE_REPORTED = "system_mode_reported"
LOCAL_TEMP_REPORTED = "local_temp_reported"
BATTERY_REPORTED = "battery_reported"

OCCUPIED_HEATING_SETPOINT_COMMAND_ID = 615
SYSTEM_MODE_COMMAND_ID = 357
LOCAL_TEMP_COMMAND_ID = 614
BATTERY_STATE_COMMAND_ID = 1385

CTRL_SEQ_OF_OPER_ATTR = 0x001B

MIN_HEAT_SETPOINT_ATTR = 0x0015
MAX_HEAT_SETPOINT_ATTR = 0x0016


class ManufacturerThermostatCluster(TuyaManufClusterAttributes):
    """Manufacturer thermostat cluster."""

    manufacturer_attributes = {
        SYSTEM_MODE_COMMAND_ID: ("system_mode", t.uint8_t),
        OCCUPIED_HEATING_SETPOINT_COMMAND_ID: ("occupied_heating_setpoint", t.uint32_t),
        LOCAL_TEMP_COMMAND_ID: ("local_temp", t.uint32_t),
        BATTERY_STATE_COMMAND_ID: ("battery_state", t.uint8_t),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == OCCUPIED_HEATING_SETPOINT_COMMAND_ID:
            self.endpoint.device.thermostat_bus.listener_event(
                OCCUPIED_HEATING_SETPOINT_REPORTED, value
            )
        elif attrid == SYSTEM_MODE_COMMAND_ID:
            self.endpoint.device.thermostat_bus.listener_event(
                SYSTEM_MODE_REPORTED, value
            )
        elif attrid == BATTERY_STATE_COMMAND_ID:
            self.endpoint.device.battery_bus.listener_event(BATTERY_REPORTED, value)
        elif attrid == LOCAL_TEMP_COMMAND_ID:
            self.endpoint.device.thermostat_bus.listener_event(
                LOCAL_TEMP_REPORTED, value
            )


class PowerConfigurationCluster(LocalDataCluster, PowerConfiguration):
    """Power configuration cluster."""

    cluster_id = PowerConfiguration.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.battery_bus.add_listener(self)

    def battery_reported(self, value):
        """Handle reported battery state."""
        _LOGGER.debug("reported battery alert: %d", value)
        if value == 1:  # alert
            self._update_attribute(
                self.attridx["battery_percentage_remaining"], 0
            )  # report 0% battery
        else:
            self._update_attribute(
                self.attridx["battery_percentage_remaining"], 200
            )  # report 100% battery


class ThermostatCluster(TuyaThermostatCluster):
    """Thermostat cluster."""

    cluster_id = Thermostat.cluster_id

    _CONSTANT_ATTRIBUTES = {
        MIN_HEAT_SETPOINT_ATTR: 500,
        MAX_HEAT_SETPOINT_ATTR: 3000,
        CTRL_SEQ_OF_OPER_ATTR: Thermostat.ControlSequenceOfOperation.Heating_Only,  # the device supports heating mode
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)

    def occupied_heating_setpoint_reported(self, value):
        """Handle reported occupied heating setpoint state."""
        self._update_attribute(self.attridx["occupied_heating_setpoint"], value * 10)
        _LOGGER.debug("reported occupied heating setpoint: %d", value)

    def local_temp_reported(self, value):
        """Handle reported local temperature."""
        self._update_attribute(self.attridx["local_temp"], value * 10)
        _LOGGER.debug("reported local temperature: %d", value)

    def system_mode_reported(self, value):
        """Handle reported system mode."""
        if value == 1:
            self._update_attribute(
                self.attridx["system_mode"], Thermostat.SystemMode.Heat
            )
            self._update_attribute(
                self.attridx["running_mode"], Thermostat.RunningMode.Heat
            )
            _LOGGER.debug("reported system_mode: heat")
        else:
            self._update_attribute(
                self.attridx["system_mode"], Thermostat.SystemMode.Off
            )
            self._update_attribute(
                self.attridx["running_mode"], Thermostat.RunningMode.Off
            )
            _LOGGER.debug("reported system_mode: off")

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to decidegree
            return {OCCUPIED_HEATING_SETPOINT_COMMAND_ID: round(value / 10)}

        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {SYSTEM_MODE_COMMAND_ID: 0}
            if value == self.SystemMode.Heat:
                return {SYSTEM_MODE_COMMAND_ID: 1}


class Thermostat_TYST11_c88teujp(TuyaThermostat):
    """Saswell 88teujp thermostat valve."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=0
        # device_version=0
        # input_clusters=[0, 3]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            ("_TYST11_c88teujp", "88teujp"),
            ("_TYST11_KGbxAXL2", "GbxAXL2"),
            ("_TYST11_zuhszj9s", "uhszj9s"),
            ("_TYST11_yw7cahqs", "w7cahqs"),
        ],
        ENDPOINTS: {
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
                    Identify.cluster_id,
                    ManufacturerThermostatCluster,
                    PowerConfigurationCluster,
                    ThermostatCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    PowerConfigurationCluster,
                    ThermostatCluster,
                ],
            }
        },
    }


class Thermostat_TZE200_c88teujp(TuyaThermostat):
    """Saswell 88teujp thermostat valve."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [("_TZE200_c88teujp", "TS0601")],
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
                    ManufacturerThermostatCluster,
                    PowerConfigurationCluster,
                    ThermostatCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    PowerConfigurationCluster,
                    ThermostatCluster,
                ],
            }
        }
    }
