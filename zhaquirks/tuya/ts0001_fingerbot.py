"""Tuya Fingerbot device."""

from typing import Any, Optional, Union

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TUYA_SEND_DATA, EnchantedDevice
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaMCUCluster,
    TuyaPowerConfigurationCluster,
)


class FingerBotMode(t.enum8):
    """FingerBot mode."""

    CLICK = 0x00
    SWITCH = 0x01
    PROGRAM = 0x02


class FingerBotReverse(t.enum8):
    """FingerBot reverse."""

    UP_ON = 0x00
    UP_OFF = 0x01


class TuyaFingerbotCluster(TuyaMCUCluster):
    """Tuya Fingerbot cluster."""

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """Attribute Definitions."""

        mode = foundation.ZCLAttributeDef(
            id=101, type=FingerBotMode, is_manufacturer_specific=True
        )
        down_movement = foundation.ZCLAttributeDef(
            id=102, type=t.uint16_t, is_manufacturer_specific=True
        )
        sustain_time = foundation.ZCLAttributeDef(
            id=103, type=t.uint16_t, is_manufacturer_specific=True
        )
        reverse = foundation.ZCLAttributeDef(
            id=104, type=FingerBotReverse, is_manufacturer_specific=True
        )
        battery = foundation.ZCLAttributeDef(
            id=105, type=t.uint16_t, is_manufacturer_specific=True
        )
        up_movement = foundation.ZCLAttributeDef(
            id=106, type=t.uint16_t, is_manufacturer_specific=True
        )
        touch_control = foundation.ZCLAttributeDef(
            id=107, type=t.Bool, is_manufacturer_specific=True
        )

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

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
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
        105: DPToAttributeMapping(
            TuyaPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
        # Up Movement
        106: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "up_movement",
        ),
        107: DPToAttributeMapping(TuyaMCUCluster.ep_attribute, "touch_control"),
    }

    data_point_handlers = {
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        106: "_dp_2_attr_update",
        107: "_dp_2_attr_update",
    }


class TuyaFingerbot(EnchantedDevice):
    """Tuya finger bot device."""

    signature = {
        MODELS_INFO: [("_TZ3210_dse8ogfy", "TS0001"), ("_TZ3210_j4pdtz9v", "TS0001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    OnOff.cluster_id,
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
                    TuyaPowerConfigurationCluster,
                    OnOff.cluster_id,
                    TuyaFingerbotCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
