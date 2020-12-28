"""Module to handle quirks of the  Zen Within thermostat."""
import asyncio
import logging
from time import sleep
from typing import Union, Optional, List, Dict, Any

import zigpy.profiles.zha as zha_p
from zhaquirks import LocalDataCluster, Bus
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters import general
import zigpy.types as t
from zigpy.zcl import foundation
from . import TuyaManufCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID, SKIP_CONFIGURATION, CLUSTER_ID, COMMAND, SHORT_PRESS, TURN_ON, COMMAND_TOGGLE, ENDPOINT_ID, LONG_PRESS,
    COMMAND_RELEASE, ARGS,
)

SITERWELL_CHILD_LOCK_ATTR = 0x0107  # [0] unlocked [1] child-locked
SITERWELL_WINDOW_OPEN_ATTR = 0x0112  # [0] window closed [1] window open detected
SITERWELL_VALVE_STATE_ATTR = 0x0114  # [0] valve closed [1] valve open
SITERWELL_TARGET_TEMP_ATTR = 0x0202  # [0,0,0,210] target room temp (decidegree)
SITERWELL_TEMPERATURE_ATTR = 0x0203  # [0,0,0,200] current room temp (decidegree)
SITERWELL_BATTERY_ATTR = 0x0215  # [0,0,0,98] battery charge
SITERWELL_MODE_ATTR = 0x0404  # [0] off [1] auto [2] heat

_LOGGER = logging.getLogger(__name__)


