"""Saswell (Tuya whitelabel) 88teujp thermostat valve quirk."""

from functools import reduce
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat

from . import TUYA_GET_DATA, TUYA_SET_DATA, TUYA_SET_DATA_RESPONSE, TuyaManufCluster
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

OCCUPIED_HEATING_SETPOINT_ATTR = 0x0012
SYSTEM_MODE_ATTR = 0x001C
RUNNING_MODE_ATTR = 0x001E
LOCAL_TEMP_ATTR = 0x0000
CTRL_SEQ_OF_OPER_ATTR = 0x001B
BATTERY_PERCENTAGE_REMAINING_ATTR = 0x0021

MIN_HEAT_SETPOINT_ATTR = 0x0015
MAX_HEAT_SETPOINT_ATTR = 0x0016


def payload_to_decimal(data):
    # Coverts command payload to a single decimal
    # e.g. [4, 0, 0, 1, 39] => 295 and [4, 0, 0, 0, 220] => 220
    return reduce(lambda acc, i: ((acc << 8) + i) % 2 ** 32, data[1:], 0)


def decimal_to_payload(number):
    # Coverts decimal to command payload
    # e.g. 295 => [4, 0, 0, 1, 39] and 220 => [4, 0, 0, 0, 220]
    hex = "{:X}".format(number).rjust(4, "0")
    chunk1 = int(hex[0:2], 16)
    chunk2 = int(hex[2:], 16)
    return [4, 0, 0, chunk1, chunk2]


class ManufacturerThermostatCluster(TuyaManufCluster):
    """Manufacturer thermostat cluster."""

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle cluster request."""
        if command_id != TUYA_GET_DATA and command_id != TUYA_SET_DATA_RESPONSE:
            return

        tuya_cmd = args[0]
        decimal = payload_to_decimal(tuya_cmd.data)

        if tuya_cmd.command_id == OCCUPIED_HEATING_SETPOINT_COMMAND_ID:
            self.endpoint.device.thermostat_bus.listener_event(
                OCCUPIED_HEATING_SETPOINT_REPORTED, decimal
            )
        elif tuya_cmd.command_id == LOCAL_TEMP_COMMAND_ID:
            self.endpoint.device.thermostat_bus.listener_event(
                LOCAL_TEMP_REPORTED, decimal
            )
        elif tuya_cmd.command_id == SYSTEM_MODE_COMMAND_ID:
            self.endpoint.device.thermostat_bus.listener_event(
                SYSTEM_MODE_REPORTED, decimal
            )
        elif tuya_cmd.command_id == BATTERY_STATE_COMMAND_ID:
            self.endpoint.device.battery_bus.listener_event(BATTERY_REPORTED, decimal)
        elif (
            tuya_cmd.command_id >= 110 and tuya_cmd.command_id <= 129
        ):  # Ignore historical data and schedules
            pass
        elif tuya_cmd.command_id == 362:  # Ignore away mode
            pass
        elif tuya_cmd.command_id == 364:  # Ignore auto/manual mode
            pass
        else:
            _LOGGER.debug(
                f"Unknown command received: {tuya_cmd.command_id} {tuya_cmd.data} {decimal}"
            )


class PowerConfigurationCluster(LocalDataCluster, PowerConfiguration):
    """Power configuration cluster."""

    cluster_id = PowerConfiguration.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.battery_bus.add_listener(self)

    def battery_reported(self, value):
        _LOGGER.debug(f"reported battery alert: {value}")
        if value == 1:  # alert
            self._update_attribute(
                BATTERY_PERCENTAGE_REMAINING_ATTR, 0
            )  # report 0% battery
        else:
            self._update_attribute(
                BATTERY_PERCENTAGE_REMAINING_ATTR, 200
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
        self._update_attribute(OCCUPIED_HEATING_SETPOINT_ATTR, value * 10)
        _LOGGER.debug(f"reported set temperature: {value}")

    def local_temp_reported(self, value):
        self._update_attribute(LOCAL_TEMP_ATTR, value * 10)
        _LOGGER.debug(f"reported local temperature: {value}")

    def system_mode_reported(self, value):
        if value == 1:
            self._update_attribute(SYSTEM_MODE_ATTR, Thermostat.SystemMode.Heat)
            self._update_attribute(RUNNING_MODE_ATTR, Thermostat.RunningMode.Heat)
            _LOGGER.debug("reported system_mode: heat")
        else:
            self._update_attribute(SYSTEM_MODE_ATTR, Thermostat.SystemMode.Off)
            self._update_attribute(RUNNING_MODE_ATTR, Thermostat.RunningMode.Off)
            _LOGGER.debug("reported system_mode: off")

    async def write_attributes(self, attributes, manufacturer=None):
        if "system_mode" in attributes:
            mode = attributes.get("system_mode")

            if mode == Thermostat.SystemMode.Off:
                await self.send_tuya_command(SYSTEM_MODE_COMMAND_ID, [1, 0])
                _LOGGER.debug("set system_mode: off")
            if mode == Thermostat.SystemMode.Heat:
                await self.send_tuya_command(SYSTEM_MODE_COMMAND_ID, [1, 1])
                _LOGGER.debug("set system_mode: heat")
        elif "occupied_heating_setpoint" in attributes:
            temperature = int(attributes.get("occupied_heating_setpoint") / 10)
            await self.send_tuya_command(
                OCCUPIED_HEATING_SETPOINT_COMMAND_ID, decimal_to_payload(temperature)
            )
            _LOGGER.debug(f"set occupied_heating_setpoint: {temperature}")
        else:
            _LOGGER.debug(f"write_attributes: {attributes}")

    async def send_tuya_command(self, cmd, data):
        cmd_payload = TuyaManufCluster.Command()
        cmd_payload.status = 0
        cmd_payload.tsn = 0
        cmd_payload.function = 0
        cmd_payload.command_id = cmd
        cmd_payload.data = data
        await self.endpoint.tuya_manufacturer.command(
            TUYA_SET_DATA,
            cmd_payload,
            expect_reply=False,
        )


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
