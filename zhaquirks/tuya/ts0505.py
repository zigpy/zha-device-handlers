"""Tuya based RGB+CCT Bulb."""
from typing import Any, List, Optional, Tuple, Union

import homeassistant.util.color as color_util

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color

from .. import Bus

from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

TUYA_BRIGHTNESS_ATTR = 0xF001
TUYA_MOVE_TO_HS = 0x0006
TUYA_RGB_MODE_ATTR = 0xF000
TUYA_RGB_MODE_ATTR_INT = 0xFFFF
TUYA_SET_RGB_MODE = 0x00F0

CT_ATTR = 0x0007
H_ATTR = 0x0000
LEVEL_ATTR = 0x0000
MOVE_TO_COLOR = 0x0007
MOVE_TO_CT = 0x000A
MOVE_TO_LEVEL = 0x0000
MOVE_TO_LEVEL_ONOFF = 0x0004
S_ATTR = 0x0001

class TuyaColorCluster(CustomCluster, Color):
    """Tuya Color cluster."""

    manufacturer_attributes = {
        TUYA_BRIGHTNESS_ATTR: ("tuya_brightness", t.uint16_t),
        TUYA_RGB_MODE_ATTR: ("tuya_rgb_mode", t.uint16_t),
    }

    manufacturer_server_commands = {
        TUYA_MOVE_TO_HS: ("tuya_move_to_hue_and_saturation", (t.uint8_t, t.uint8_t, t.uint16_t, t.uint8_t), False),
        TUYA_SET_RGB_MODE: ("tuya_rgb_mode", (t.uint16_t,), False),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.brightness_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        if attrid == CT_ATTR:
            super()._update_attribute(attrid, round(-1.36 * value + 500))
        elif attrid == H_ATTR:
            super()._update_attribute(attrid, round((value * 360) / 254))
        elif attrid == S_ATTR:
            super()._update_attribute(attrid, round(value / 2.54))
        elif attrid == TUYA_RGB_MODE_ATTR:
            self.endpoint.device.mode_bus.listener_event("mode_reported", value)
            super()._update_attribute(attrid, value)
        else:
            super()._update_attribute(attrid, value)

    def level_reported(self, value):
        """Level reported."""
        payload = list()
        payload.append(round((self._attr_cache.get(H_ATTR, 1) * 254) / 360))
        payload.append(round(self._attr_cache.get(S_ATTR, 1) * 2.54))
        payload.append(1500)
        payload.append(value)
        self.create_catching_task(super().command(TUYA_MOVE_TO_HS, *tuple(payload)))

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        if command_id == MOVE_TO_CT:
            payload = list(args)
            payload[0] = round(-0.734 * payload[0] + 367)
            self.create_catching_task(super().command(TUYA_SET_RGB_MODE, 0))
            self.endpoint.device.brightness_bus.listener_event("move_to_ct_brightness", self._attr_cache.get(TUYA_BRIGHTNESS_ATTR))
            return super().command(command_id, *tuple(payload))
        if command_id == MOVE_TO_COLOR:
            payload = list(args)
            hs_color = color_util.color_xy_to_hs(round(payload[0] / 65535, 3), round(payload[1] / 65535, 3))
            payload[0] = round((hs_color[0] * 254) / 360)
            payload[1] = round(hs_color[1] * 2.54)
            payload.append(self._attr_cache.get(TUYA_BRIGHTNESS_ATTR))
            self.create_catching_task(super().command(TUYA_SET_RGB_MODE, 1))
            return super().command(TUYA_MOVE_TO_HS, *tuple(payload))

        return super().command(command_id, *args)

class TuyaLevelControlCluster(CustomCluster, LevelControl):
    """Tuya LevelControl cluster."""

    manufacturer_attributes = {
        TUYA_RGB_MODE_ATTR_INT: ("tuya_rgb_mode_internal", t.uint16_t),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.brightness_bus.add_listener(self)
        self.endpoint.device.mode_bus.add_listener(self)

    def _update_attribute(self, attrid, value):
        if attrid == LEVEL_ATTR:
            self.endpoint.device.brightness_bus.listener_event("level_reported", value)
            super()._update_attribute(attrid, value)
        else:
            super()._update_attribute(attrid, value)

    def mode_reported(self, value):
        """Mode reported."""
        self._update_attribute(TUYA_RGB_MODE_ATTR_INT, value)

    def move_to_ct_brightness(self, value):
        """Move to CT adjust level."""
        self.create_catching_task(super().command(MOVE_TO_LEVEL, *(value, 1)))

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        if command_id == MOVE_TO_LEVEL_ONOFF:
            if self._attr_cache.get(TUYA_RGB_MODE_ATTR_INT) == 1:
                self._update_attribute(LEVEL_ATTR, list(args)[0])
                return foundation.Status.SUCCESS
            return await super().command(MOVE_TO_LEVEL, *args)

        return await super().command(command_id, *args)


class TuyaRGBCCTBulb(CustomDevice):
    """Tuya RGB+CCT Bulb"""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.brightness_bus = Bus()
        self.mode_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("_TZ3000_sosdczdl", "TS0505A")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Time.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaLevelControlCluster,
                    Time.cluster_id,
                    TuyaColorCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
