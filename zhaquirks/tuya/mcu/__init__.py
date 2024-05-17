"""Tuya MCU communications."""

from collections.abc import Callable
import dataclasses
import datetime
import logging
from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import LevelControl, OnOff, PowerConfiguration

from zhaquirks import Bus, DoublingPowerConfigurationCluster

# add EnchantedDevice import for custom quirks backwards compatibility
from zhaquirks.tuya import (
    ATTR_COVER_DIRECTION_SETTING,
    ATTR_COVER_DIRECTION_SETTING_NAME,
    ATTR_COVER_INVERTED_SETTING,
    ATTR_COVER_INVERTED_SETTING_NAME,
    ATTR_COVER_LIFTPERCENT_NAME,
    ATTR_COVER_MAIN_CONTROL,
    ATTR_COVER_MAIN_CONTROL_NAME,
    TUYA_DP_ID_BATTERY_PERCENT,
    TUYA_DP_ID_CONTROL,
    TUYA_DP_ID_DIRECTION_SETTING,
    TUYA_DP_ID_LIMIT_SETTINGS,
    TUYA_DP_ID_PERCENT_CONTROL,
    TUYA_DP_ID_PERCENT_STATE,
    TUYA_DP_ID_SMALL_STEP,
    TUYA_MCU_SET_CLUSTER_DATA,
    TUYA_MCU_SET_DATAPOINTS,
    TUYA_MCU_VERSION_RSP,
    TUYA_SET_DATA,
    TUYA_SET_TIME,
    WINDOW_COVER_COMMAND_DOWNCLOSE,
    WINDOW_COVER_COMMAND_LIFTPERCENT,
    WINDOW_COVER_COMMAND_SMALL_STEP,
    WINDOW_COVER_COMMAND_SMALL_STEP_NAME,
    WINDOW_COVER_COMMAND_STOP,
    WINDOW_COVER_COMMAND_UPDATE_LIMITS,
    WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
    WINDOW_COVER_COMMAND_UPOPEN,
    EnchantedDevice,  # noqa: F401
    NoManufacturerCluster,
    PowerOnState,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaEnchantableCluster,
    TuyaLocalCluster,
    TuyaNewManufCluster,
    TuyaTimePayload,
)

# New manufacturer attributes
ATTR_MCU_VERSION = 0xEF00

# manufacturer commands
TUYA_MCU_CONNECTION_STATUS = 0x25

_LOGGER = logging.getLogger(__name__)

@dataclasses.dataclass
class DPToAttributeMapping:
    """Container for datapoint to cluster attribute update mapping."""

    ep_attribute: str
    attribute_name: Union[str, tuple]
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


@dataclasses.dataclass
class CommandToDPValueMapping:
    """Container for command id to datapoint value mapping."""

    dp: t.uint8_t
    value_source: Union[int, str, Callable[..., TuyaData]]


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

class CoverCommandStepDirection(t.enum8):
    """Window cover step command direction enum."""

    Open = 0
    Close = 1


class CoverMotorStatus(t.enum8):
    """Window cover motor states enum."""

    Opening = 0
    Stopped = 1
    Closing = 2


class CoverSettingMotorDirection(t.enum8):
    """Window cover motor direction configuration enum."""

    Forward = 0
    Backward = 1


