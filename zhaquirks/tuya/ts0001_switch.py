"""Tuya switch device."""

from zha.quirks import TUYA_PLUG_ONOFF
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import (
    ExternalSwitchType,
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)
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


# TS0001 switch modules whose firmware exposes seMetering (0x0702) and
# haElectricalMeasurement (0x0B04) clusters, but whose boards have no metering
# front-end: every measurement attribute (including rms_voltage) always reads
# as a constant 0. Verified with on-device reads under a real load; zigbee2mqtt
# classifies these fingerprints as plain switch modules without power
# monitoring (TS0001_switch_module / WHD02). The stub clusters are removed so
# ZHA does not create dead, always-zero W/V/A/kWh sensors and does not poll
# them every 30-45 seconds.
(
    TuyaQuirkBuilder("_TZ3000_tqlv4ug4", "TS0001")
    .applies_to("_TZ3000_prits6g4", "TS0001")
    .applies_to("_TZ3000_46t1rvdu", "TS0001")
    .applies_to("_TZ3000_fdxihpp7", "TS0001")
    .applies_to("_TZ3000_fdxihpp7", "TS000F")
    .tuya_enchantment()
    .removes(Metering.cluster_id)
    .removes(ElectricalMeasurement.cluster_id)
    .replace_cluster_occurrences(TuyaZBOnOffAttributeCluster)
    .replace_cluster_occurrences(TuyaZBE000Cluster)
    .replace_cluster_occurrences(TuyaZBExternalSwitchTypeCluster)
    .exposes_feature(TUYA_PLUG_ONOFF)
    .enum(
        attribute_name=TuyaZBExternalSwitchTypeCluster.AttributeDefs.external_switch_type.name,
        enum_class=ExternalSwitchType,
        cluster_id=TuyaZBExternalSwitchTypeCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
)
