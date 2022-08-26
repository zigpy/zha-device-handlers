"""Module for Schneider Electric devices quirks."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.foundation import ZCLAttributeDef

_LOGGER = logging.getLogger(__name__)

SE_MANUF_NAME = "Schneider Electric"
SE_MANUF_ID = 4190

# Attribute IDs
ATTR_CURRENT_POSITION_LIFT_PERCENTAGE=0x0008

# Command IDs
CMD_GO_TO_LIFT_PERCENTAGE = 0x0005

class SEManufCluster(CustomCluster):
    """Schneider Electric manufacturer specific cluster."""

    name = "Schneider Electric Manufacturer Specicific"
    ep_attribute = "schneider_electric_manufacturer"


class SEBasicCluster(SEManufCluster, Basic):

    attributes: dict[int, ZCLAttributeDef] = Basic.attributes.copy()

    attributes.update(
        {
            0xE001: ZCLAttributeDef(
                id=0xE001,
                name="unknown_attribute_57345",
                type=t.CharacterString,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57345" # ex: "002.004.016 R
        {
            0xE002: ZCLAttributeDef(
                id=0xE002,
                name="unknown_attribute_57346",
                type=t.CharacterString,
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57346" # ex: "001.000.000"
        {
            0xE004: ZCLAttributeDef(
                id=0xE004,
                name="unknown_attribute_57348",
                type=t.CharacterString,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57348"  # ex: "213249FEFF5ECFD"
        {
            0xE007: ZCLAttributeDef(
                id=0xE007,
                name="unknown_attribute_57351",
                type=t.enum16,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57351"
        {
            0xE008: ZCLAttributeDef(
                id=0xE008,
                name="unknown_attribute_57352",
                type=t.CharacterString,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57352" # ex: "Wiser Light"
        {
            0xE009: ZCLAttributeDef(
                id=0xE009,
                name="unknown_attribute_57353",
                type=t.CharacterString,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57353" # ex: "NHPB/SHUTTER/1"
        {
            0xE00A: ZCLAttributeDef(
                id=0xE00A,
                name="unknown_attribute_57354",
                type=t.CharacterString,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57354" # ex: "Wiser Home"
        {
            0xE00B: ZCLAttributeDef(
                id=0xE00B,
                name="unknown_attribute_57355",
                type=t.CharacterString,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57355"
    )


class SESpecificCluster(SEManufCluster):
    cluster_id = 0xFF17

    attributes = {
        {
            0x0000: ZCLAttributeDef(
                id=0x0000,
                name="unknown_attribute_0",
                type=t.enum8,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"0"
        {
            0x0001: ZCLAttributeDef(
                id=0x0001,
                name="unknown_attribute_1",
                type=t.enum8,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"1"
        {
            0x0010: ZCLAttributeDef(
                id=0x0010,
                name="unknown_attribute_16",
                type=t.uint8_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"16"
        {
            0x0011: ZCLAttributeDef(
                id=0x0011,
                name="unknown_attribute_17",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"17"
        {
            0x0020: ZCLAttributeDef(
                id=0x0020,
                name="unknown_attribute_32",
                type=t.uint8_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"32"
        {
            0x0021: ZCLAttributeDef(
                id=0x0021,
                name="unknown_attribute_33",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"33"
        {
            0xFFFD: ZCLAttributeDef(
                id=0xFFFD,
                name="unknown_attribute_65533",
                type=t.uint16_t,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"65533"
    }


class SEWindowCovering(SEManufCluster, WindowCovering):
    """Manufacturer Specific Cluster of Device cover."""

    attributes: dict[int, ZCLAttributeDef] = WindowCovering.attributes.copy()

    attributes.update(
        {
            0xFFFD: ZCLAttributeDef(
                id=0xFFFD,
                name="lift_duration",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"65533"
        {
            0xE000: ZCLAttributeDef(
                id=0xE000,
                name="unknown_attribute_57344",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57344"
        {
            0xE010: ZCLAttributeDef(
                id=0xE010,
                name="unknown_attribute_57360",
                type=t.bitmap8,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57360"
        {
            0xE012: ZCLAttributeDef(
                id=0xE012,
                name="unknown_attribute_57362",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57362"
        {
            0xE013: ZCLAttributeDef(
                id=0xE013,
                name="unknown_attribute_57363",
                type=t.bitmap8,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57363"
        {
            0xE014: ZCLAttributeDef(
                id=0xE014,
                name="unknown_attribute_57364",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57364"
        {
            0xE015: ZCLAttributeDef(
                id=0xE015,
                name="unknown_attribute_57365",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57365"
        {
            0xE016: ZCLAttributeDef(
                id=0xE016,
                name="unknown_attribute_57366",
                type=t.uint16_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57366"
        {
            0xE017: ZCLAttributeDef(
                id=0xE017,
                name="unknown_attribute_57367",
                type=t.uint8_t,
                access="rw",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"57367"
    )

    def _update_attribute(self, attrid, value):
        if attrid == self.ATTR_CURRENT_POSITION_LIFT_PERCENTAGE:
            # Invert the percentage value
            value = 100 - value
        super()._update_attribute(attrid, value)

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Override default command to invert percent lift value."""
        if command_id == self.CMD_GO_TO_LIFT_PERCENTAGE:
            percent = args[0]
            percent = 100 - percent
            v = (percent,)
            return await super().command(command_id, *v)
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn
        )

class SEDiagnostic(CustomCluster, Diagnostic):

    attributes: dict[int, ZCLAttributeDef] = Diagnostic.attributes.copy()

    # TODO: Check -> this attr don't seems to be manufacturer related (no "manf_id")
    attributes.update(
        {
            0xFFFD: ZCLAttributeDef(
                id=0xFFFD,
                name="unknown_attribute_65533",
                type=t.uint16_t,
                access="r",
                is_manufacturer_specific=True,
            )
        },  # attribute_name:"65533"
    )
