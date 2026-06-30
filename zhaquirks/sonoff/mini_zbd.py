"""Sonoff MINI-ZBD - Zigbee Switch with inching support."""

from typing import Any

from zigpy import types
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    DataTypeId,
    Status,
    WriteAttributesStatusRecord,
    ZCLAttributeDef,
)

from zhaquirks.builder import NumberDeviceClass, QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster


class SonoffExternalSwitchTriggerType(types.enum8):
    """External switch trigger type."""

    Edge_trigger = 0x00
    Pulse_trigger = 0x01
    Normally_off_follow_trigger = 0x02
    Normally_on_follow_trigger = 0x82


class SonoffInchingMode(types.enum8):
    """Inching mode: what happens after the timer expires."""

    Turn_OFF = 0x00  # Auto-off after turning on
    Turn_ON = 0x01  # Auto-on after turning off


class InchingPayload(t.Struct):
    """Protocol data payload for inching command (cluster 0xFC11, cmd 0x01)."""

    cmd: t.uint8_t
    subcmd: t.uint8_t
    length: t.uint8_t
    seqnum: t.uint8_t
    mode: t.uint8_t
    channel: t.uint8_t
    time_lo: t.uint8_t
    time_hi: t.uint8_t
    reserved1: t.uint8_t
    reserved2: t.uint8_t
    checksum: t.uint8_t


EWELINK_MANUFACTURER_CODE = 0x1286
PROTOCOL_DATA_COMMAND_ID = 0x01
INCHING_ATTR_NAMES = frozenset({"inching_control", "inching_time", "inching_mode"})


class SonoffCluster(CustomCluster):
    """Sonoff cluster 0xFC11 with inching support via protocolData command."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            manufacturer_code=None,
        )
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            manufacturer_code=None,
        )
        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=SonoffExternalSwitchTriggerType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        detach_relay = ZCLAttributeDef(
            id=0x0017,
            type=t.Bool,
            manufacturer_code=None,
        )
        # Virtual attributes for inching (intercepted in write_attributes)
        inching_control = ZCLAttributeDef(
            id=0x0050,
            type=t.Bool,
            manufacturer_code=None,
        )
        inching_time = ZCLAttributeDef(
            id=0x0051,
            type=t.uint16_t,
            manufacturer_code=None,
        )
        inching_mode = ZCLAttributeDef(
            id=0x0052,
            type=SonoffInchingMode,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[WriteAttributesStatusRecord]]:
        """Intercept inching attribute writes and send protocolData command."""
        regular_attrs = {}
        inching_changed = False

        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_name = attr_def.name

            if attr_name in INCHING_ATTR_NAMES:
                inching_changed = True
                self._update_attribute(attr_def.id, value)
            else:
                regular_attrs[attr] = value

        result = None

        if regular_attrs:
            result = await super().write_attributes(regular_attrs, **kwargs)

        if inching_changed:
            await self._send_inching_command()

        if result is None:
            result = [[WriteAttributesStatusRecord(status=Status.SUCCESS)]]

        return result

    async def _send_inching_command(self):
        """Build and send the protocolData payload for inching."""
        time_half_secs = int(self.get(self.AttributeDefs.inching_time.id, 2))

        mode = 0x00
        if self.get(self.AttributeDefs.inching_control.id, False):
            mode |= 0x80
        if self.get(self.AttributeDefs.inching_mode.id, 0):
            mode |= 0x01

        raw = [
            0x01,  # Cmd
            0x17,  # SubCmd (inching)
            0x07,  # Length
            0x80,  # SeqNum
            mode,
            0x00,  # Channel 1
            time_half_secs & 0xFF,
            (time_half_secs >> 8) & 0xFF,
            0x00,  # Reserved
            0x00,  # Reserved
        ]

        checksum = 0
        for b in raw:
            checksum ^= b

        await self.request(
            False,
            PROTOCOL_DATA_COMMAND_ID,
            InchingPayload,
            *raw,
            checksum,
            manufacturer=EWELINK_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("SONOFF", "MINI-ZBD")
    .replaces(SonoffCluster)
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        SonoffExternalSwitchTriggerType,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.turbo_mode.name,
        SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .switch(
        SonoffCluster.AttributeDefs.detach_relay.name,
        SonoffCluster.cluster_id,
        translation_key="detach_relay",
        fallback_name="Detach relay",
    )
    .switch(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffCluster.cluster_id,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .switch(
        SonoffCluster.AttributeDefs.inching_control.name,
        SonoffCluster.cluster_id,
        translation_key="inching_control",
        fallback_name="Inching",
    )
    .number(
        SonoffCluster.AttributeDefs.inching_time.name,
        SonoffCluster.cluster_id,
        min_value=0.5,
        max_value=3599.5,
        step=0.5,
        multiplier=0.5,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="inching_time",
        fallback_name="Inching time",
    )
    .enum(
        SonoffCluster.AttributeDefs.inching_mode.name,
        SonoffInchingMode,
        SonoffCluster.cluster_id,
        translation_key="inching_mode",
        fallback_name="Inching mode",
    )
    .add_to_registry()
)
