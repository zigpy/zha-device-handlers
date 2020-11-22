"""Saswell (Tuya whitelabel) 88teujp thermostat valve quirk."""

import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat

from . import TuyaManufClusterAttributes
from .. import Bus, LocalDataCluster
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


class ThermostatCluster(LocalDataCluster, Thermostat):
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

    async def write_attributes(self, attributes, manufacturer=None):
        """Override remote writes."""
        records = self._write_attr_records(attributes)

        if not records:
            return (foundation.Status.SUCCESS,)

        manufacturer_attrs = {}
        for record in records:
            attr_name = self.attributes[record.attrid][0]
            new_attrs = self.map_attribute(attr_name, record.value.value)

            _LOGGER.debug(
                "[0x%04x:%s:0x%04x] Mapping standard %s (0x%04x) "
                "with value %s to custom %s",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attr_name,
                record.attrid,
                repr(record.value.value),
                repr(new_attrs),
            )

            manufacturer_attrs.update(new_attrs)

        if not manufacturer_attrs:
            return (foundation.Status.FAILURE,)

        await self.endpoint.tuya_manufacturer.write_attributes(
            manufacturer_attrs, manufacturer=manufacturer
        )

        return (foundation.Status.SUCCESS,)

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


class Thermostat88teujp(CustomDevice):
    """Saswell 88teujp thermostat valve."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_bus = Bus()
        self.battery_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=0
        # device_version=0
        # input_clusters=[0, 3]
        # output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_c88teujp", "88teujp")],
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
