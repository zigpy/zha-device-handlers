"""Module to handle quirks of the  Zen Within thermostat."""
import logging
import datetime
import concurrent.futures as futures
import zigpy.profiles.zha as zha_p
from zhaquirks import LocalDataCluster, Bus
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters import general, hvac
import zigpy.types as t
from zigpy.zcl import foundation
from . import TUYA_CLUSTER_ID
from ..const import *

_LOGGER = logging.getLogger(__name__)


#https://github.com/Koenkk/zigbee-herdsman-converters/blob/57ff9696bb7958354a92bf4fc99dc18d8606f13d/lib/tuya.js#L244
WINDOW_DETECTION = 8
FROST_DETECTION = 10
TEMP_CALIBRATION = 27
PING = 36
CHILD_LOCK = 40
ON_OFF = 101
CURRENT_TEMPERATURE = 102
HEATING_SETPOINT = 103
LOW_BATTERY = 105
AWAY_MODE = 106
SCHEDULE_MODE = 108
SETPOINT_HISTORY_DAY = 110
SETPOINT_HISTORY_WEEK = 112
SETPOINT_HISTORY_MONTH = 113
SETPOINT_HISTORY_YEAR = 114
LOCAL_HISTORY_DAY = 115
LOCAL_HISTORY_WEEK = 116
LOCAL_HISTORY_MONTH = 117
LOCAL_HISTORY_YEAR = 118
MOTOR_HISTORY_DAY = 119
MOTOR_HISTORY_WEEK = 120
MOTOR_HISTORY_MONTH = 121
MOTOR_HISTORY_YEAR = 122
ANTI_SCALING = 130

SHIFTING_MAP = {
    WINDOW_DETECTION: 58,
    FROST_DETECTION: 60,
    TEMP_CALIBRATION: 77,
    PING: 86,
    CHILD_LOCK: 90,
}


ATTR_TO_EVENTS = {
    WINDOW_DETECTION: 'update_attribute',
    FROST_DETECTION: 'update_attribute',
    PING: 'ping',
    CHILD_LOCK: 'child_lock_reported',
    ON_OFF: 'power_reported',
    CURRENT_TEMPERATURE: 'current_temp_reported',
    HEATING_SETPOINT: 'heating_setpoint_reported',
    615: 'heating_setpoint_reported',
    SCHEDULE_MODE: 'mode_reported',
    LOW_BATTERY: 'low_battery_reported',
    AWAY_MODE: 'away_mode_reported',
    TEMP_CALIBRATION: 'update_attribute',
    SETPOINT_HISTORY_DAY: 'update_attribute',
    SETPOINT_HISTORY_WEEK: 'update_attribute',
    SETPOINT_HISTORY_MONTH: 'update_attribute',
    SETPOINT_HISTORY_YEAR: 'update_attribute',
    LOCAL_HISTORY_DAY: 'update_attribute',
    LOCAL_HISTORY_WEEK: 'update_attribute',
    LOCAL_HISTORY_MONTH: 'update_attribute',
    LOCAL_HISTORY_YEAR: 'update_attribute',
    MOTOR_HISTORY_DAY: 'update_attribute',
    MOTOR_HISTORY_WEEK: 'update_attribute',
    MOTOR_HISTORY_MONTH: 'update_attribute',
    MOTOR_HISTORY_YEAR: 'update_attribute',
    ANTI_SCALING: 'update_attribute',
    # 123: 'reported_schedule',
    # 124: 'reported_schedule',
    # 125: 'reported_schedule',
    # 126: 'reported_schedule',
    # 127: 'reported_schedule',
    # 128: 'reported_schedule',
    # 129: 'reported_schedule',
}


# DAY_OF_WEEK = {
#     # https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/toZigbee.js#L3113
#     123: 'Sun',
#     124: 'Mon',
#     125: 'Tue',
#     126: 'Wed',
#     127: 'Thu',
#     128: 'Fri',
#     129: 'Sat',
# }


class Data(t.List, item_type=t.uint8_t):
    pass


class Temperature(t.uint16_t):
    def __str__(self):
        return str(self.convert_to_temperature(self.serialize()))

    @staticmethod
    def convert_to_temperature(value):
        data = value[-2:]
        data_b = bytes()
        for d in data:
            data_b += d.to_bytes(length=1, byteorder='big')
        tempr = int.from_bytes(data_b, byteorder='big', signed=False) / 10
        return tempr