class CoverSettingLimitOperation(t.enum8):
    """Window cover limits item to set / clear."""

    SetOpen = 0
    SetClose = 1
    ClearOpen = 2
    ClearClose = 3
    ClearBoth = 4


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
                cluster_name=self.ep_attribute,
                cluster_attr=self.attributes[record.attrid].name,
                attr_value=record.value.value,
                expect_reply=False,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_SET_CLUSTER_DATA,
                cluster_data,
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class TuyaCommandCluster(CustomCluster):
    """A tuya-based cluster that accepts zigbee commands and maps them to data point updates.

    Derived classed only need define a map and value converter to enable processing of commands
    into data point updates, sent to the tuya mcu cluster to send a set data command to the device.
    """

    command_to_dp: dict[Union[foundation.GeneralCommand, int, t.uint8_t], CommandToDPValueMapping] = {
    }

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        _tsn: Optional[Union[int, t.uint8_t]] = None,
        **kwargs: Any,
    ):
        """Process any commands that are mapped to data points."""
        _LOGGER.debug(
            "Processing command to dp mappings for Cluster Command. Command is %x, args=%s, kwargs=%s",
            command_id,
            args,
            kwargs,
        )

        # if there's a map for this command to a data points, call the map value function and send
        # the new value to the MCU cluster to send to the device
        command_map = self.command_to_dp.get(command_id, None)
        if command_map is not None:
            # command_map.value_source can refer to a numbered or named parameter or lambda
            if isinstance(command_map.value_source, int):
                value = args[command_map.value_source]
            elif isinstance(command_map.value_source, str):
                value = kwargs[command_map.value_source]
            else:
                value = command_map.value_source(*args, **kwargs)

            self.send_tuya_set_datapoints_command(command_map.dp, value, expect_reply=expect_reply,
                manufacturer=manufacturer)
            return self.default_response(command_id)

        _LOGGER.warning("Unsupported command_id: %s", command_id)
        return self.unsupported_response(command_id)


    def send_tuya_set_datapoints_command(
        self,
        dp: t.uint8_t,
        data: TuyaData,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
    ):
        """Send a set_data for a Tuya data point value (via the mcu cluster)."""

        datapoints = [TuyaDatapointData(dp, data)]
        self.debug("Sending TUYA_MCU_SET_DATAPOINTS: %s", datapoints)

        self.endpoint.device.command_bus.listener_event(
            TUYA_MCU_SET_DATAPOINTS, datapoints, manufacturer, expect_reply
        )


    def default_response(
        self, command_id: Union[foundation.GeneralCommand, int, t.uint8_t]
    ):
        """Return a default success response for a given command."""

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


    def unsupported_response(
        self, command_id: Union[foundation.GeneralCommand, int, t.uint8_t]
    ):
        """Return an 'unsupported' response for a given command."""

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


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

                return f"{major}.{minor}.{release}"

            return None

    class TuyaConnectionStatus(t.Struct):
        """Tuya connection status data."""

        tsn: t.uint8_t
        status: t.LVBytes

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
    client_commands.update(
        {
            TUYA_MCU_CONNECTION_STATUS: foundation.ZCLCommandDef(
                "mcu_connection_status",
                {"payload": TuyaConnectionStatus},
                True,
                is_manufacturer_specific=True,
            ),
        }
    )

    server_commands = TuyaNewManufCluster.server_commands.copy()
    server_commands.update(
        {
            TUYA_MCU_CONNECTION_STATUS: foundation.ZCLCommandDef(
                "mcu_connection_status_rsp",
                {"payload": TuyaConnectionStatus},
                False,
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
            cmd_payload.datapoints = [dpd]

            tuya_commands.append(cmd_payload)
        return tuya_commands

    def tuya_mcu_set_cluster_data(self, cluster_data: TuyaClusterData):
        """Tuya MCU listener to send/set tuya data points from cluster attributes.

        Only manufacturer endpoint must listen to MCU commands.
        """

        self.debug(
            "tuya_mcu_set_cluster_data: cluster_data=%s",
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

        endpoint = self.endpoint.device.endpoints[cluster_data.endpoint_id]
        cluster = getattr(endpoint, cluster_data.cluster_name)
        cluster.update_attribute(cluster_data.cluster_attr, cluster_data.attr_value)

    def tuya_mcu_set_datapoints(
        self,
        datapoints: list[TuyaDatapointData],
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
    ):
        """Tuya MCU listener to send/set tuya datapoint values."""

        self.debug("tuya_mcu_set_datapoints: datapoints=%s", datapoints)

        if len(datapoints) == 0:
            self.warning("no datapoints for tuya_mcu_set_datapoints")
            return

        cmd_payload = TuyaCommand()
        cmd_payload.status = 0
        cmd_payload.tsn = self.endpoint.device.application.get_sequence()
        cmd_payload.datapoints = datapoints

        self.create_catching_task(
            self.command(
                TUYA_SET_DATA,
                cmd_payload,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
            )
        )

    def get_dp_mapping(
        self, endpoint_id: int, attribute_name: str
    ) -> Optional[tuple[int, DPToAttributeMapping]]:
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

        utc_now = datetime.datetime.utcnow()  # noqa: DTZ003
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

    def handle_mcu_connection_status(
        self, payload: TuyaConnectionStatus
    ) -> foundation.Status:
        """Handle gateway connection status requests (0x25)."""

        payload_rsp = TuyaMCUCluster.TuyaConnectionStatus()
        payload_rsp.tsn = payload.tsn
        payload_rsp.status = b"\x01"  # 0x00 not connected to internet | 0x01 connected to internet | 0x02 time out

        self.create_catching_task(
            super().command(TUYA_MCU_CONNECTION_STATUS, payload_rsp, expect_reply=False)
        )

        return foundation.Status.SUCCESS


class TuyaOnOff(TuyaEnchantableCluster, OnOff, TuyaLocalCluster):
    """Tuya MCU OnOff cluster."""

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
        **_kwargs: Any
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
                TUYA_MCU_SET_CLUSTER_DATA,
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

    attributes = TuyaOnOffManufCluster.attributes.copy()
    attributes.update(
        {
            0x8001: ("backlight_mode", MoesBacklight),
            0x8002: ("power_on_state", PowerOnState),
        }
    )

    dp_to_attribute: dict[int, DPToAttributeMapping] = (
        TuyaOnOffManufCluster.dp_to_attribute.copy()
    )
    dp_to_attribute.update(
        {
            14: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "power_on_state",
                converter=PowerOnState,
            )
        }
    )
    dp_to_attribute.update(
        {
            15: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "backlight_mode",
                converter=MoesBacklight,
            ),
        }
    )

    data_point_handlers = TuyaOnOffManufCluster.data_point_handlers.copy()
    data_point_handlers.update({14: "_dp_2_attr_update"})
    data_point_handlers.update({15: "_dp_2_attr_update"})


class TuyaNewWindowCoverControl(TuyaAttributesCluster, TuyaCommandCluster, WindowCovering):
    """Tuya Window Cover Cluster, based on new TuyaNewManufClusterForWindowCover.

    Derive from TuyaLocalCluster to disable attribute writes, in a way that's compatible with
    TuyaNewManufClusterForWindowCover (not TuyaManufacturerWindowCover.)
    """

    attributes = WindowCovering.attributes.copy()
    # main control attribute is logically write-only, only used by commands and not very useful
    # to HA, but it's return in a set_data and set_data_response packet so I've mapped it to
    # an attribute.
    attributes.update(
        {
            ATTR_COVER_MAIN_CONTROL: (ATTR_COVER_MAIN_CONTROL_NAME, t.enum8),
            ATTR_COVER_INVERTED_SETTING: (
                ATTR_COVER_INVERTED_SETTING_NAME,
                t.Bool,
            ),
            ATTR_COVER_DIRECTION_SETTING: (
                ATTR_COVER_DIRECTION_SETTING_NAME,
                CoverSettingMotorDirection,
            ),
        }
    )

    server_commands = WindowCovering.server_commands.copy()
    server_commands.update(
        {
            WINDOW_COVER_COMMAND_SMALL_STEP: foundation.ZCLCommandDef(
                WINDOW_COVER_COMMAND_SMALL_STEP,
                {"direction": CoverCommandStepDirection},
                foundation.Direction.Client_to_Server,
                is_manufacturer_specific=True,
                name=WINDOW_COVER_COMMAND_SMALL_STEP_NAME,
            ),
            WINDOW_COVER_COMMAND_UPDATE_LIMITS: foundation.ZCLCommandDef(
                WINDOW_COVER_COMMAND_UPDATE_LIMITS,
                {"operation": CoverSettingLimitOperation},
                foundation.Direction.Client_to_Server,
                is_manufacturer_specific=True,
                name=WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
            ),
        }
    )

    command_to_dp: dict[Union[foundation.GeneralCommand, int, t.uint8_t], CommandToDPValueMapping] = {
        WINDOW_COVER_COMMAND_SMALL_STEP: CommandToDPValueMapping(TUYA_DP_ID_SMALL_STEP, "direction"),
        WINDOW_COVER_COMMAND_UPDATE_LIMITS: CommandToDPValueMapping(TUYA_DP_ID_LIMIT_SETTINGS, "operation"),
    }

    # For most tuya devices Up/Open = 0, Stop = 1, Down/Close = 2
    tuya_cover_command = {
        WINDOW_COVER_COMMAND_UPOPEN: 0x0000,
        WINDOW_COVER_COMMAND_DOWNCLOSE: 0x0002,
        WINDOW_COVER_COMMAND_STOP: 0x0001,
    }

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

        _LOGGER.debug(
            "Sending Tuya Cluster Command... Cluster Command is %x, args=%s, kwargs=%s",
            command_id,
            args,
            kwargs,
        )

        # Custom command processing first
        # Open Close or Stop commands
        # TODO - consider using command to dp mapping for these (knowing that the attribute will be
        # updated) when the device echos the dp values.
        if command_id in (
            WINDOW_COVER_COMMAND_UPOPEN,
            WINDOW_COVER_COMMAND_DOWNCLOSE,
            WINDOW_COVER_COMMAND_STOP,
        ):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr=ATTR_COVER_MAIN_CONTROL_NAME,
                # Map from zigbee command to tuya DP value
                attr_value=self.tuya_cover_command[command_id],
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_SET_CLUSTER_DATA,
                cluster_data,
            )
            return self.default_response(command_id)
        # TODO - Use command to dp mapping for lift percent, but need a way to call convert_lift_percent
        elif command_id == WINDOW_COVER_COMMAND_LIFTPERCENT:
            self.send_tuya_set_datapoints_command(
                TUYA_DP_ID_PERCENT_CONTROL,
                self._compute_lift_percent(args[0]),
                expect_reply=expect_reply,
                manufacturer=manufacturer,
            )
            return self.default_response(command_id)

        # now let TuyaCommandCluster handle any remaining commands mapped to data points
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs
            )

    def _compute_lift_percent(self, input_value: int):
        """Convert/invert lift percent when needed.

        HA shows % open. The zigbee cluster value is called 'lift_percent' but seems to need to
        be % closed. This logic follows the convention of other Tuya covers, inverting the value
        by default, unless the cluster invert attribute is set. (This seems strange to me, but it's
        better to be consistent.)

        It's safe to use the same calculation converting motor position to zigbee attribute value
        and attribute value to motor position command.
        """

        invert = self._attr_cache.get(ATTR_COVER_INVERTED_SETTING) == 1
        return input_value if invert else 100 - input_value


    def update_lift_percent(self, raw_value: int):
        """Update lift percent attribute when it's data point data is received."""

        new_attribute_value = self._compute_lift_percent(raw_value)
        self.update_attribute(ATTR_COVER_LIFTPERCENT_NAME, new_attribute_value)


