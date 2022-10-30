"""Tuya Dimmer TS110E."""
from typing import Any, Optional, Union

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    NoManufacturerCluster,
    TuyaDimmerSwitch,
    TuyaZBExternalSwitchTypeCluster,
)

TUYA_LEVEL_ATTRIBUTE = 0xF000
TUYA_BULB_TYPE_ATTRIBUTE = 0xFC02
TUYA_MIN_LEVEL_ATTRIBUTE = 0xFC03
TUYA_MAX_LEVEL_ATTRIBUTE = 0xFC04
TUYA_CUSTOM_LEVEL_COMMAND = 0x00F0


class TuyaLevelPayload(t.Struct):
    """Tuya Level payload."""

    level: t.uint16_t
    transtime: t.uint16_t


class TuyaBulbType(t.enum8):
    """Tuya bulb type."""

    LED = 0x00
    INCANDESCENT = 0x01
    HALOGEN = 0x02


class F000LevelControlCluster(NoManufacturerCluster, LevelControl):
    """LevelControlCluster that reports to attrid 0xF000."""

    server_commands = LevelControl.server_commands.copy()
    server_commands[TUYA_CUSTOM_LEVEL_COMMAND] = foundation.ZCLCommandDef(
        "moveToLevelTuya",
        (TuyaLevelPayload,),
        is_manufacturer_specific=False,
    )

    attributes = LevelControl.attributes.copy()
    attributes.update(
        {
            # 0xF000
            TUYA_LEVEL_ATTRIBUTE: ("manufacturer_current_level", t.uint16_t),
            # 0xFC02
            TUYA_BULB_TYPE_ATTRIBUTE: ("bulb_type", TuyaBulbType),
            # 0xFC03
            TUYA_MIN_LEVEL_ATTRIBUTE: ("manufacturer_min_level", t.uint16_t),
            # 0xFC04
            TUYA_MAX_LEVEL_ATTRIBUTE: ("manufacturer_max_level", t.uint16_t),
        }
    )

    # 0xF000 reported values are 10-1000, convert to 0-254
    def _update_attribute(self, attrid, value):
        if attrid == TUYA_LEVEL_ATTRIBUTE:
            self.debug(
                "Getting brightness %s",
                value,
            )
            value = (value + 4 - 10) * 254 // (1000 - 10)
            attrid = 0x0000

        super()._update_attribute(attrid, value)

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
        self.debug(
            "Sending Cluster Command. Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )
        # move_to_level, move, move_to_level_with_on_off
        if command_id in (0x0000, 0x0001, 0x0004):
            # getting the level value
            if kwargs and "level" in kwargs:
                level = kwargs["level"]
            elif args:
                level = args[0]
            else:
                level = 0
            # convert dim values to 10-1000
            brightness = level * (1000 - 10) // 254 + 10
            self.debug(
                "Setting brightness to %s",
                brightness,
            )
            return await super().command(
                TUYA_CUSTOM_LEVEL_COMMAND,
                TuyaLevelPayload(level=brightness, transtime=0),
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )

        return super().command(
            command_id, *args, manufacturer, expect_reply, tsn, **kwargs
        )


class DimmerSwitchWithNeutral1Gang(TuyaDimmerSwitch):
    """Tuya Dimmer Switch Module With Neutral 1 Gang."""

    signature = {
        MODELS_INFO: [("_TZ3210_ngqk6jia", "TS110E")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=257
            # input_clusters=[0, 4, 5, 6, 8, 57345]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    F000LevelControlCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