class Time(t.uint16_t):
    def __str__(self):
        value = int.from_bytes(self.serialize(), byteorder='big', signed=False)
        decimal_hours_minutes = float(value / 60)
        hours = int(decimal_hours_minutes)
        minutes = round(60 * (decimal_hours_minutes - hours))
        return '{}:{}'.format(hours, minutes)


class LocalDataBusListenerCluster(LocalDataCluster, CustomCluster):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint.device.data_bus.add_listener(self)

    def handle_cluster_request(self, tsn, command_id, args):
        if args:
            resp = args[0]
        else:
            resp = None
        if isinstance(resp, SiterwellTRVCluster.Command) and resp.dp in ATTR_TO_EVENTS.keys():
            attr_id = SHIFTING_MAP.get(resp.dp, resp.dp)
            self.endpoint.device.data_bus.listener_event(
                ATTR_TO_EVENTS.get(resp.dp), attr_id, resp.data)
        elif command_id == PING:
            self.endpoint.device.data_bus.listener_event(ATTR_TO_EVENTS.get(PING), SHIFTING_MAP.get(PING), resp)
        else:
            _LOGGER.debug('Unsupported command {} : {}'.format(command_id, args))

    @staticmethod
    def prepare_command(attrid, initial_value_bytes, transid):
        if attrid in [CURRENT_TEMPERATURE, HEATING_SETPOINT]:
            datatype = 2
            value = round(t.Half.deserialize(initial_value_bytes)[0] * 10)
            value_bytes = t.uint16_t(value).to_bytes(length=2, byteorder='big')
            data_list = [0, 0, value_bytes[0], value_bytes[1]]
        elif attrid in (ON_OFF, SCHEDULE_MODE):
            datatype = 1
            data_list = list(initial_value_bytes)

        cmd_payload = SiterwellTRVCluster.Command()
        cmd_payload.status = 0
        cmd_payload.transid = transid
        cmd_payload.dp = attrid
        cmd_payload.datatype = datatype
        cmd_payload.length_hi = (len(data_list) >> 8) & 0xFF
        cmd_payload.length_lo = len(data_list) & 0xFF
        cmd_payload.data = data_list
        return cmd_payload

    async def send_command(self, command, manufacturer, tsn):
        try:
            return await super().command(
                0x0000,
                command,
                manufacturer=manufacturer,
                expect_reply=False,
                tsn=tsn
            )
        except futures.TimeoutError:
            pass

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        for record in records:
            initial_value_bytes = record.value.value.serialize()
            sequence = self.endpoint.device.application.get_sequence()
            cmd_payload = self.prepare_command(record.attrid, initial_value_bytes, sequence)
            await self.send_command(cmd_payload, manufacturer, cmd_payload.transid)
        return (foundation.Status.SUCCESS,)

    def mode_reported(self, attr_id, value):
        self._update_attribute(attr_id, value[0])

    def heating_setpoint_reported(self, attr_id, value):
        tempr = Temperature.convert_to_temperature(value)
        self._update_attribute(attr_id, tempr)

    def power_reported(self, attr_id, value):
        self._update_attribute(attr_id, value[0])

    def current_temp_reported(self, attr_id, value):
        tempr = Temperature.convert_to_temperature(value)
        self._update_attribute(attr_id, tempr)

    def ping(self, attr_id, value=None):
        self._update_attribute(attr_id, str(datetime.datetime.utcnow()))


    # def reported_schedule(self, attr_id, value):
    #     day = DAY_OF_WEEK.get(attr_id)
    #     v_bytes = value.serialize()
    #     schedule, _ = SiterwellTRVCluster.Schedule().deserialize(v_bytes)
    #     self._update_attribute(day, schedule)


