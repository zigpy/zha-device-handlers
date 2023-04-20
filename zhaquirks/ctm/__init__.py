"""Quirks for CTM Lyng products."""

import logging
from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import AnalogOutput, OnOff
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks import PowerConfigurationCluster, LocalDataCluster

_LOGGER = logging.getLogger(__name__)

CTM = "CTM Lyng"
CTM_MFCODE = 0x1337


class CtmPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.8
    MAX_VOLTS = 3.1


class CtmOnOff(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    attributes = OnOff.attributes.copy()
    attributes.update(
        {
            0x2200: ("device_mode", t.uint8_t),
            0x2201: ("device_enabled", t.Bool),
            0x2202: ("tamper_lock_enabled", t.Bool),
            0x5000: ("current_flag", t.uint8_t, True),
            0x5001: ("relay_state", t.Bool, True),
        }
    )


class CtmTemperatureMeasurement(CustomCluster, TemperatureMeasurement):
    """CTM Lyng custom temperature measurement cluster."""

    attributes = TemperatureMeasurement.attributes.copy()
    attributes.update(
        {
            0x0400: ("temperature_offset", t.int8s, True),
        }
    )


class CtmThermostatCluster(CustomCluster, Thermostat):
    """CTM Lyng custom thermostat cluster."""

    class TemperatureSensor(t.enum8):
        """Temperatur sensor in use."""

        Air = 0x00
        Floor = 0x01
        External = 0x02
        Regulator = 0x03
        Protection_Air = 0x04
        Protection_External = 0x05
        Protection_Regulator = 0x06

    class RegulationMode(t.uint8_t):
        """Regulation modes of the thermostat."""

        Thermostat = 0x00
        Regulator = 0x01
        Zzilent = 0x02

    class OperationMode(t.uint8_t):
        """Operation modes of the thermostat."""

        Off = 0x00
        Anti_Freeze_Mode = 0x01
        Night_Saving_Mode = 0x02
        Comfort_Mode = 0x03
        Energy_Control = 0x04

    attributes = Thermostat.attributes.copy()
    attributes.update(
        {
            0x0401: ("load", t.uint16_t),
            0x0402: ("display_text", t.LimitedCharString(19)),
            0x0403: ("temperature_sensor", TemperatureSensor),
            0x0405: ("regulator_mode_enabled", t.Bool),
            0x0406: ("power_status", t.Bool),
            0x0408: ("mean_power", t.uint16_t),
            0x0409: ("current_floor_temperature", t.int16s),
            0x0411: ("night_switching_enabled", t.Bool),
            0x0412: ("frost_guard_enabled", t.Bool),
            0x0413: ("child_lock_enabled", t.Bool),
            0x0414: ("maximum_floor_temperature", t.uint8_t),
            0x0415: ("heating_active", t.Bool),
            0x0420: ("regulator_setpoint", t.uint8_t),
            0x0421: ("regulation_mode", RegulationMode),
            0x0422: ("operation_mode", OperationMode),
            0x0423: ("maximum_floor_temp_guard", t.Bool),
            0x0424: ("weekly_timer_enabled", t.Bool),
            0x0425: ("frost_guard_setpoint", t.uint8_t),
            0x0426: ("external_temperature", t.int16s),
            0x0428: ("exteral_sensor_source", t.uint16_t),
            0x0429: ("current_air_temperature", t.int16s),
            0x042B: ("floor_sensor_error", t.Bool),
            0x042C: ("external_air_sensor_error", t.Bool),
        }
    )

    def _update_attribute(self, attrid, value):
        _LOGGER.debug(f"Attribute update: {self.attributes[attrid].name}: {value}")
        super()._update_attribute(attrid, value)


class CtmGroupConfigCluster(CustomCluster):
    """CTM Lyng custom group config cluster."""

    name = "CTM Group Config"
    cluster_id = 0xFEA7
    ep_attribute = "ctm_group_config"
    attributes: dict[int, foundation.ZCLAttributeDef] = {
        0x0000: ("grpup_id", t.uint16_t, True),
        0xFFFD: ("cluster_revision", t.uint16_t),
    }


class CtmDiagnosticsCluster(CustomCluster):
    """CTM Lyng custom diagnostics cluster."""

    name = "CTM Diagnostics"
    cluster_id = 0xFEED
    ep_attribute = "ctm_diagnostics"
    attributes: dict[int, foundation.ZCLAttributeDef] = {
        0x0000: ("last_reset_info", t.uint8_t, True),
        0x0001: ("last_extended_reset_info", t.uint16_t, True),
        0x0002: ("reboot_counter", t.uint16_t, True),
        0x0003: ("last_hop_lqi", t.uint8_t, True),
        0x0004: ("last_hop_rssi", t.int8s, True),
        0x0005: ("tx_power", t.int8s, True),
        0x0006: ("parent_node_id", t.uint16_t, True),
        0x0010: ("button_0_click_counter", t.uint16_t, True),
        0x0020: ("button_0_ms_click_counter", t.uint16_t, True),
        0x0401: ("debug_int", t.uint32_t, True),
        0xFFFD: ("cluster_revision", t.uint16_t),
    }


class CtmStoveGuardCluster(CustomCluster):
    """CTM Lyng custom stove guard cluster."""

    class AlarmStatus(t.uint8_t):
        """Alarm status of the stove guard."""

        OK = 0x00
        Tamper = 0x01
        High_Temperature = 0x02
        Timer = 0x03
        Battery_Alarm = 0x07
        Error = 0x08

    class BatteryAlarm(t.uint8_t):
        """Battery alarm status of the stove guard."""

        OK = 0x00
        Battery_Alarm = 0x01

    class ActiveStatus(t.uint8_t):
        """Active status of the stove guard (In use)."""

        Inactive = 0x00
        Active = 0x01

    name = "CTM Stove Guard"
    cluster_id = 0xFFC9
    ep_attribute = "ctm_stove_guard"
    attributes: dict[int, foundation.ZCLAttributeDef] = {
        0x0001: ("alarm_status", AlarmStatus, True),
        0x0002: ("battery_alarm", BatteryAlarm, True),
        0x0003: ("temperature", t.uint16_t, True),
        0x0004: ("ambient_temperature", t.uint8_t, True),
        0x0005: ("active", ActiveStatus, True),
        0x0006: ("runtime", t.uint16_t, True),
        0x0007: ("runtime_timeout", t.uint16_t, True),
        0x0008: ("reset_reason", t.uint8_t, True),
        0x0009: ("dip_switch", t.uint8_t, True),
        0x000A: ("software_version", t.uint8_t, True),
        0x000B: ("hardware_version", t.uint8_t, True),
        0x000C: ("bootloader_version", t.uint8_t, True),
        0x000D: ("model", t.uint16_t, True),
        0x0010: ("paired_with_address", t.EUI64, True),
        0x0100: ("relay_current_flag", t.uint8_t, True),
        0x0101: ("relay_current", t.uint8_t, True),
        0x0102: ("relay_status", t.uint8_t, True),
        0x0103: ("relay_ext_button", t.uint8_t, True),
        0x0104: ("relay_alarm", t.uint8_t, True),
        0x0105: ("relay_sensor_alarm", AlarmStatus, True),
        0xFFFD: ("cluster_revision", t.uint16_t),
    }


class CtmOnOffDataCluster(LocalDataCluster, OnOff):
    """CTM Lyng custom helper onoff data cluster."""

    name = "OnOff Helper"

    def on_off_change(self, value):
        self._update_attribute(self.attributes_by_name["on_off"].id, value)

    async def write_on_off(self, value):
        """Defer on_off commands to writing attribute function."""
        return [
            foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Write_Attributes_rsp
            ].schema(
                status_records=(
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.SUCCESS
                        ),
                    ]
                )
            ),
        ]

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=False, tsn=None
    ):
        """Override the default Cluster command."""

        if command_id in (0x0000, 0x0001, 0x0002):
            if command_id == 0x0000:
                value = False

            elif command_id == 0x0001:
                value = True

            else:
                attrid = self.attributes_by_name["on_off"].id
                success, _ = await self.read_attributes(
                    (attrid,), manufacturer=manufacturer
                )
                try:
                    value = success[attrid]
                except KeyError:
                    return foundation.GENERAL_COMMANDS[
                        foundation.GeneralCommand.Default_Response
                    ].schema(command_id=command_id, status=foundation.Status.FAILURE)
                value = not value

            _LOGGER.debug(f"On/Off helper {self.name}: {value}")
            result = await self.write_on_off(value)
            if isinstance(result, list):
                result = result[0]
            _LOGGER.debug(f"On/Off helper {self.name}: {value}, {result}")
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=result[0][0].status)

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class CtmAnalogOutputDataCluster(LocalDataCluster, AnalogOutput):
    """CTM Lyng custom helper analogoutput data cluster."""

    name = "AnalogOutput Helper"

    def value_update(self, value):
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    async def write_output_value(self, value):
        """Defer present_value to writing attribute function."""
        return [
            foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Write_Attributes_rsp
            ].schema(
                status_records=(
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.SUCCESS
                        ),
                    ]
                )
            ),
        ]

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer the present_value attribute to write_output_value."""
        result = False
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id

            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue

            self._update_attribute(attrid, value)

            if attrid == self.attributes_by_name["present_value"].id:
                _LOGGER.debug(f"AnalogOutput helper {self.name}: {value}")
                result = await self.write_output_value(value)
                _LOGGER.debug(f"AnalogOutput helper {self.name}: {value}, {result}")
                if isinstance(result, list):
                    result = result[0]

        return (
            result
            if result
            else ([foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],)
        )
