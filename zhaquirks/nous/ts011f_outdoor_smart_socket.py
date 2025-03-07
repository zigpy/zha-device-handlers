"""Nous A4Z Outdoor 2 plug with metering."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering


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
    QuirkBuilder("_TZ3000_uwkja6z1", "TS011F")
    .friendly_name(manufacturer="Nous", model="A4Z ZigBee Outdoor Smart Socket")
    .replaces(CustomMetering, endpoint_id=1)
    .replaces(CustomElectricalMeasurement, endpoint_id=1)
    # We remove endpoint 2 measurement and metering, because its duplicated
    .removes(Metering.cluster_id, endpoint_id=2)
    .removes(ElectricalMeasurement.cluster_id, endpoint_id=2)
    .add_to_registry()
)
