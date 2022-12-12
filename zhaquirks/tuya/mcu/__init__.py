"""Tuya MCU comunications."""
import asyncio
import dataclasses
import datetime
from typing import Any, Callable, Dict, Optional, Tuple, Union

from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks import Bus, DoublingPowerConfigurationCluster
from zhaquirks.tuya import (
    TUYA_MCU_COMMAND,
    TUYA_MCU_VERSION_RSP,
    TUYA_SET_DATA,
    TUYA_SET_TIME,
    Data,
    NoManufacturerCluster,
    PowerOnState,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaLocalCluster,
    TuyaNewManufCluster,
    TuyaTimePayload,
)

# New manufacturer attributes
ATTR_MCU_VERSION = 0xEF00


class TuyaDPType(t.enum8):
    """Tuya DataPoint Type."""

    RAW = 0x00, None
    BOOL = 0x01, t.Bool
    VALUE = 0x02, t.uint32_t
    STRING = 0x03, None
    ENUM = 0x04, t.enum8
    BITMAP = 0x05, None

    def __new__(cls, value, ztype):
        """Overload instance to store the ztype."""

        member = t.enum8.__new__(cls, value)
        member.ztype = ztype
        return member


@dataclasses.dataclass
class DPToAttributeMapping:
    """Container for datapoint to cluster attribute update mapping."""

    ep_attribute: str
    attribute_name: Union[str, tuple]
    dp_type: TuyaDPType
    converter: Optional[
        Callable[
            [
                Any,
            ],
            Any,
        ]
    ] = None
    dp_converter: Optional[
        Callable[
            [
                Any,
            ],
            Any,
        ]
    ] = None
    endpoint_id: Optional[int] = None


class TuyaClusterData(t.Struct):
    """Tuya cluster data."""

    endpoint_id: int
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

    def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Ignore remote reads as the "get_data" command doesn't seem to do anything."""

        self.debug("read_attributes --> attrs: %s", attributes)
        return super().read_attributes(
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
                cluster_attr=self.attributes[record.attrid][0],
                attr_value=record.value.value,
                expect_reply=False,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class TuyaMCUCluster(TuyaAttributesCluster, TuyaNewManufCluster):
    """Manufacturer specific cluster for sending Tuya MCU commands."""

    set_time_offset = 1970  # MCU timestamp from 1/1/1970
    set_time_local_offset = None

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

                return "{}.{}.{}".format(major, minor, release)

            return None

    attributes = TuyaNewManufCluster.attributes.copy()
    attributes.update(
        {
            # MCU version
            ATTR_MCU_VERSION: ("mcu_version", t.uint48_t, True),
        }
    )

    client_commands = TuyaNewManufCluster.client_commands.copy()
    client_commands.update(
        {
            TUYA_MCU_VERSION_RSP: foundation.ZCLCommandDef(
                "mcu_version_response",
                {"version": MCUVersion},
                True,
                is_manufacturer_specific=True,
            ),
        }
    )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # Cluster for endpoint: 1 (listen MCU commands)
        self.endpoint.device.command_bus = Bus()
        self.endpoint.device.command_bus.add_listener(self)

    def from_cluster_data(self, data: TuyaClusterData) -> Optional[TuyaCommand]:
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

        tuya_commands = []
        for dp, mapping in dp_mapping.items():
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()

            datapoint_type = mapping.dp_type
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
                self.debug("converted: %s", val)
            if datapoint_type.ztype:
                val = datapoint_type.ztype(val)
                self.debug("ztype: %s", val)
            val = Data.from_value(val)
            self.debug("from_value: %s", val)

            tuya_data = TuyaData()
            tuya_data.dp_type = datapoint_type
            tuya_data.function = 0
            tuya_data.raw = t.LVBytes.deserialize(val)[0]
            self.debug("raw: %s", tuya_data.raw)
            dpd = TuyaDatapointData(dp, tuya_data)
            cmd_payload.datapoints = [dpd]

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
                    TUYA_SET_DATA,
                    tuya_command,
                    expect_reply=cluster_data.expect_reply,
                    manufacturer=cluster_data.manufacturer,
                )
            )

    def get_dp_mapping(
        self, endpoint_id: int, attribute_name: str
    ) -> Optional[Tuple[int, DPToAttributeMapping]]:
        """Search for the DP in dp_to_attribute."""

        result = {}
        for dp, dp_mapping in self.dp_to_attribute.items():
            if (
                attribute_name == dp_mapping.attribute_name
                or (
                    isinstance(dp_mapping.attribute_name, tuple)
                    and attribute_name in dp_mapping.attribute_name
                )
            ) and (
                (
                    dp_mapping.endpoint_id is None
                    and endpoint_id == self.endpoint.endpoint_id
                )
                or (endpoint_id == dp_mapping.endpoint_id)
            ):
                self.debug("get_dp_mapping --> found DP: %s", dp)
                result[dp] = dp_mapping
        return result

    def handle_mcu_version_response(self, payload: MCUVersion) -> foundation.Status:
        """Handle MCU version response."""

        self.debug("MCU version: %s", payload.version)
        self.update_attribute("mcu_version", payload.version)
        return foundation.Status.SUCCESS

    def handle_set_time_request(self, payload: t.uint16_t) -> foundation.Status:
        """Handle set_time requests (0x24)."""

        self.debug("handle_set_time_request payload: %s", payload)
        payload_rsp = TuyaTimePayload()

        utc_now = datetime.datetime.utcnow()
        now = datetime.datetime.now()

        offset_time = datetime.datetime(self.set_time_offset, 1, 1)
        offset_time_local = datetime.datetime(
            self.set_time_local_offset or self.set_time_offset, 1, 1
        )

        utc_timestamp = int((utc_now - offset_time).total_seconds())
        local_timestamp = int((now - offset_time_local).total_seconds())

        payload_rsp.extend(utc_timestamp.to_bytes(4, "big", signed=False))
        payload_rsp.extend(local_timestamp.to_bytes(4, "big", signed=False))

        self.debug("handle_set_time_request response: %s", payload_rsp)
        self.create_catching_task(
            super().command(TUYA_SET_TIME, payload_rsp, expect_reply=False)
        )

        return foundation.Status.SUCCESS


