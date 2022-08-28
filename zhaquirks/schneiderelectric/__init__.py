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
ATTR_CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008

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
            0xE001: (
                "se_sw_build_id",
                t.CharacterString,
            ),  # attribute_name:"57345" # ex: "002.004.016 R
            0xE002: (
                "unknown_attribute_57346",
                t.CharacterString,
            ),  # attribute_name:"57346" # ex: "001.000.000"
            0xE004: (
                "unknown_attribute_57348",
                t.CharacterString,
            ),  # attribute_name:"57348"  # ex: "213249FEFF5ECFD"
            0xE007: ("unknown_attribute_57351", t.enum16),  # attribute_name:"57351"
            0xE008: (
                "se_device_type",
                t.CharacterString,
            ),  # attribute_name:"57352" # ex: "Wiser Light"
            0xE009: (
                "se_model",
                t.CharacterString,
            ),  # attribute_name:"57353" # ex: "NHPB/SHUTTER/1"
            0xE00A: (
                "se_realm",
                t.CharacterString,
            ),  # attribute_name:"57354" # ex: "Wiser Home"
            0xE00B: (
                "unknown_attribute_57355",
                t.CharacterString,
            ),  # attribute_name:"57355"
        }
    )


class SESpecificCluster(SEManufCluster):
    cluster_id = 0xFF17

    attributes = {
        0x0000: ("unknown_attribute_0", t.enum8),  # attribute_name:"0"
        0x0001: ("unknown_attribute_1", t.enum8),  # attribute_name:"1"
        0x0010: ("unknown_attribute_16", t.uint8_t),  # attribute_name:"16"
        0x0011: ("unknown_attribute_17", t.uint16_t),  # attribute_name:"17"
        0x0020: ("unknown_attribute_32", t.uint8_t),  # attribute_name:"32"
        0x0021: ("unknown_attribute_33", t.uint16_t),  # attribute_name:"33"
        0xFFFD: ("unknown_attribute_65533", t.uint16_t),  # attribute_name:"65533"
    }


class SEWindowCovering(SEManufCluster, WindowCovering):
    """Manufacturer Specific Cluster of cover device."""

    attributes: dict[int, ZCLAttributeDef] = WindowCovering.attributes.copy()

    attributes.update(
        {
            0xFFFD: ("unknown_attribute_65533", t.uint16_t),  # attribute_name:"65533"
            0xE000: ("lift_duration", t.uint16_t),  # attribute_name:"57344"
            0xE010: ("unknown_attribute_57360", t.bitmap8),  # attribute_name:"57360"
            0xE012: ("unknown_attribute_57362", t.uint16_t),  # attribute_name:"57362"
            0xE013: ("unknown_attribute_57363", t.bitmap8),  # attribute_name:"57363"
            0xE014: ("unknown_attribute_57364", t.uint16_t),  # attribute_name:"57364"
            0xE015: ("unknown_attribute_57365", t.uint16_t),  # attribute_name:"57365"
            0xE016: ("unknown_attribute_57366", t.uint16_t),  # attribute_name:"57366"
            0xE017: ("unknown_attribute_57367", t.uint8_t),  # attribute_name:"57367"
        }
    )

    def _update_attribute(self, attrid, value):
        if attrid == ATTR_CURRENT_POSITION_LIFT_PERCENTAGE:
            # Invert the percentage value
            value = 100 - value
        super()._update_attribute(attrid, value)

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Override default command to invert percent lift value."""
        if command_id == CMD_GO_TO_LIFT_PERCENTAGE:
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
            0xFFFD: ("unknown_attribute_65533", t.uint16_t),  # attribute_name:"65533"
        }
    )