class SiterwellTRVCluster(LocalDataBusListenerCluster):
    """https://github.com/Koenkk/zigbee-herdsman/blob/master/src/zcl/definition/cluster.ts"""
    name = "Tuya Manufacturer Specicific TRV"
    cluster_id = TUYA_CLUSTER_ID
    ep_attribute = "tuya_manufacturer"

    class SystemMode(t.enum8):
        Off = 0x00
        On = 0x01

    class ScheduleMode(t.enum8):
        Off = 0x00
        On = 0x01

    class Command(t.Struct):
        status: t.uint8_t
        transid: t.uint8_t
        dp: t.uint8_t
        datatype: t.uint8_t
        length_hi: t.uint8_t
        length_lo: t.uint8_t
        data: Data

    # class Schedule(t.Struct):
    #     schedule_type: t.uint8_t
    #     period_1_time: Time
    #     period_1_temperature: Temperature
    #     period_2_time: Time
    #     period_2_temperature: Temperature
    #     period_3_time: Time
    #     period_3_temperature: Temperature
    #     period_4_time: Time
    #     period_4_temperature: Temperature

    manufacturer_client_commands = {
        0x0001: ("get_data", (Command,), True),
        0x0002: ("set_data_response", (Command,), True),
        0x0024: ("ping", (t.uint8_t, t.uint8_t), True),

    }
    manufacturer_server_commands = {
        0x0000: ("set_data", (Command,), False),
        0x0001: ("get_data", (Command,), True),
    }
    manufacturer_attributes = {
        CURRENT_TEMPERATURE: ("current_temperature", t.Half),
        HEATING_SETPOINT: ("heating_setpoint", t.Half),
        SCHEDULE_MODE: ("schedule_mode", ScheduleMode),
        ON_OFF: ("system_mode", SystemMode),
        SHIFTING_MAP.get(PING): ("ping", t.CharacterString),
        SHIFTING_MAP.get(WINDOW_DETECTION): ('open_window_detected', t.Bool),
        SHIFTING_MAP.get(FROST_DETECTION):  ('frost_detected', t.Bool),
        SHIFTING_MAP.get(CHILD_LOCK): ('child_lock', t.Bool),
        SHIFTING_MAP.get(TEMP_CALIBRATION): ('temp_calibration', Data),
        LOW_BATTERY: ('low_battery_detected', t.Bool),
        AWAY_MODE: ('away_mode', t.Bool),
        SETPOINT_HISTORY_DAY: ('setpoint_history_day', Data),
        SETPOINT_HISTORY_WEEK: ('setpoint_history_week', Data),
        SETPOINT_HISTORY_MONTH: ('setpoint_history_month', Data),
        SETPOINT_HISTORY_YEAR: ('setpoint_history_year', Data),
        LOCAL_HISTORY_DAY: ('local_history_day', Data),
        LOCAL_HISTORY_WEEK: ('local_history_week', Data),
        LOCAL_HISTORY_MONTH: ('local_history_month', Data),
        LOCAL_HISTORY_YEAR: ('local_history_year', Data),
        MOTOR_HISTORY_DAY: ('motor_history_day', Data),
        MOTOR_HISTORY_WEEK: ('motor_history_week', Data),
        MOTOR_HISTORY_MONTH: ('motor_history_month', Data),
        MOTOR_HISTORY_YEAR: ('motor_history_year', Data),
        ANTI_SCALING: ('anti_scaling_detected', t.Bool),
        # 123: (DAY_OF_WEEK.get(123), Schedule),
        # 124: (DAY_OF_WEEK.get(124), Schedule),
        # 125: (DAY_OF_WEEK.get(125), Schedule),
        # 126: (DAY_OF_WEEK.get(126), Schedule),
        # 127: (DAY_OF_WEEK.get(127), Schedule),
        # 128: (DAY_OF_WEEK.get(128), Schedule),
        # 129: (DAY_OF_WEEK.get(129), Schedule),
    }


