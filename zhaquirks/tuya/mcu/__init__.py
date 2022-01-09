"""Tuya MCU comunications."""
from typing import Dict, Optional, Union

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks import Bus
from zhaquirks.tuya import (
    ATTR_ON_OFF,
    TUYA_MCU_COMMAND,
    TUYA_MCU_VERSION_RSP,
    TUYA_SET_DATA,
    Data,
    DPToAttributeMapping,
    TuyaCommand,
    TuyaData,
    TuyaLocalCluster,
    TuyaNewManufCluster,
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

    @classmethod
    def get_from_ztype(cls, ztype):
        """Search for the TuyaDPType with a compatible ztype."""

        for dpt in TuyaDPType:
            if dpt.ztype and issubclass(ztype, dpt.ztype):
                return dpt
        return None


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

        records = self._write_attr_records(attributes)

        for record in records:

            self.debug("write_attributes --> record: %s", record)

            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()

            ztype = self.attributes[record.attrid][1]
            dp_type = TuyaDPType.get_from_ztype(ztype)
            val = Data.from_value(ztype(record.value.value))

            cmd_payload.data = TuyaData()
            cmd_payload.data.dp_type = dp_type
            cmd_payload.data.function = 0
            cmd_payload.data.raw = t.LVBytes.deserialize(val)[0]

            self.debug("write_attributes --> payload: %s", cmd_payload)

            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cmd_payload,
                self.endpoint.endpoint_id,
                self.attributes[record.attrid][0],
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class TuyaMCUCluster(TuyaAttributesCluster, TuyaNewManufCluster):
    """Manufacturer specific cluster for sending Tuya MCU commands."""

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
                major = self.version_raw >> 6
                minor = (self.version_raw & 63) >> 4
                release = self.version_raw & 15

                return "{}.{}.{}".format(major, minor, release)

            return None

    manufacturer_attributes = {
        # MCU version
        ATTR_MCU_VERSION: ("mcu_version", t.uint48_t),
    }

    manufacturer_client_commands = (
        TuyaNewManufCluster.manufacturer_client_commands.copy()
    )
    manufacturer_client_commands.update(
        {
            TUYA_MCU_VERSION_RSP: ("mcu_version_response", (MCUVersion,), True),
        }
    )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # Cluster for endpoint: 1 (listen MCU commands)
        self.endpoint.device.command_bus = Bus()
        self.endpoint.device.command_bus.add_listener(self)

    def tuya_mcu_command(
        self, command: TuyaCommand, endpoint_id: int, attribute_name: str
    ):
        """Tuya MCU command listener. Only manufacturer endpoint must listen to MCU commands."""

        self.debug("tuya_mcu_command: %s", command)
        cluster_dp = self.get_dp_from_cluster(endpoint_id, attribute_name)
        if cluster_dp:
            command.dp = cluster_dp

            self.create_catching_task(
                self.command(TUYA_SET_DATA, command, expect_reply=True)
            )
        else:
            self.info(
                "No cluster_dp found for %s, %s",
                endpoint_id,
                attribute_name,
            )

    def get_dp_from_cluster(
        self, endpoint_id: int, attribute_name: str
    ) -> Optional[int]:
        """Search for the DP in dp_to_attribute."""

        for dp, dp_mapping in self.dp_to_attribute.items():
            if (attribute_name == dp_mapping.attribute_name) and (
                endpoint_id in [dp_mapping.endpoint_id, self.endpoint.endpoint_id]
            ):
                self.debug("get_dp_from_cluster --> found DP: %s", dp)
                return dp
        return None

    def handle_mcu_version_response(self, payload: MCUVersion) -> foundation.Status:
        """Handle MCU version response."""

        self.debug("MCU version: %s", payload.version)
        self.update_attribute("mcu_version", payload.version)
        return foundation.Status.SUCCESS


class TuyaOnOff(OnOff, TuyaLocalCluster):
    """Tuya MCU OnOff cluster."""

    attributes = {
        ATTR_ON_OFF: ("on_off", t.Bool),
    }

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
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
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            # cmd_payload.tsn = tsn if tsn else self.endpoint.device.application.get_sequence()
            cmd_payload.tsn = 0
            cmd_payload.data = TuyaData()
            cmd_payload.data.dp_type = TuyaDPType.BOOL
            cmd_payload.data.function = 0
            val = Data.from_value(TuyaDPType.BOOL.ztype(command_id))
            cmd_payload.data.raw = t.LVBytes.deserialize(val)[0]

            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cmd_payload,
                self.endpoint.endpoint_id,
                "on_off",
            )
            return foundation.Status.SUCCESS

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaOnOffManufCluster(TuyaMCUCluster):
    """Tuya with On/Off data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
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
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
    }


class SurfaceSwitchManufCluster(TuyaOnOffManufCluster):
    """On/Off Tuya cluster with extra device attributes."""

    attributes = {
        0x8001: ("backlight_mode", t.enum8),
        0x8002: ("power_on_state", t.enum8),
    }

    dp_to_attribute: Dict[
        int, DPToAttributeMapping
    ] = TuyaOnOffManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update(
        {
            14: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "power_on_state",
                # lambda x: PowerOnState(x),
            )
        }
    )
    dp_to_attribute.update(
        {
            15: DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "backlight_mode",
                # lambda x: BackLight(x),
            ),
        }
    )

    data_point_handlers = TuyaOnOffManufCluster.data_point_handlers.copy()
    data_point_handlers.update({14: "_dp_2_attr_update"})
    data_point_handlers.update({15: "_dp_2_attr_update"})


class TuyaLevelControl(LevelControl, TuyaLocalCluster):
    """Tuya MCU Level cluster for dimmable device."""

    attributes = {0x0000: ("current_level", t.uint8_t)}

    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""
        self.debug(
            "Sending Tuya Cluster Command. Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )
        # (move_to_level, move, move_to_level_with_on_off)
        if command_id in (0x0000, 0x0001, 0x0004):
            cmd_payload = TuyaCommand()
            cmd_payload.status = 0
            # cmd_payload.tsn = tsn if tsn else self.endpoint.device.application.get_sequence()
            cmd_payload.tsn = 0
            cmd_payload.data = TuyaData()
            cmd_payload.data.dp_type = TuyaDPType.VALUE
            cmd_payload.data.function = 0

            brightness = (args[0] * 1000) // 255
            val = Data.from_value(TuyaDPType.VALUE.ztype(brightness))
            cmd_payload.data.raw = t.LVBytes.deserialize(val)[0]

            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cmd_payload,
                self.endpoint.endpoint_id,
                "current_level",
            )
            return foundation.Status.SUCCESS

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaInWallLevelControl(TuyaAttributesCluster, TuyaLevelControl):
    """Tuya Level cluster for inwall dimmable device."""

    # Not sure if these are 'inwall' specific attributes
    manufacturer_attributes = {
        0xEF01: ("minimum_level", t.uint8_t),
        0xEF02: ("bulb_type", t.enum8),
    }


class TuyaLevelControlManufCluster(TuyaMCUCluster):
    """Tuya with Level Control data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        2: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "current_level",
            lambda x: (x * 255) // 1000,
        ),
        3: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            lambda x: (x * 255) // 1000,
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
            lambda x: (x * 255) // 1000,
            endpoint_id=2,
        ),
        9: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "minimum_level",
            lambda x: (x * 255) // 1000,
            endpoint_id=2,
        ),
        10: DPToAttributeMapping(
            TuyaLevelControl.ep_attribute,
            "bulb_type",
            endpoint_id=2,
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
    }
