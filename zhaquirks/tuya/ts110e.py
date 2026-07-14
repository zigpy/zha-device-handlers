"""Tuya Dimmer TS110E."""

from typing import Any, Final, Union

from zigpy.profiles import zgp, zha
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
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
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
# on some variants (e.g. _TZ3210_k1msuvg6) attribute 0xFC02 holds the
# external switch type instead of the bulb type, matching the Zigbee2MQTT
# TS110E_options/TS110E_switch_type converters
TUYA_SWITCH_TYPE_ATTRIBUTE = 0xFC02
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

    class ServerCommandDefs(LevelControl.ServerCommandDefs):
        """Server command definitions."""

        moveToLevelTuya = foundation.ZCLCommandDef(  # noqa: N815
            id=TUYA_CUSTOM_LEVEL_COMMAND,
            schema={"payload": TuyaLevelPayload},
            is_manufacturer_specific=False,
        )

    class AttributeDefs(LevelControl.AttributeDefs):
        """Attribute definitions."""

        # 0xF000
        manufacturer_current_level: Final = ZCLAttributeDef(
            id=TUYA_LEVEL_ATTRIBUTE, type=t.uint16_t
        )
        # 0xFC02
        bulb_type: Final = ZCLAttributeDef(
            id=TUYA_BULB_TYPE_ATTRIBUTE, type=TuyaBulbType
        )
        # 0xFC03
        manufacturer_min_level: Final = ZCLAttributeDef(
            id=TUYA_MIN_LEVEL_ATTRIBUTE, type=t.uint16_t
        )
        # 0xFC04
        manufacturer_max_level: Final = ZCLAttributeDef(
            id=TUYA_MAX_LEVEL_ATTRIBUTE, type=t.uint16_t
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
        manufacturer: Union[int, t.uint16_t] | None = None,
        expect_reply: bool = True,
        tsn: Union[int, t.uint8_t] | None = None,
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


class TS110EExternalSwitchType(t.enum8):
    """External switch type attached to the dimmer.

    Values match the Zigbee2MQTT ``TS110E_options`` converter
    (``genLevelCtrl`` attribute 64514).
    """

    Momentary = 0x00
    Toggle = 0x01
    State = 0x02


class TS110EStateGuardMixin:
    """Workarounds for the desynced internal MCU of some TS110E dimmers.

    The internal Tuya MCU of the ``_TZ3210_k1msuvg6`` dimmer desyncs from the
    actual output state:

    * Reading ``on_off``/``current_level`` returns the stale MCU state
      (typically "on at 1%") regardless of reality, so reads of those
      attributes are answered from the attribute cache instead of the device.
    * The periodic unsolicited reports the device sends (roughly every 15
      minutes) carry the same stale values. They can be told apart from
      genuine reports (physical switch presses and echoes of received
      commands): the stale reports have ``disable_default_response=1`` in
      the ZCL frame control, genuine reports have it unset. The stale
      reports are dropped.
    """

    CACHE_ONLY_READ_ATTRIBUTES = frozenset()

    def _read_is_cache_only(self, attr) -> bool:
        """Return whether reading this attribute must not hit the device."""
        if isinstance(attr, str):
            attr_def = self.attributes_by_name.get(attr)
            return (
                attr_def is not None and attr_def.id in self.CACHE_ONLY_READ_ATTRIBUTES
            )
        return attr in self.CACHE_ONLY_READ_ATTRIBUTES

    async def read_attributes(
        self,
        attributes: list[int | str | ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Serve reads of the desynced state attributes from the cache."""
        if any(self._read_is_cache_only(attr) for attr in attributes):
            self.debug("Serving read of %s from the attribute cache", attributes)
            allow_cache = True
            only_cache = True
        return await super().read_attributes(
            attributes, allow_cache=allow_cache, only_cache=only_cache, **kwargs
        )

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Drop the periodic reports carrying the stale MCU state."""
        if (
            hdr.command_id == foundation.GeneralCommand.Report_Attributes
            and hdr.frame_control.disable_default_response
        ):
            self.debug("Dropping report with stale MCU state: %s", args)
            return
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


class TS110EOnOffCluster(TS110EStateGuardMixin, NoManufacturerCluster, OnOff):
    """OnOff cluster for TS110E dimmers with a desynced internal MCU."""

    CACHE_ONLY_READ_ATTRIBUTES = frozenset({OnOff.AttributeDefs.on_off.id})

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid != OnOff.AttributeDefs.on_off.id or not value:
            return

        # The device never reports a usable current_level on its own, so the
        # brightness is unknown until it is set through Zigbee at least once.
        # If the light turns on before that happened (physical switch press
        # after a fresh pairing), force full brightness onto the device so
        # Home Assistant and the light stay in sync.
        level_cluster = getattr(self.endpoint, LevelControl.ep_attribute, None)
        if (
            level_cluster is None
            or level_cluster.get(LevelControl.AttributeDefs.current_level.id)
            is not None
        ):
            return

        self.debug("Turned on with unknown brightness, forcing full brightness")
        level_cluster.update_attribute(LevelControl.AttributeDefs.current_level.id, 254)
        self.create_catching_task(
            level_cluster.command(
                LevelControl.ServerCommandDefs.move_to_level_with_on_off.id,
                level=254,
                transition_time=1,
            )
        )


class TS110ELevelControlCluster(
    TS110EStateGuardMixin, NoManufacturerCluster, LevelControl
):
    """LevelControl cluster for TS110E dimmers with a desynced internal MCU."""

    CACHE_ONLY_READ_ATTRIBUTES = frozenset(
        {LevelControl.AttributeDefs.current_level.id}
    )

    class AttributeDefs(LevelControl.AttributeDefs):
        """Attribute definitions."""

        # 0xFC02, the bulb type on other TS110E variants
        external_switch_type: Final = ZCLAttributeDef(
            id=TUYA_SWITCH_TYPE_ATTRIBUTE, type=TS110EExternalSwitchType
        )

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Union[int, t.uint16_t] | None = None,
        expect_reply: bool = True,
        tsn: Union[int, t.uint8_t] | None = None,
        **kwargs: Any,
    ):
        """Send an explicit on() before switching on via a level command.

        When the light is turned on with just move_to_level_with_on_off, the
        physical switch cannot turn it off afterwards, see
        https://github.com/Koenkk/zigbee2mqtt/issues/15902
        """
        if command_id == self.ServerCommandDefs.move_to_level_with_on_off.id:
            level = kwargs["level"] if "level" in kwargs else args[0] if args else None
            if level:
                await self.endpoint.on_off.on()
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


(
    QuirkBuilder("_TZ3210_k1msuvg6", "TS110E")
    .replaces(TS110EOnOffCluster)
    .replaces(TS110ELevelControlCluster)
    .enum(
        attribute_name=TS110ELevelControlCluster.AttributeDefs.external_switch_type.name,
        enum_class=TS110EExternalSwitchType,
        cluster_id=TS110ELevelControlCluster.cluster_id,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