class SiterwellThermostatCluster(hvac.Thermostat, SiterwellTRVCluster):
    attributes = hvac.Thermostat.attributes.copy()
    _CONSTANT_ATTRIBUTES = {
        0x001B: hvac.Thermostat.ControlSequenceOfOperation.Heating_Only,
        0x0015: 500,
        0x0016: 3000,
    }

    def power_reported(self, attr_id, value):
        super(SiterwellThermostatCluster, self).power_reported(attr_id, value)
        if value[0]:
            self._update_attribute(self.attridx["system_mode"], self.SystemMode.Heat)
            self._update_attribute(self.attridx["running_mode"], self.RunningMode.Heat)
            self._update_attribute(self.attridx["running_state"], self.RunningState.Heat_State_On)
        else:
            self._update_attribute(self.attridx["system_mode"], self.SystemMode.Off)
            self._update_attribute(self.attridx["running_mode"], self.RunningMode.Off)
            self._update_attribute(self.attridx["running_state"], self.RunningState.Idle)

    def mode_reported(self, attr_id, value):
        super(SiterwellThermostatCluster, self).mode_reported(attr_id, value)
        if value[0]:
            self._update_attribute(self.attridx["programing_oper_mode"], self.ProgrammingOperationMode.Schedule_programming_mode)
        else:
            self._update_attribute(self.attridx["programing_oper_mode"], self.ProgrammingOperationMode.Simple)

    def heating_setpoint_reported(self, attr_id, value):
        super(SiterwellThermostatCluster, self).heating_setpoint_reported(attr_id, value)
        temp = self.get(self.manufacturer_attributes[attr_id][0])
        self._update_attribute('occupied_heating_setpoint', temp * 100)

    def current_temp_reported(self, attr_id, value):
        super(SiterwellThermostatCluster, self).current_temp_reported(attr_id, value)
        temp = self.get(self.manufacturer_attributes[attr_id][0])
        self._update_attribute('local_temp', temp * 100)

    async def write_attributes(self, attributes, manufacturer=None):
        """Implement writeable attributes."""

        records = self._write_attr_records(attributes)

        if not records:
            return (foundation.Status.SUCCESS,)

        for record in records:
            if record.attrid == ON_OFF:
                mode_map = {
                    hvac.Thermostat.SystemMode.Heat: SiterwellTRVCluster.SystemMode.On,
                    hvac.Thermostat.SystemMode.Off: SiterwellTRVCluster.SystemMode.Off,
                }
                await self.endpoint.tuya_manufacturer.write_attributes({ON_OFF: mode_map[record.value.value]})
            elif record.attrid == 18:
                value = record.value.value / 100
                await self.endpoint.tuya_manufacturer.write_attributes({HEATING_SETPOINT: value})
            else:
                self.error('Can not set attrid {} to {}.'.format(record.attrid, record.value))

        return (foundation.Status.SUCCESS,)


class SiterwellTrvUserInterface(hvac.UserInterface):
    """HVAC User interface cluster for tuya electric heating thermostats."""
    _CONSTANT_ATTRIBUTES = {
        0x0000: hvac.UserInterface.TemperatureDisplayMode.Metric,
        0x0001: hvac.UserInterface.KeypadLockout.Level_1_lockout,
        0x0002: hvac.UserInterface.ScheduleProgrammingVisibility.Enabled,
    }


class Battery(general.BinaryOutput, SiterwellTRVCluster):
    cluster_id = general.BinaryOutput.cluster_id
    manufacturer_attributes = {}
    _CONSTANT_ATTRIBUTES = {
        0x0004: 'Battery is LOW',
        0x002E: 'Battery is OK',
        0x001C: 'Battery state',
    }

    def low_battery_reported(self, attr_id, value):
        self._update_attribute(self.attridx['present_value'], bool(value[0]))


class TuyaTRV(CustomDevice):
    """Tuya Within Sasswell Thermostat custom device.
    https://zigbee.blakadder.com/Saswell_SEA801-Zigbee.html
    {
      "node_descriptor": "NodeDescriptor(
        byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=0, maximum_buffer_size=82,
        maximum_incoming_transfer_size=255, server_mask=11264, maximum_outgoing_transfer_size=255,
        descriptor_capability_field=0)",
      "endpoints": {
        "1": {
          "profile_id": 260,
          "device_type": "0x0000",
          "in_clusters": [
            "0x0000",
            "0x0003"
          ],
          "out_clusters": [
            "0x0003",
            "0x0019"
            socket://192.168.88.211:8888
          ]
        }
      },
      "manufacturer": "_TYST11_KGbxAXL2",
      "model": "GbxAXL2",
      "class": "zigpy.device.Device"
    """
    def __init__(self, *args, **kwargs):
        self.data_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            ('_TYST11_KGbxAXL2', "GbxAXL2"),
            ('_TYST11_c88teujp', "88teujp"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    general.Identify.cluster_id,
                    general.Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: False,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                    general.PowerConfiguration.cluster_id,
                    general.PowerProfile.cluster_id,
                    SiterwellTRVCluster,
                    SiterwellThermostatCluster,
                    SiterwellTrvUserInterface,
                    Battery,
                ],
                OUTPUT_CLUSTERS: [
                    general.Identify.cluster_id,
                    general.Ota.cluster_id],
            }
        }
    }
