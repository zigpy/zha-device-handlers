"""Tuya 1 gang switch with power monitoring.

The v1 ``ts000x.Switch_1G_Metering`` quirk matches the same hardware by endpoint
signature, but these manufacturers also ship layouts without the Green Power
endpoint or the 0xE000 cluster, which that signature misses. This v2 quirk matches
them by manufacturer and takes precedence over the v1 quirk, so it carries the same
Tuya plug features and spell.
"""

from zha.quirks import TUYA_PLUG_ONOFF
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import TuyaZBExternalSwitchTypeCluster, TuyaZBOnOffAttributeCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class CustomElectricalMeasurement(ElectricalMeasurement, CustomCluster):
    """Custom electrical measurement cluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
    }


class CustomMetering(Metering, CustomCluster):
    """Custom metering cluster."""

    KILOWATT_HOURS = 0x0
    ELECTRIC_METERING = 0x0

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.unit_of_measure.id: KILOWATT_HOURS,
        Metering.AttributeDefs.metering_device_type.id: ELECTRIC_METERING,
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


(
    TuyaQuirkBuilder("_TZ3000_xkap8wtb", "TS0001")
    .applies_to("_TZ3000_qnejhcsu", "TS0001")
    .applies_to("_TZ3000_x3ewpzyr", "TS0001")
    .applies_to("_TZ3000_mkhkxx1p", "TS0001")
    .applies_to("_TZ3000_tgddllx4", "TS0001")
    .applies_to("_TZ3000_kqvb5akv", "TS0001")
    .applies_to("_TZ3000_g92baclx", "TS0001")
    .applies_to("_TZ3000_qlai3277", "TS0001")
    .applies_to("_TZ3000_qaabwu5c", "TS0001")
    .applies_to("_TZ3000_ikuxinvo", "TS0001")
    .applies_to("_TZ3000_hzlsaltw", "TS0001")
    .applies_to("_TZ3000_jsfzkftc", "TS0001")
    .replaces(CustomMetering)
    .replaces(CustomElectricalMeasurement)
    .replaces(TuyaZBOnOffAttributeCluster)
    .replaces(TuyaZBExternalSwitchTypeCluster)
    .exposes_feature(TUYA_PLUG_ONOFF)
    .tuya_enchantment()
    .add_to_registry()
)
