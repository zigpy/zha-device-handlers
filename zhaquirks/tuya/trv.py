"""Module to handle quirks of the  Zen Within thermostat."""
import asyncio
import logging
import datetime
import concurrent.futures as futures
from time import sleep
from typing import Union, Optional, List, Dict, Any

import zigpy.profiles.zha as zha_p
from zhaquirks import LocalDataCluster, Bus
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters import general, homeautomation, hvac
import zigpy.types as t
from zigpy.zcl import foundation
from . import TuyaManufCluster, TUYA_CMD_BASE, TUYA_SET_DATA, TuyaManufClusterAttributes
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID, SKIP_CONFIGURATION, CLUSTER_ID, COMMAND, SHORT_PRESS, TURN_ON, COMMAND_TOGGLE, ENDPOINT_ID, LONG_PRESS,
    COMMAND_RELEASE, ARGS, COMMAND_ON, ON,
)

_LOGGER = logging.getLogger(__name__)

PROGRAM_MODES = {
    1: "single",
    2: "week_weekend",
    3: "week_sat_sun",
    4: "full",
}

DAY_OF_WEEK = {
    # https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/toZigbee.js#L3113
    123: 'Sun',
    124: 'Mon',
    125: 'Tue',
    126: 'Wed',
    127: 'Thu',
    128: 'Fri',
    129: 'Sat',
}

ATTR_TO_EVENTS = {
    36: 'ping',
    101: 'power_reported',
    102: 'current_temp_reported',
    103: 'heating_setpoint_reported',
    615: 'heating_setpoint_reported',
    108: 'mode_reported',
    123: 'reported_schedule',
    124: 'reported_schedule',
    125: 'reported_schedule',
    126: 'reported_schedule',
    127: 'reported_schedule',
    128: 'reported_schedule',
    129: 'reported_schedule',
    'power_reported': 101,
    'current_temp_reported': 102,
    'heating_setpoint_reported': 103,
    'mode_reported': 108,
    'schedule_day_1': 123,
    'schedule_day_2': 124,
    'schedule_day_3': 125,
    'schedule_day_4': 126,
    'schedule_day_5': 127,
    'schedule_day_6': 128,
    'schedule_day_7': 129,
}
# 105: ("battery", t.uint8_t),
# 104: ("valve_pos", t.uint8_t),


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


class TuyaTRVCluster(LocalDataCluster, TuyaManufClusterAttributes):
    """https://github.com/Koenkk/zigbee-herdsman/blob/master/src/zcl/definition/cluster.ts"""

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

    class Schedule(t.Struct):
        schedule_type: t.uint8_t
        period_1_time: Time
        period_1_temperature: Temperature
        period_2_time: Time
        period_2_temperature: Temperature
        period_3_time: Time
        period_3_temperature: Temperature
        period_4_time: Time
        period_4_temperature: Temperature

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.data_bus.add_listener(self)

    def reported_schedule(self, attr_id, value):
        day = DAY_OF_WEEK.get(attr_id)
        v_bytes = value.serialize()
        schedule, _ = TuyaTRVCluster.Schedule().deserialize(v_bytes)
        self._update_attribute(day, schedule)

    def power_reported(self, attr_id, value):
        self._update_attribute(attr_id, value[0])

    def ping(self, attr_id, value=None):
        self._update_attribute(attr_id, str(datetime.datetime.utcnow()))

    def mode_reported(self, attr_id, value):
        self._update_attribute(attr_id, value[0])

    def current_temp_reported(self, attr_id, value):
        tempr = Temperature.convert_to_temperature(value)
        self._update_attribute(attr_id, tempr)

    def heating_setpoint_reported(self, attr_id, value):
        tempr = Temperature.convert_to_temperature(value)
        self._update_attribute(attr_id, tempr)

    def handle_cluster_request(self, tsn, command_id, args):
        resp = args[0]
        if isinstance(resp, TuyaTRVCluster.Command) and resp.dp in ATTR_TO_EVENTS.keys():
            self.endpoint.device.data_bus.listener_event(
                ATTR_TO_EVENTS.get(resp.dp), resp.dp, resp.data)
        elif command_id == 36:
            self.endpoint.device.data_bus.listener_event(ATTR_TO_EVENTS.get(36), 36, resp)
        else:
            print('*'*100)
            print('Unsupported command {} : {}'.format(command_id, args))
            print('*'*100)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        for record in records:
            data_list = None
            if record.attrid in [103, 102]:
                datatype = 2
                value = round(record.value.value * 10)
                value_bytes = t.uint16_t(value).to_bytes(length=2, byteorder='big')
                data_list = [0, 0, value_bytes[0], value_bytes[1]]
            else:
                datatype = 1
                data_list = list(record.value.value.serialize())

            cmd_payload = TuyaTRVCluster.Command()
            cmd_payload.status = 0
            cmd_payload.transid = self.endpoint.device.application.get_sequence()
            cmd_payload.dp = record.attrid
            cmd_payload.datatype = datatype
            cmd_payload.length_hi = (len(data_list) >> 8) & 0xFF
            cmd_payload.length_lo = len(data_list) & 0xFF
            cmd_payload.data = data_list

            try:
                await super().command(
                    0x0000,
                    cmd_payload,
                    manufacturer=manufacturer,
                    expect_reply=False,
                )
            except futures.TimeoutError:
                pass

        return (foundation.Status.SUCCESS,)

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
        102: ("current_temperature", t.Single),
        103: ("heating_setpoint", t.Single),
        108: ("schedule_mode", ScheduleMode),
        101: ("system_mode", SystemMode),
        36: ("ping", t.CharacterString),
        123: (DAY_OF_WEEK.get(123), Schedule),
        124: (DAY_OF_WEEK.get(124), Schedule),
        125: (DAY_OF_WEEK.get(125), Schedule),
        126: (DAY_OF_WEEK.get(126), Schedule),
        127: (DAY_OF_WEEK.get(127), Schedule),
        128: (DAY_OF_WEEK.get(128), Schedule),
        129: (DAY_OF_WEEK.get(129), Schedule),
    }


class TuyaTRVUserInterfaceCluster(CustomCluster, UserInterface):
    """Danfoss custom cluster."""

    manufacturer_attributes = {
        102: ("current_temperature", t.Single),
        103: ("heating_setpoint", t.Single),
        108: ("schedule_mode", TuyaTRVCluster.ScheduleMode),
        101: ("system_mode", TuyaTRVCluster.SystemMode),
        36: ("ping", t.CharacterString),
    }

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
        MODELS_INFO: [('_TYST11_KGbxAXL2', "GbxAXL2")],
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
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                    homeautomation.ApplianceIdentification.cluster_id,
                    # general.Groups.cluster_id,
                    # general.Scenes.cluster_id,
                    # general.PollControl.cluster_id,
                    # general.DeviceTemperature,
                    # general.PowerConfiguration.cluster_id,
                    general.PowerProfile.cluster_id,
                    TuyaTRVCluster,
                    TuyaTRVUserInterfaceCluster,
                ],
                OUTPUT_CLUSTERS: [
                    general.Identify.cluster_id,
                    general.Ota.cluster_id],
            }
        }
    }
    device_automation_triggers = {
        # (SHORT_PRESS, TURN_ON): {
        #     COMMAND: COMMAND_TOGGLE,
        #     CLUSTER_ID: 6,
        #     ENDPOINT_ID: 1,
        # },
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: TuyaTRVCluster.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: [ON],
        },
    }
