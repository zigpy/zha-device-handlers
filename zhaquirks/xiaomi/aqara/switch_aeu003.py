"""Quirk for Aqara Shutter Switch H2 EU (lumi.switch.aeu003)."""

import asyncio
import logging
from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

LOGGER: Final = logging.getLogger(__name__)

ATTR_ID: Final = "attr_id"
BUTTON: Final = "button"
BUTTON_3: Final = "button_3"
BUTTON_4: Final = "button_4"
COMMAND: Final = "command"
COMMAND_DOUBLE: Final = "double"
COMMAND_HOLD: Final = "hold"
COMMAND_RELEASE: Final = "release"
COMMAND_SINGLE: Final = "single"
PRESS_TYPE: Final = "press_type"
VALUE: Final = "value"
ZHA_SEND_EVENT: Final = "zha_send_event"

COMMAND_3_SINGLE: Final = "3_single"
COMMAND_3_DOUBLE: Final = "3_double"
COMMAND_3_HOLD: Final = "3_hold"
COMMAND_3_RELEASE: Final = "3_release"
COMMAND_4_SINGLE: Final = "4_single"
COMMAND_4_DOUBLE: Final = "4_double"
COMMAND_4_HOLD: Final = "4_hold"
COMMAND_4_RELEASE: Final = "4_release"

