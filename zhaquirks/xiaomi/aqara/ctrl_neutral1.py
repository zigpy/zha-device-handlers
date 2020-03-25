"""Xiaomi aqara single key wall switch devices."""
import logging

import zigpy.types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    DeviceTemperature,
    Time,
    BinaryOutput,
)

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)

DOUBLE = "double"
HOLD = "long press"
PRESS_TYPES = {0: "long press", 1: "single", 2: "double"}
SINGLE = "single"
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_CLUSTER_ID = 0xFFFF
XIAOMI_DEVICE_TYPE = 0x5F01
XIAOMI_DEVICE_TYPE2 = 0x5F02
XIAOMI_DEVICE_TYPE3 = 0x5F03

_LOGGER = logging.getLogger(__name__)

# click attr 0xF000
# single click 0x3FF1F00
# double click 0xCFF1F00


class XiaomiOnOffCluster(OnOff):

    attributes = {
        0x0000: ("on_off", t.Bool),
        0x4000: ("global_scene_control", t.Bool),
        0x4001: ("on_time", t.uint16_t),
        0x4002: ("off_wait_time", t.uint16_t),

        # 0xFF22: ("single", t.Bool),
        0xFF22: ("left", t.uint8_t),
        0xFF23: ("right", t.uint8_t),
    }

    server_commands = {
        0x0000: ("off", (), False),
        0x0001: ("on", (), False),
        # 0x0002: ("toggle", (), False),
        # 0x0040: ("off_with_effect", (t.uint8_t, t.uint8_t), False),
        # 0x0041: ("on_with_recall_global_scene", (), False),
        # 0x0042: ("on_with_timed_off", (t.uint8_t, t.uint16_t, t.uint16_t), False),
    }

    def command(self, command, *args, manufacturer=None, expect_reply=True):
        _LOGGER.debug('command: %s %s m:%s, r:%s', command, args, manufacturer, expect_reply)
        # traceback.print_stack()


        # return self.write_attributes({
        #     "left": 0x12,
        # }, manufacturer=manufacturer)

        return super().command(command, *args, manufacturer=manufacturer, expect_reply=expect_reply)

    def _update_attribute(self, attrid, value):
        _LOGGER.debug('_update_attribute: %s %s', attrid, value)
        super()._update_attribute(attrid, value)

    # def request(self, general, command_id, schema, *args, manufacturer=None, expect_reply=True):
    #     _LOGGER.debug('request: %s %s', general, command_id)
    #     return super().request(general, command_id, schema, *args, manufacturer=manufacturer,
    #                            expect_reply=expect_reply)

# 2020-03-15 20:22:39 DEBUG (MainThread) [homeassistant.core] Bus:Handling <Event call_service[L]:
#   domain=light, service=turn_off, service_data=
#       entity_id=light.ikea_of_sweden_tradfri_bulb_e27_w_opal_1000lm_b5adc2fe_level_on_off>
# 2020-03-15 20:22:39 DEBUG (MainThread) [zhaquirks.xiaomi.aqara.ctrl_neutral1] command: 0 () m:None, r:True
#   File "/home/sandor/.virtualenvs/homeassistant/bin/hass", line 11, in <module>
#     load_entry_point('homeassistant', 'console_scripts', 'hass')()
#   File "/home/sandor/repos/home-assistant/homeassistant/__main__.py", line 342, in main
#     exit_code = asyncio.run(setup_and_run_hass(config_dir, args))
#   File "/usr/lib/python3.7/asyncio/runners.py", line 43, in run
#     return loop.run_until_complete(main)
#   File "/usr/lib/python3.7/asyncio/base_events.py", line 566, in run_until_complete
#     self.run_forever()
#   File "/usr/lib/python3.7/asyncio/base_events.py", line 534, in run_forever
#     self._run_once()
#   File "/usr/lib/python3.7/asyncio/base_events.py", line 1771, in _run_once
#     handle._run()
#   File "/usr/lib/python3.7/asyncio/events.py", line 88, in _run
#     self._context.run(self._callback, *self._args)
#   File "/home/sandor/repos/home-assistant/homeassistant/components/zha/light.py", line 321, in async_turn_off
#     result = await self._on_off_channel.off()
#   File "/home/sandor/repos/home-assistant/homeassistant/components/zha/core/channels/base.py", line 53, in wrapper
#     result = await command(*args, **kwds)
#   File "/home/sandor/repos/zigpy/zha-device-handlers/zhaquirks/xiaomi/aqara/ctrl_neutral1.py", line 73, in command
#     traceback.print_stack()


# zigbee-herdsman:controller:endpoint Command 0x00158d00024be541/2 genOnOff.on({},
#   {"timeout":6000,"manufacturerCode":null,"disableDefaultResponse":false})
# zigbee-herdsman:adapter:zStack:znp:SREQ --> AF - dataRequest -
#   {"dstaddr":65311,"destendpoint":2,"srcendpoint":1,"clusterid":6,"transid":17,"options":0,"radius":30,"len":3,
#       "data":{"type":"Buffer","data":[1,8,1]}}
# zigbee-herdsman:adapter:zStack:unpi:writer -->frame [254,13,36,1,31,255,2,1,6,0,17,0,30,3,1,8,1,201]


# zigbee-herdsman:controller:endpoint Command 0x00158d00024be541/2 genOnOff.off({},
#   {"timeout":6000,"manufacturerCode":null,"disableDefaultResponse":false})
# zigbee-herdsman:adapter:zStack:znp:SREQ --> AF - dataRequest -
#   {"dstaddr":65311,"destendpoint":2,"srcendpoint":1,"clusterid":6,"transid":16,"options":0,"radius":30,"len":3,
#       "data":{"type":"Buffer","data":[1,7,0]}}
# zigbee-herdsman:adapter:zStack:unpi:writer --> frame [254,13,36,1,31,255,2,1,6,0,16,0,30,3,1,7,0,198]


class CtrlNeutral1(XiaomiCustomDevice):
    """Aqara single key switch device."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.ctrl_neutral1")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=2
            # input_clusters=[0, 3, 1, 2, 25, 10]
            # output_clusters=[0, 10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    DeviceTemperature.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Time.cluster_id, Ota.cluster_id,],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=256
            # device_version=2
            # input_clusters=[16, 6, 4, 5]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=256
            # device_version=2
            # input_clusters=[16, 6, 4, 5]
            # output_clusters=[]
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=5 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=6 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=8 profile=260 device_type=83
            # device_version=2
            # input_clusters=[12]
            # output_clusters=[]>
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [BasicCluster],
                OUTPUT_CLUSTERS: [],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [BasicCluster, XiaomiOnOffCluster],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    # device_automation_triggers = {
    #     (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: DOUBLE},
    #     (SHORT_PRESS, SHORT_PRESS): {COMMAND: SINGLE},
    #     (LONG_PRESS, LONG_PRESS): {COMMAND: HOLD},
    # }