ATTR_TO_EVENTS = {
    101: 'power_reported',
    102: 'current_temp_reported',
    103: 'heating_setpoint_reported',
    108: 'mode_reported',
    123: 'schedule_day_1',
    124: 'schedule_day_2',
    125: 'schedule_day_3',
    126: 'schedule_day_4',
    127: 'schedule_day_5',
    128: 'schedule_day_6',
    129: 'schedule_day_7',
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
    """"""


class A(LocalDataCluster, ManufacturerSpecificCluster):
    cluster_id = 0xEF00
    name = 'Tuya manufacturer cluster'
    ep_attribute = "tuya_manufacturer"

    class Command(t.Struct):
        """Tuya manufacturer cluster command."""

        status: t.int8s
        transid: t.int8s
        dp: t.uint8_t
        datatype: t.uint8_t
        function: t.uint8_t
        data: Data

    class SetDataCommand(t.Struct):
        """Tuya manufacturer cluster command."""

        status: t.int8s
        transid: t.int8s
        dp: t.uint8_t
        datatype: t.uint8_t
        length_hi: t.uint8_t
        length_lo: t.uint8_t
        data: Data

    class SetTimeCommand(t.Struct):
        """Tuya manufacturer cluster command."""

        payload_size: t.uint16_t
        payload: t.Optional(t.uint16_t)

        @classmethod
        def deserialize(cls, data):
            if len(data) >= 2:
                return super().deserialize(data)
            else:
                print(data)

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.heating_setpoint_bus.add_listener(self)
        self.endpoint.device.current_temp_bus.add_listener(self)
        self.endpoint.device.power_bus.add_listener(self)
        self.endpoint.device.mode_bus.add_listener(self)

    def schedule_day_1(self, value):
        self._update_attribute(123, value)

    def power_reported(self, value):
        self._update_attribute(101, value[1])

    def mode_reported(self, value):
        self._update_attribute(108, value[1])

    def current_temp_reported(self, value):
        tempr = self.convert_to_temperature(value)
        self._update_attribute(102, tempr)

    def heating_setpoint_reported(self, value):
        tempr = self.convert_to_temperature(value)
        self._update_attribute(103, tempr)

    @staticmethod
    def convert_to_temperature(value):
        data_b = value[3].to_bytes(length=1, byteorder='big')
        data_b += value[4].to_bytes(length=1, byteorder='big')
        tempr = int.from_bytes(data_b, byteorder='big', signed=False) / 10
        return tempr

    def handle_cluster_request(self, tsn, command_id, args):
        resp = args[0]
        if isinstance(resp, A.Command) and resp.dp in ATTR_TO_EVENTS.keys() :
            self.endpoint.device.power_bus.listener_event(
                ATTR_TO_EVENTS.get(resp.dp), resp.data)
        else:
            print('*'*100)
            print('Unsupported command {} : {}'.format(command_id, args))
            print('*'*100)

    # def command(
    #         self,
    #         command_id: Union[foundation.Command, int, t.uint8_t],
    #         *args,
    #         manufacturer: Optional[Union[int, t.uint16_t]] = None,
    #         expect_reply: bool = True,
    #         tsn: Optional[Union[int, t.uint8_t]] = None,
    # ):
    #     """Override the default Cluster command."""
    #     # if command_id in ATTR_TO_EVENTS.keys():
    #     data = bytes(220)
    #     cmd_payload = A.SetDataCommand()
    #     cmd_payload.status = 0
    #     cmd_payload.transid = self.endpoint.device.application.get_sequence() + 1
    #     cmd_payload.dp = 103
    #     cmd_payload.datatype = 2
    #     cmd_payload.length_hi = (len(data) >> 8) & 0xFF
    #     cmd_payload.length_lo = len(data) & 0xFF
    #     cmd_payload.data = [data]
    #
    #     return self.endpoint.tuya_manufacturer.command(
    #         0x0000, cmd_payload, expect_reply=True
    #     )
    #
    #     # return foundation.Status.UNSUP_CLUSTER_COMMAND

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        for record in records:
            # serialized in little-endian
            data = list(record.value.value.serialize())
            # we want big-endian, with length prepended
            data.append(len(data))
            data.reverse()
            #
            # cmd_payload = TuyaManufCluster.Command()
            # cmd_payload.status = 0
            # cmd_payload.tsn = self.endpoint.device.application.get_sequence()
            # cmd_payload.command_id = record.attrid
            # cmd_payload.function = 0
            # cmd_payload.data = data

            cmd_payload = A.SetDataCommand()
            cmd_payload.status = 0
            cmd_payload.transid = self.endpoint.device.application.get_sequence() + 1
            cmd_payload.dp = record.attrid
            cmd_payload.datatype = 2
            cmd_payload.length_hi = (len(data) >> 8) & 0xFF
            cmd_payload.length_lo = len(data) & 0xFF
            cmd_payload.data = data

        aaa = await super().command(
                0x0000,
                cmd_payload,
                manufacturer=manufacturer,
                expect_reply=False,
            )

        return (foundation.Status.SUCCESS,)


        # data = args[0]
        # if isinstance(data, A.Command):
        #     self._update_attribute(data.dp, data.data[len(data.data)-1])
        # data = bytes(22)
        # cmd_payload = A.SetDataCommand()
        # cmd_payload.status = 0
        # cmd_payload.transid = tsn + 1
        # cmd_payload.dp = 103
        # cmd_payload.datatype = 2
        # cmd_payload.length_hi = (len(data) >> 8) & 0xFF
        # cmd_payload.length_lo = len(data) & 0xFF
        # cmd_payload.data = data
        # loop = asyncio.get_event_loop()
        # data = self.endpoint.tuya_manufacturer.command(
        #     0x0000,  *cmd_payload.as_dict().values(), expect_reply=True)
        # res = loop.create_task(data)
        # while not res.done():
        #     sleep(3)
        # print(res.result())

    manufacturer_client_commands = {
        0x0001: ("get_data", (SetTimeCommand,), True),
        0x0002: ("set_data_response", (Command,), True),
        # 0x8a06: ("set_time", (t.uint8_t, t.uint8_t), True),
        # 0x0024: ("s", (SetTimeCommand,), True),

    }

    manufacturer_server_commands = {
        0x0000: ("set_data", (SetDataCommand,), False),
        0x0001: ("get_data", (Command,), True),
        0x0024: ("set_time", (SetTimeCommand,), True),
    }

    manufacturer_attributes = {
        102: ("current_temp", t.Single),
        103: ("heating_setpoint", t.Single),
        108: ("mode", t.uint8_t),
        101: ("power", t.uint8_t),

        # 105: ("battery", t.uint8_t),
        # 104: ("valve_pos", t.uint8_t),
    }



class TuyaThermostat1(CustomDevice):
    """Tuya Within  Sasswell Thermostat custom device.
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
        self.current_temp_bus = Bus()
        self.heating_setpoint_bus = Bus()
        self.power_bus = Bus()
        self.mode_bus = Bus()
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
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                    # general.Groups.cluster_id,
                    # general.Scenes.cluster_id,
                    # general.PollControl.cluster_id,
                    # general.DeviceTemperature,
                    # general.PowerConfiguration.cluster_id,
                    # general.PowerProfile.cluster_id,
                    A,
                ],
                OUTPUT_CLUSTERS: [
                    general.Identify.cluster_id,
                    general.Ota.cluster_id],
            }
        }
    }
    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
        },
        (LONG_PRESS, TURN_ON): {
            COMMAND: COMMAND_RELEASE,
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
    }