PRESS_TYPES: Final = {
    0: "hold",
    1: "single",
    2: "double",
    3: "triple",
    255: "release",
}
STATUS_TYPE_ATTR: Final = 0x0055


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster for button events."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    async def configure_reporting(
        self,
        attribute,
        min_interval,
        max_interval,
        reportable_change,
        manufacturer=None,
    ):
        """Configure reporting (unused)."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            self._current_state = PRESS_TYPES.get(value)
            event_args = {
                BUTTON: self.endpoint.endpoint_id,
                PRESS_TYPE: self._current_state,
                ATTR_ID: attrid,
                VALUE: value,
            }
            action = f"{self.endpoint.endpoint_id}_{self._current_state}"
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            # show something in the sensor in HA
            super()._update_attribute(0, action)


class AqaraOperationMode(t.enum8):
    """Aqara operation mode attribute values."""

    Decoupled = 0x00
    Relay = 0x01


class AqaraPowerOnMode(t.enum8):
    """Aqara power on mode attribute values."""

    On = 0x00
    Previous = 0x01
    Off = 0x02
    Inverted = 0x03




class AqaraManuSpecificCluster(CustomCluster):
    """Manufacturer-specific cluster for Aqara shutter switch features."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._movement_stopped: bool = False
        self._position_refresh_task: asyncio.Task | None = None
        super().__init__(*args, **kwargs)

    cluster_id: Final = 0xFCC0
    ep_attribute: Final = "opple_cluster"
    _MULTI_CLICK_ATTR: Final = 0x0286
    _Aqara_MFG_CODE: Final = 0x115F
    _RAW_POSITION_MASK: Final = 0xFF

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for Aqara shutter switch."""

        power_on_mode: Final = ZCLAttributeDef(
            id=0x0517,
            type=AqaraPowerOnMode,
            access="rw",
            is_manufacturer_specific=True,
        )
        operation_mode: Final = ZCLAttributeDef(
            id=0x0200,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        led_indicator: Final = ZCLAttributeDef(
            id=0x0203,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )
        flip_led_indicator: Final = ZCLAttributeDef(
            id=0x00F0,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )
        multi_click: Final = ZCLAttributeDef(
            id=0x0286,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        reverse_direction: Final = ZCLAttributeDef(
            id=0x0402,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )
        position_raw: Final = ZCLAttributeDef(
            id=0x00F5,
            type=t.uint32_t,
            access="r",
            is_manufacturer_specific=True,
        )
        position_percent: Final = ZCLAttributeDef(
            id=0x041F,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        """Log manufacturer-specific updates to help map attributes."""
        LOGGER.debug(
            "Aqara aeu003 mfg attr update: ep=%s attr=0x%04X value=%s",
            self.endpoint.endpoint_id,
            attrid,
            value,
        )
        if attrid == self.AttributeDefs.position_percent.id:
            try:
                pct = max(0, min(100, 100 - int(value)))
                if self._movement_stopped and pct in (0, 100):
                    pct = 50
                self.endpoint.window_covering.update_attribute(
                    WindowCovering.AttributeDefs.current_position_lift_percentage.id,
                    pct,
                )
                self.endpoint.window_covering.update_attribute(
                    WindowCovering.AttributeDefs.current_position_lift.id,
                    pct,
                )
            except Exception:  # noqa: BLE001 - best effort update
                LOGGER.debug("Failed to update lift percentage from percent value")
        if attrid in (0x0420, 0x0421):
            try:
                self._movement_stopped = value == 0
                self._position_refresh_task = asyncio.create_task(
                    self.read_attributes([self.AttributeDefs.position_percent.id])
                )
            except Exception:
                LOGGER.debug("Failed to refresh position on movement update")
        super()._update_attribute(attrid, value)

    async def bind(self):
        """Bind cluster and enable multi-click reporting.

        This device only emits double/hold/release once multi-click is enabled
        (write attribute 0x0286 = 2 with Aqara manufacturer code 0x115F) on
        endpoints 3 and 4.
        """
        result = await super().bind()
        if self.endpoint.endpoint_id in (3, 4):
            await self.write_attributes(
                {self._MULTI_CLICK_ATTR: 2}, manufacturer=self._Aqara_MFG_CODE
            )
        if self.endpoint.endpoint_id == 1:
            await self.read_attributes([self.AttributeDefs.position_percent.id])
        return result

    async def write_attributes(self, attributes, manufacturer=None):
        """Ensure Aqara manufacturer code is used for mfg-specific writes."""
        return await super().write_attributes(
            attributes, manufacturer=manufacturer or self._Aqara_MFG_CODE
        )

    async def read_attributes(self, attributes, manufacturer=None, **kwargs):
        """Ensure Aqara manufacturer code is used for mfg-specific reads."""
        return await super().read_attributes(
            attributes, manufacturer=manufacturer or self._Aqara_MFG_CODE, **kwargs
        )


(
    QuirkBuilder("Aqara", "lumi.switch.aeu003")
    .friendly_name(model="Shutter Switch H2", manufacturer="Aqara")
    .replaces(MultistateInputCluster, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(AqaraManuSpecificCluster, endpoint_id=1)
    .replaces(AqaraManuSpecificCluster, endpoint_id=2)
    .replaces(AqaraManuSpecificCluster, endpoint_id=3)
    .replaces(AqaraManuSpecificCluster, endpoint_id=4)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=WindowCovering.cluster_id,
        function=lambda entity: getattr(entity, "translation_key", None) == "inverted",
    )
    .command_button(
        command_name="up_open",
        cluster_id=WindowCovering.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.STANDARD,
        translation_key="force_open_cover",
        fallback_name="Force open cover",
    )
    .command_button(
        command_name="down_close",
        cluster_id=WindowCovering.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.STANDARD,
        translation_key="force_close_cover",
        fallback_name="Force close cover",
    )
    .command_button(
        command_name="stop",
        cluster_id=WindowCovering.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.STANDARD,
        translation_key="stop_cover",
        fallback_name="Force stop cover",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.multi_click.name,
        AqaraManuSpecificCluster.cluster_id,
        off_value=1,
        on_value=2,
        endpoint_id=3,
        translation_key="multi_click_button_3",
        fallback_name="Multi-click button 3",
        unique_id_suffix="button_3",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.multi_click.name,
        AqaraManuSpecificCluster.cluster_id,
        off_value=1,
        on_value=2,
        endpoint_id=4,
        translation_key="multi_click_button_4",
        fallback_name="Multi-click button 4",
        unique_id_suffix="button_4",
    )
    .sensor(
        AqaraManuSpecificCluster.AttributeDefs.position_raw.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="position_raw",
        fallback_name="Position raw",
    )
    .device_automation_triggers(
        {
            (COMMAND_HOLD, BUTTON_3): {COMMAND: COMMAND_3_HOLD},
            (COMMAND_SINGLE, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
            (COMMAND_DOUBLE, BUTTON_3): {COMMAND: COMMAND_3_DOUBLE},
            (COMMAND_RELEASE, BUTTON_3): {COMMAND: COMMAND_3_RELEASE},
            (COMMAND_HOLD, BUTTON_4): {COMMAND: COMMAND_4_HOLD},
            (COMMAND_SINGLE, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
            (COMMAND_DOUBLE, BUTTON_4): {COMMAND: COMMAND_4_DOUBLE},
            (COMMAND_RELEASE, BUTTON_4): {COMMAND: COMMAND_4_RELEASE},
        },
    )
    .add_to_registry()
)
