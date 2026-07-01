"""Tuya MCU communications."""

from __future__ import annotations

from collections.abc import Callable
import datetime
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import Bus, DoublingPowerConfigurationCluster

# add EnchantedDevice import for custom quirks backwards compatibility
from zhaquirks.tuya import (
    TUYA_MCU_COMMAND,
    TUYA_MCU_VERSION_RSP,
    TUYA_SET_TIME,
    DPToAttributeMapping as DpToAttributeMappingBase,
    EnchantedDevice,  # noqa: F401
    NoManufacturerCluster,
    PowerOnState,
    TuyaCommand,
    TuyaDatapointData,
    TuyaLocalCluster,
    TuyaNewManufCluster,
    TuyaTimePayload,
)

# New manufacturer attributes
ATTR_MCU_VERSION = 0xEF00

# manufacturer commands
TUYA_MCU_CONNECTION_STATUS = 0x25


class DPToAttributeMapping(DpToAttributeMappingBase):
    """Container for datapoint to cluster attribute update mapping."""

    def __init__(
        self,
        ep_attribute: str,
        attribute_name: str | tuple[str, ...],
        converter: Callable[[Any], Any] | None = None,
        dp_converter: Callable[[Any], Any] | None = None,
        endpoint_id: int | None = None,
    ):
        """Init method for compatibility with previous quirks using positional arguments."""
        super().__init__(ep_attribute, attribute_name, converter, endpoint_id)
        self.dp_converter = dp_converter


class TuyaClusterData(t.Struct):
    """Tuya cluster data."""

    endpoint_id: int
    cluster_name: str
    cluster_attr: str
    attr_value: int  # Maybe also others types?
    expect_reply: bool
    manufacturer: int


class MoesBacklight(t.enum8):
    """MOES switch backlight mode enum."""

    off = 0x00
    light_when_on = 0x01
    light_when_off = 0x02
    freeze = 0x03


class TuyaPowerConfigurationCluster(
    TuyaLocalCluster, DoublingPowerConfigurationCluster
):
    """PowerConfiguration cluster for battery-operated tuya devices reporting percentage."""


class TuyaAttributesCluster(TuyaLocalCluster):
    """Manufacturer specific cluster for Tuya converting attributes <-> commands."""

    async def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Ignore remote reads as the "get_data" command doesn't seem to do anything."""

        self.debug("read_attributes --> attrs: %s", attributes)
        return await super().read_attributes(
            attributes, allow_cache=True, only_cache=True, manufacturer=manufacturer
        )

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        await super().write_attributes(attributes, manufacturer)

        records = self._write_attr_records(attributes)

        for record in records:
            self.debug("write_attributes --> record: %s", record)

            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr=self.attributes[record.attrid].name,
                attr_value=record.value.value,
                expect_reply=False,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class MCUVersion(t.Struct):
    """Tuya MCU version response Zcl payload."""

    status: t.uint8_t
    tsn: t.uint8_t
    version_raw: t.uint8_t

    @property
    def version(self) -> str:
        """Format the raw version to X.Y.Z."""

        if self.version_raw:
            # MCU version is 1 byte length
            # is converted from HEX -> BIN -> XX.XX.XXXX -> DEC (x.y.z)
            # example: 0x98 -> 10011000 -> 10.01.1000 -> 2.1.8
            # https://developer.tuya.com/en/docs/iot-device-dev/firmware-version-description?id=K9zzuc5n2gff8#title-1-Zigbee%20firmware%20versions
            major = self.version_raw >> 6
            minor = (self.version_raw & 63) >> 4
            release = self.version_raw & 15

            return f"{major}.{minor}.{release}"

        return None


class TuyaConnectionStatus(t.Struct):
    """Tuya connection status data."""

    tsn: t.uint8_t
    status: t.LVBytes


