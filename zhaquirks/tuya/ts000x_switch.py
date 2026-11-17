"""Tuya TS000X multi-gang switch modules without metering hardware.

These fingerprints expose seMetering (0x0702) and haElectricalMeasurement
(0x0B04) clusters from Tuya's shared TS000x firmware, but the boards have no
metering front-end: every measurement attribute (including rms_voltage) always
reads back as a constant 0. Long-term recorder statistics on live devices show
years of all-zero readings under daily real load. zigbee2mqtt classifies the
TS0002/TS0004 fingerprints as plain switch modules (TS0002_basic /
TS0004_switch_module_2); _TZ3000_ly9apzky (TS0003) is not listed in
zigbee2mqtt and is included based on a live unit showing the same all-zero
behavior.

The quirk removes the two stub clusters so ZHA does not create dead,
always-zero W/V/A/kWh sensors (and does not poll them every 30-45 seconds),
keeps the Tuya on/off extensions (backlight mode / power-on state selects) and
exposes the external switch type selector, matching zigbee2mqtt's exposes.
"""

from zha.quirks import TUYA_PLUG_ONOFF
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import EntityType
from zhaquirks.tuya import (
    ExternalSwitchType,
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZ3000_eei0ubpy", "TS0002")
    .applies_to("_TZ3000_lmlsduws", "TS0002")
    .applies_to("_TZ3000_zmy4lslw", "TS0002")
    .applies_to("_TZ3000_ly9apzky", "TS0003")
    .applies_to("_TZ3000_knoj8lpk", "TS0004")
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
