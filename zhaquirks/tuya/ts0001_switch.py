"""Tuya switch device."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.tuya import TuyaZBOnOffAttributeCluster


class CustomMetering(Metering, CustomCluster):
    """Tuya Valve Water consumed cluster."""

    KILOWATT_HOURS = 0x0
    ELECTRIC_METERING = 0x0

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.unit_of_measure.id: KILOWATT_HOURS,
        Metering.AttributeDefs.metering_device_type.id: ELECTRIC_METERING,
    }


(
    QuirkBuilder("_TZ3000_tgddllx4", "TS0001")
    .replaces(CustomMetering)
    .replaces(TuyaZBOnOffAttributeCluster)
    .add_to_registry()
)
