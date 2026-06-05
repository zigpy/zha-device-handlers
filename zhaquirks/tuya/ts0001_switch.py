"""Tuya switch device."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.tuya import TuyaZBExternalSwitchTypeCluster, TuyaZBOnOffAttributeCluster


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
    QuirkBuilder("_TZ3000_xkap8wtb", "TS0001")
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
    .add_to_registry()
)