class TuyaMCUCluster(TuyaAttributesCluster, TuyaNewManufCluster):
    """Manufacturer specific cluster for sending Tuya MCU commands."""

    set_time_offset = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
    set_time_local_offset = datetime.datetime(1970, 1, 1)

    # TODO: Backwards compatibility, remove
    MCUVersion = MCUVersion
    TuyaConnectionStatus = TuyaConnectionStatus

    class AttributeDefs(TuyaNewManufCluster.AttributeDefs):
        """Attribute Definitions."""

        mcu_version = foundation.ZCLAttributeDef(
            id=ATTR_MCU_VERSION,
            type=t.uint48_t,
            access=foundation.ZCLAttributeAccess.Read,
            is_manufacturer_specific=True,
        )

    class ClientCommandDefs(TuyaNewManufCluster.ClientCommandDefs):
        """Client command definitions."""

        mcu_version_response = foundation.ZCLCommandDef(
            id=TUYA_MCU_VERSION_RSP,
            schema={"version": MCUVersion},
            is_manufacturer_specific=True,
        )
        mcu_connection_status = foundation.ZCLCommandDef(
            id=TUYA_MCU_CONNECTION_STATUS,
            schema={"payload": TuyaConnectionStatus},
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(TuyaNewManufCluster.ServerCommandDefs):
        """Server command definitions."""

        mcu_connection_status_rsp = foundation.ZCLCommandDef(
            id=TUYA_MCU_CONNECTION_STATUS,
            schema={"payload": TuyaConnectionStatus},
            is_manufacturer_specific=True,
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # Cluster for endpoint: 1 (listen MCU commands)
        self.endpoint.device.command_bus = Bus()
        self.endpoint.device.command_bus.add_listener(self)

    def from_cluster_data(self, data: TuyaClusterData) -> list[TuyaCommand]:
        """Convert from cluster data to a tuya data payload."""

        dp_mapping = self.get_dp_mapping(data.endpoint_id, data.cluster_attr)
        self.debug("from_cluster_data: %s", dp_mapping)
        if len(dp_mapping) == 0:
            self.warning(
                "No cluster_dp found for %s, %s",
                data.endpoint_id,
                data.cluster_attr,
            )
            return []

        tuya_commands: list[TuyaCommand] = []
        for dp, mapping in dp_mapping.items():
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()

            val = data.attr_value
            if mapping.dp_converter:
                args = []
                if isinstance(mapping.attribute_name, tuple):
                    endpoint = self.endpoint
                    if mapping.endpoint_id:
                        endpoint = endpoint.device.endpoints[mapping.endpoint_id]
                    cluster = getattr(endpoint, mapping.ep_attribute)
                    for attr in mapping.attribute_name:
                        args.append(
                            val if attr == data.cluster_attr else cluster.get(attr)
                        )
                else:
                    args.append(val)
                val = mapping.dp_converter(*args)
            self.debug("value: %s", val)

            dpd = TuyaDatapointData(dp, val)
            self.debug("raw: %s", dpd.data.raw)
            cmd_payload.datapoints = t.List([dpd])

            tuya_commands.append(cmd_payload)
        return tuya_commands

    def tuya_mcu_command(self, cluster_data: TuyaClusterData):
        """Tuya MCU command listener. Only manufacturer endpoint must listen to MCU commands."""

        self.debug(
            "tuya_mcu_command: cluster_data=%s",
            cluster_data,
        )

        tuya_commands = self.from_cluster_data(cluster_data)
        self.debug("tuya_commands: %s", tuya_commands)
        if len(tuya_commands) == 0:
            self.warning(
                "no MCU command for data %s",
                cluster_data,
            )
            return

        for tuya_command in tuya_commands:
            self.create_catching_task(
                self.command(
                    self.mcu_write_command,
                    tuya_command,
                    expect_reply=cluster_data.expect_reply,
                    manufacturer=cluster_data.manufacturer,
                )
            )

        endpoint = self.endpoint.device.endpoints[cluster_data.endpoint_id]
        cluster = getattr(endpoint, cluster_data.cluster_name)
        cluster.update_attribute(cluster_data.cluster_attr, cluster_data.attr_value)

    def get_dp_mapping(
        self, endpoint_id: int, attribute_name: str
    ) -> dict[int, DPToAttributeMapping]:
        """Search for the DP in _dp_to_attributes."""

        result: dict[int, DPToAttributeMapping] = {}
        for dp, dp_mapping in self._dp_to_attributes.items():
            for mapped_attr in dp_mapping:
                if (
                    attribute_name == mapped_attr.attribute_name
                    or (
                        isinstance(mapped_attr.attribute_name, tuple)
                        and attribute_name in mapped_attr.attribute_name
                    )
                ) and (
                    (
                        mapped_attr.endpoint_id is None
                        and endpoint_id == self.endpoint.endpoint_id
                    )
                    or (endpoint_id == mapped_attr.endpoint_id)
                ):
                    self.debug("get_dp_mapping --> found DP: %s", dp)
                    result[dp] = mapped_attr
        return result

    def handle_mcu_version_response(self, payload: MCUVersion) -> foundation.Status:  # type:ignore[valid-type]
        """Handle MCU version response."""

        self.debug("MCU version: %s", payload.version)
        self.update_attribute("mcu_version", payload.version)
        return foundation.Status.SUCCESS

    def handle_set_time_request(self, payload: t.uint16_t) -> foundation.Status:
        """Handle set_time requests (0x24)."""

        self.debug("handle_set_time_request payload: %s", payload)
        payload_rsp = TuyaTimePayload()

        utc_timestamp = int(
            (datetime.datetime.now(datetime.UTC) - self.set_time_offset).total_seconds()
        )
        local_timestamp = int(
            (datetime.datetime.now() - self.set_time_local_offset).total_seconds()
        )

        payload_rsp.extend(utc_timestamp.to_bytes(4, "big", signed=False))
        payload_rsp.extend(local_timestamp.to_bytes(4, "big", signed=False))

        self.debug("handle_set_time_request response: %s", payload_rsp)
        self.create_catching_task(
            super().command(TUYA_SET_TIME, payload_rsp, expect_reply=False)
        )

        return foundation.Status.SUCCESS

    def handle_mcu_connection_status(
        self,
        payload: TuyaConnectionStatus,  # type:ignore[valid-type]
    ) -> foundation.Status:
        """Handle gateway connection status requests (0x25)."""

        payload_rsp = TuyaMCUCluster.TuyaConnectionStatus()
        payload_rsp.tsn = payload.tsn
        payload_rsp.status = b"\x01"  # 0x00 not connected to internet | 0x01 connected to internet | 0x02 time out

        self.create_catching_task(
            super().command(TUYA_MCU_CONNECTION_STATUS, payload_rsp, expect_reply=False)
        )

        return foundation.Status.SUCCESS


class TuyaOnOff(OnOff, TuyaLocalCluster):
    """Tuya MCU OnOff cluster."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Cluster attributes."""

    class ServerCommandDefs(OnOff.ServerCommandDefs):
        """Server command definitions."""

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ):
        """Override the default Cluster command."""

        self.debug(
            "Sending Tuya Cluster Command... Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )

        # (off, on)
        if command_id in (0x0000, 0x0001):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr="on_off",
                attr_value=bool(command_id),
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class TuyaOnOffNM(NoManufacturerCluster, TuyaOnOff):
    """Tuya OnOff cluster with NoManufacturerID."""


class TuyaOnOffManufCluster(TuyaMCUCluster):
    """Tuya with On/Off data points."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        2: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=2,
        ),
        3: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=3,
        ),
        4: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=4,
        ),
        5: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=5,
        ),
        6: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=6,
        ),
        0x65: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=7,
        ),
        0x66: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=8,
        ),
        0x67: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=9,
        ),
        0x68: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=10,
        ),
        0x69: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=11,
        ),
        0x6A: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=12,
        ),
        0x6B: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=13,
        ),
        0x6C: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=14,
        ),
        0x6D: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=15,
        ),
        0x6E: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=16,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        0x65: "_dp_2_attr_update",
        0x66: "_dp_2_attr_update",
        0x67: "_dp_2_attr_update",
        0x68: "_dp_2_attr_update",
        0x69: "_dp_2_attr_update",
        0x6A: "_dp_2_attr_update",
        0x6B: "_dp_2_attr_update",
        0x6C: "_dp_2_attr_update",
        0x6D: "_dp_2_attr_update",
        0x6E: "_dp_2_attr_update",
    }


class MoesSwitchManufCluster(TuyaOnOffManufCluster):
    """On/Off Tuya cluster with extra device attributes."""

    class AttributeDefs(TuyaOnOffManufCluster.AttributeDefs):
        """Attribute definitions."""

        backlight_mode: Final = ZCLAttributeDef(id=0x8001, type=MoesBacklight)
        power_on_state: Final = ZCLAttributeDef(id=0x8002, type=PowerOnState)

    dp_to_attribute: dict[int, DPToAttributeMapping] = (
        TuyaOnOffManufCluster.dp_to_attribute.copy()
    )
    dp_to_attribute.update(
        {
            14: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "power_on_state",
                converter=lambda x: PowerOnState(x),
            )
        }
    )
    dp_to_attribute.update(
        {
            15: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "backlight_mode",
                converter=lambda x: MoesBacklight(x),
            ),
        }
    )

    data_point_handlers = TuyaOnOffManufCluster.data_point_handlers.copy()
    data_point_handlers.update({14: "_dp_2_attr_update"})
    data_point_handlers.update({15: "_dp_2_attr_update"})


class TuyaLevelControl(LevelControl, TuyaLocalCluster):
    """Tuya MCU Level cluster for dimmable device."""

    class AttributeDefs(LevelControl.AttributeDefs):
        """Cluster attributes."""

    async def command(
        self,
        command_id: foundation.GeneralCommand | int | t.uint8_t,
        *args,
        manufacturer: int | t.uint16_t | None = None,
        expect_reply: bool = True,
        tsn: int | t.uint8_t | None = None,
        **kwargs: Any,
    ):
        """Override the default Cluster command."""
        self.debug(
            "Sending Tuya Cluster Command. Cluster Command is %x, Arguments are %s, %s",
            command_id,
            args,
            kwargs,
        )

        # getting the level value
        if kwargs and "level" in kwargs:
            level = kwargs["level"]
        elif args:
            level = args[0]
        else:
            level = 0

        on_off = bool(level)  # maybe must be compared against `minimum_level` attribute

        # (move_to_level_with_on_off --> send the on_off command first, but only if needed)
        if command_id == 0x0004 and self.endpoint.on_off.get("on_off") != on_off:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name="on_off",
                cluster_attr="on_off",
                attr_value=on_off,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )

        # level 0 --> switched off
        if command_id == 0x0004 and not on_off:
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        # (move_to_level, move, move_to_level_with_on_off)
        if command_id in (0x0000, 0x0001, 0x0004):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr="current_level",
                attr_value=level,
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class TuyaInWallLevelControl(TuyaAttributesCluster, TuyaLevelControl):
    """Tuya Level cluster for inwall dimmable device."""

    class AttributeDefs(TuyaLevelControl.AttributeDefs):
        """Attribute definitions."""

        minimum_level: Final = ZCLAttributeDef(
            id=0xEF01, type=t.uint32_t, is_manufacturer_specific=True
        )
        bulb_type: Final = ZCLAttributeDef(
            id=0xEF02, type=t.enum8, is_manufacturer_specific=True
        )


class TuyaLevelControlManufCluster(TuyaMCUCluster):
    """Tuya with Level Control data points."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        2: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
        ),
        3: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
        ),
        4: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
        ),
        7: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=2,
        ),
        8: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=2,
        ),
        9: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=2,
        ),
        10: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
            endpoint_id=2,
        ),
        15: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            endpoint_id=3,
        ),
        16: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=3,
        ),
        17: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=3,
        ),
        18: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
            endpoint_id=3,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        8: "_dp_2_attr_update",
        9: "_dp_2_attr_update",
        10: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
        16: "_dp_2_attr_update",
        17: "_dp_2_attr_update",
        18: "_dp_2_attr_update",
    }