class TuyaNewManufClusterForWindowCover(TuyaMCUCluster):
    """Manufacturer Specific Cluster for cover device (based on new TuyaMCUCluster).

    I.e. Uses newer TuyaMCUCluster mechanism for translations between cluster attributes and
    Tuya data points.
    """

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        TUYA_DP_ID_CONTROL: DPToAttributeMapping(
            TuyaNewWindowCoverControl.ep_attribute,
            ATTR_COVER_MAIN_CONTROL_NAME,
            # Converting raw ints to a type allows the attributes UI show meaningful values
            CoverMotorStatus,
            CoverMotorStatus,
        ),
        TUYA_DP_ID_DIRECTION_SETTING: DPToAttributeMapping(
            TuyaNewWindowCoverControl.ep_attribute,
            ATTR_COVER_DIRECTION_SETTING_NAME,
            CoverSettingMotorDirection,
            CoverSettingMotorDirection,
        ),
        TUYA_DP_ID_BATTERY_PERCENT: DPToAttributeMapping(
            PowerConfiguration.ep_attribute,
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
            # Tuya report real percent, zigbee expects value*2, but
            # TuyaPowerConfigurationCluster will convert it
        ),
    }

    data_point_handlers = {
        TUYA_DP_ID_CONTROL: "_dp_2_attr_update",
        TUYA_DP_ID_PERCENT_STATE: "update_lift_percent",
        TUYA_DP_ID_DIRECTION_SETTING: "_dp_2_attr_update",
        TUYA_DP_ID_BATTERY_PERCENT: "_dp_2_attr_update",
        # Ignore updates from data points that are used as write-only commands to the device, we
        # don't need attributes to display their values, but they're echoed back in get_data and
        # would otherwise log debug messages.
        TUYA_DP_ID_PERCENT_CONTROL: "ignore_update",
        # I don't know what 7 is, but it's part of set_data_response
        7: "ignore_update",
        TUYA_DP_ID_LIMIT_SETTINGS: "ignore_update",
        TUYA_DP_ID_SMALL_STEP: "ignore_update",
    }

    def update_lift_percent(self, datapoint: TuyaDatapointData):
        """Update lift percent attribute when it's data point data is received.

        This can't be done as a dp_to_attribute entry because it needs access to self which
        dp_to_attribute callbacks don't have, but data_point_handlers do.
        """
        cluster = self.endpoint.window_covering
        cluster.update_lift_percent(datapoint.data.payload)

    def ignore_update(self, _datapoint: TuyaDatapointData) -> None:
        """Process (and ignore) some data point updates."""
        return None


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
                TUYA_MCU_SET_CLUSTER_DATA,
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
                TUYA_MCU_SET_CLUSTER_DATA,
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
