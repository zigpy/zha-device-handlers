"""Nous A4Z outdoor smart socket."""

from zha.quirks import SE_POLL_SUMMATION, TUYA_PLUG_ONOFF
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import TuyaZBOnOffAttributeCluster


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
    .friendly_name(model="A4Z outdoor smart socket", manufacturer="Nous")
    # The socket reports neither the Metering multiplier/divisor nor the
    # ElectricalMeasurement AC current multiplier/divisor, so without these
    # constants both fall back to 1/1: summation reads 100x and current 1000x
    # too high.
    .replaces(CustomMetering)
    .replaces(CustomElectricalMeasurement)
    # The socket does not report summation on its own, it has to be polled. ZHA
    # polls Metering for a model allowlist that TS011F is on, but the friendly
    # name above renames the model out of that list, so ask for the poll here.
    .exposes_feature(SE_POLL_SUMMATION)
    # Endpoint 2 re-reports the whole-socket measurement instead of its own
    # outlet, so its sensors only duplicate endpoint 1's.
    .removes(Metering.cluster_id, endpoint_id=2)
    .removes(ElectricalMeasurement.cluster_id, endpoint_id=2)
    # Power on state, backlight mode and child lock, as on other TS011F plugs.
    # These are one socket-wide register mirrored on both endpoints, so they are
    # only exposed on endpoint 1: writing endpoint 2 changes endpoint 1 too.
    .replaces(TuyaZBOnOffAttributeCluster)
    .exposes_feature(TUYA_PLUG_ONOFF)
    .add_to_registry()
)
