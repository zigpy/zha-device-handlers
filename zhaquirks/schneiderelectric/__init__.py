"""Module for Schneider Electric devices quirks."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.homeautomation import Diagnostic

_LOGGER = logging.getLogger(__name__)

SE = "Schneider Electric"


class SEManufCluster(CustomCluster):
    """Schneider Electric manufacturer specific cluster."""

    name = "Schneider Electric Manufacturer Specicific"
    ep_attribute = "schneider_electric_manufacturer"


class SEBasicCluster(SEManufCluster, Basic):
    ATT_ID_E001 = 0xE001
    ATT_ID_E002 = 0xE002
    ATT_ID_E004 = 0xE004
    ATT_ID_E007 = 0xE007
    ATT_ID_E008 = 0xE008
    ATT_ID_E009 = 0xE009
    ATT_ID_E00A = 0xE00A
    ATT_ID_E00B = 0xE00B

    attributes = Basic.attributes.copy()

    attributes.update(
        {
            ATT_ID_E001: ("57345", t.CharacterString)
        },  # attribute_name:"57345" # ex: "002.004.016 R
        {
            ATT_ID_E002: ("57346", t.CharacterString)
        },  # attribute_name:"57346" # ex: "001.000.000"
        {
            ATT_ID_E004: ("57348", t.CharacterString)
        },  # attribute_name:"57348"  # ex: "213249FEFF5ECFD"
        {ATT_ID_E007: ("57351", t.enum16)},  # attribute_name:"57351"
        {
            ATT_ID_E008: ("57352", t.CharacterString)
        },  # attribute_name:"57352" # ex: "Wiser Light"
        {
            ATT_ID_E009: ("57353", t.CharacterString)
        },  # attribute_name:"57353" # ex: "NHPB/SHUTTER/1"
        {
            ATT_ID_E00A: ("57354", t.CharacterString)
        },  # attribute_name:"57354" # ex: "Wiser Home"
        {ATT_ID_E00B: ("57355", t.CharacterString)},  # attribute_name:"57355"
    )


class SEManufSwitchCluster(SEManufCluster):
    name = "Schneider Electric Manufacturer Specicific"
    cluster_id = 0xFF17

    ATT_ID_0000 = 0x0000
    ATT_ID_0001 = 0x0001
    ATT_ID_0010 = 0x0010
    ATT_ID_0011 = 0x0011
    ATT_ID_0020 = 0x0020
    ATT_ID_0021 = 0x0021
    ATT_ID_FFFD = 0xFFFD

    attributes = {
        {ATT_ID_0000: ("0", t.enum8)},  # attribute_name:"0"
        {ATT_ID_0001: ("1", t.enum8)},  # attribute_name:"1"
        {ATT_ID_0010: ("16", t.uint8_t)},  # attribute_name:"16"
        {ATT_ID_0011: ("17", t.uint16_t)},  # attribute_name:"17"
        {ATT_ID_0020: ("32", t.uint8_t)},  # attribute_name:"32"
        {ATT_ID_0021: ("33", t.uint16_t)},  # attribute_name:"33"
        {ATT_ID_FFFD: ("65533", t.uint16_t)},  # attribute_name:"65533"
    }


class SEWindowCover(CustomCluster, WindowCovering):
    """Manufacturer Specific Cluster of Device cover."""

    ATT_ID_FFFD = 0xFFFD
    ATT_ID_E000 = 0xE000
    ATT_ID_E010 = 0xE010
    ATT_ID_E012 = 0xE012
    ATT_ID_E013 = 0xE013
    ATT_ID_E014 = 0xE014
    ATT_ID_E015 = 0xE015
    ATT_ID_E016 = 0xE016
    ATT_ID_E017 = 0xE017

    attributes = WindowCovering.attributes.copy()

    attributes.update(
        {
            ATT_ID_FFFD: ("57344", t.uint16_t)
        },  # attribute_name:"57344" # seems to be lift_duration
        {ATT_ID_E000: ("65533", t.uint16_t)},  # attribute_name:"65533"
        {ATT_ID_E010: ("57360", t.bitmap8)},  # attribute_name:"57360"
        {ATT_ID_E012: ("57362", t.uint16_t)},  # attribute_name:"57362"
        {ATT_ID_E013: ("57363", t.bitmap8)},  # attribute_name:"57363"
        {ATT_ID_E014: ("57364", t.uint16_t)},  # attribute_name:"57364"
        {ATT_ID_E015: ("57365", t.uint16_t)},  # attribute_name:"57365"
        {ATT_ID_E016: ("57366", t.uint16_t)},  # attribute_name:"57366"
        {ATT_ID_E017: ("57367", t.uint8_t)},  # attribute_name:"57367"
    )


class SEDiagnostic(CustomCluster, Diagnostic):

    ATT_ID_FFFD = 0xFFFD

    attributes = Diagnostic.attributes.copy()

    # TODO: Check -> this attr don't seems to be manufacturer related (no "manf_id")
    attributes.update(
        {ATT_ID_FFFD: ("65533", t.uint16_t)},  # attribute_name:"65533"
    )