class TuyaOnOff(OnOff, TuyaLocalCluster):
    """Tuya MCU OnOff cluster."""

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
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
                cluster_attr="on_off",
                attr_value=command_id,
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

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
        ),
        2: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=2,
        ),
        3: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=3,
        ),
        4: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=4,
        ),
        5: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=5,
        ),
        6: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=6,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
    }


class MoesSwitchManufCluster(TuyaOnOffManufCluster):
    """On/Off Tuya cluster with extra device attributes."""

    attributes = TuyaOnOffManufCluster.attributes.copy()
    attributes.update(
        {
            0x8001: ("backlight_mode", MoesBacklight),
            0x8002: ("power_on_state", PowerOnState),
        }
    )

    dp_to_attribute: Dict[
        int, DPToAttributeMapping
    ] = TuyaOnOffManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update(
        {
            14: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "power_on_state",
                dp_type=TuyaDPType.ENUM,
                converter=lambda x: PowerOnState(x),
            )
        }
    )
    dp_to_attribute.update(
        {
            15: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "backlight_mode",
                dp_type=TuyaDPType.ENUM,
                converter=lambda x: MoesBacklight(x),
            ),
        }
    )

    data_point_handlers = TuyaOnOffManufCluster.data_point_handlers.copy()
    data_point_handlers.update({14: "_dp_2_attr_update"})
    data_point_handlers.update({15: "_dp_2_attr_update"})


class TuyaLevelControl(LevelControl, TuyaLocalCluster):
    """Tuya MCU Level cluster for dimmable device."""

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

        # (move_to_level_with_on_off --> send the on_off command first)
        if command_id == 0x0004:
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_attr="on_off",
                attr_value=bool(
                    level
                ),  # maybe must be compared against `minimum_level` attribute
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )

        # (move_to_level, move, move_to_level_with_on_off)
        if command_id in (0x0000, 0x0001, 0x0004):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
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

    # Not sure if these are 'inwall' specific attributes or common to dimmers
    attributes = TuyaLevelControl.attributes.copy()
    attributes.update(
        {
            0xEF01: ("minimum_level", t.uint32_t, True),
            0xEF02: ("bulb_type", t.enum8, True),
        }
    )


class TuyaLevelControlManufCluster(TuyaMCUCluster):
    """Tuya with Level Control data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
        ),
        2: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
        ),
        3: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
        ),
        4: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
            dp_type=TuyaDPType.ENUM,
        ),
        7: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=2,
        ),
        8: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=2,
        ),
        9: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=2,
        ),
        10: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
            dp_type=TuyaDPType.ENUM,
            endpoint_id=2,
        ),
        15: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
            endpoint_id=3,
        ),
        16: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=3,
        ),
        17: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            dp_type=TuyaDPType.VALUE,
            converter=lambda x: (x * 255) // 1000,
            dp_converter=lambda x: (x * 1000) // 255,
            endpoint_id=3,
        ),
        18: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
            dp_type=TuyaDPType.ENUM,
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


class EnchantedDevice(CustomDevice):
    """Class for enchanted Tuya devices which needs to be unlocked by casting a 'spell'."""

    def __init__(self, *args, **kwargs):
        """Initialize with task."""
        super().__init__(*args, **kwargs)
        self._init_device_task = asyncio.create_task(self.spell())

    async def spell(self) -> None:
        """Initialize device so that all endpoints become available."""
        attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
        basic_cluster = self.endpoints[1].in_clusters[0]
        await basic_cluster.read_attributes(attr_to_read)
