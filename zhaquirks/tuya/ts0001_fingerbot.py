from typing import Any, Dict, Optional, Union

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TUYA_SEND_DATA
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    EnchantedDevice,
    TuyaMCUCluster,
    TuyaOnOff,
)


class FingerBotMode(t.enum8):
    CLICK = 0x00
    SWITCH = 0x01
    PROGRAM = 0x02


class FingerBotReverse(t.enum8):
    UP_ON = 0x00
    UP_OFF = 0x01


class TuyaFingerbotCluster(TuyaMCUCluster):
    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update({101: ("mode", FingerBotMode)})
    attributes.update({102: ("down_movement", t.uint16_t)})
    attributes.update({103: ("sustain_time", t.uint16_t)})
    attributes.update({104: ("reverse", FingerBotReverse)})
    attributes.update({105: ("battery", t.uint16_t)})
    attributes.update({106: ("up_movement", t.uint16_t)})
    attributes.update({107: ("touch_control", t.Bool)})

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
        **kwargs: Any,
    ):
        """Override the default Cluster command."""

        return await super().command(
            TUYA_SEND_DATA,
            *args,
            manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(TuyaOnOff.ep_attribute, "on_off"),
        # Mode
        101: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "mode",
            converter=lambda x: FingerBotMode(x),
        ),
        # Down Movement
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "down_movement",
        ),
        # Sustain Time
        103: DPToAttributeMapping(TuyaMCUCluster.ep_attribute, "sustain_time"),
        # Reverse
        104: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "reverse",
            converter=lambda x: FingerBotReverse(x),
        ),
        # Battery
        105: DPToAttributeMapping(TuyaMCUCluster.ep_attribute, "battery"),
        # Up Movement
        106: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "up_movement",
        ),
        107: DPToAttributeMapping(TuyaMCUCluster.ep_attribute, "touch_control"),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        106: "_dp_2_attr_update",
        107: "_dp_2_attr_update",
    }


class TuyaFingerbot(EnchantedDevice):
    signature = {
        MODELS_INFO: [("_TZ3210_dse8ogfy", "TS0001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaOnOff.cluster_id,
                    TuyaFingerbotCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaOnOff,
                    TuyaFingerbotCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
