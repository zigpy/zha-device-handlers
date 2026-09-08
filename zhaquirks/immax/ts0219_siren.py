"""Map from manufacturer to standard clusters for the NEO Siren device."""

import logging
from typing import Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.security import IasWd, IasZone, StrobeLevel, WarningType

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)


class ImmaxIasWd(CustomCluster, IasWd):
    """Immax TS0219."""

    attributes = IasWd.attributes.copy()
    attributes.update(
        {
            0x0001: ("alarm_light", t.uint8_t, False),
            0x0002: ("alarm_radio", t.uint8_t, False),
            0x0003: ("disalarm", t.Bool, False),
            0xF000: ("custom", t.uint8_t, False),
        }
    )

    async def request(
        self,
        general: bool,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        schema: Union[dict, t.Struct],
        *args,
        manufacturer: Union[int, t.uint16_t, None] = None,
        expect_reply: bool = True,
        tsn: Union[int, t.uint8_t, None] = None,
        **kwargs,
    ):
        # skip Read_Attributes = 0x00
        if command_id == 0x00 and not isinstance(command_id, foundation.GeneralCommand):
            expect_reply = False  # fix sending 3 times

            warning = WarningType(args[0]) if len(args) > 0 else kwargs.get("warning")
            level = 1
            if warning.level == WarningType.SirenLevel.Low_level_sound:
                level = 1
            elif warning.level == WarningType.SirenLevel.Medium_level_sound:
                level = 15
            elif warning.level == WarningType.SirenLevel.High_level_sound:
                level = 30
            elif warning.level == WarningType.SirenLevel.Very_high_level_sound:
                level = 50

            duration = args[1] if len(args) > 0 else kwargs.get("warning_duration")

            strobe = (args[2] if len(args) > 0 else kwargs.get("strobe_duty_cycle")) > 0

            strobe_level = args[3] if len(args) > 0 else kwargs.get("stobe_level")
            if strobe_level == StrobeLevel.Low_level_strobe:
                strobe_level = 10
            elif strobe_level == StrobeLevel.Medium_level_strobe:
                strobe_level = 50
            elif strobe_level == StrobeLevel.High_level_strobe:
                strobe_level = 75
            elif strobe_level == StrobeLevel.Very_high_level_strobe:
                strobe_level = 100

            _LOGGER.debug(
                "siren start args duration=%s strobe=%s level=%s",
                duration,
                strobe_level,
                level,
            )
            await self.write_attributes(
                {
                    "max_duration": duration,
                    "alarm_light": strobe_level if strobe is True else 0,
                    "alarm_radio": level,
                }
            )

        return await super().request(
            general,
            command_id,
            schema,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


class ImmaxSirenTS0219(CustomDevice):
    """Immax Tuya Siren."""

    signature = {
        # "endpoints": {
        #     "1": {
        #       "profile_id": "0x0104",
        #       "device_type": "0x0403",
        #       "input_clusters": [
        #         "0x0000",
        #         "0x0001",
        #         "0x0003",
        #         "0x0004",
        #         "0x0005",
        #         "0x0500",
        #         "0x0502",
        #         "0xeeff"
        #       ],
        #       "output_clusters": [
        #         "0x0003",
        #         "0x0019"
        #       ]
        #     }
        #   },
        #   "manufacturer": "_TYZB01_b6eaxdlh",
        #   "model": "TS0219",
        #   "class": "zigpy.device.Device"
        MODELS_INFO: [("_TYZB01_b6eaxdlh", "TS0219")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005,
                    IasZone.cluster_id,  # 0x0500
                    IasWd.cluster_id,  # 0x0502
                    0xEEFF,  # Unknown
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                    Identify.cluster_id,  # 0x0003
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005,
                    IasZone.cluster_id,  # 0x0500
                    ImmaxIasWd,  # 0x0502
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                    Identify.cluster_id,  # 0x0003
                ],
            }
        },
    }
