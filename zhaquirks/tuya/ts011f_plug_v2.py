"""Tuya TS011F plug variants handled by v2 quirks.

BSEED wall-mounted socket `_TZ3000_o1jzcxou` ships in two firmware flavors:
one that does not declare metering clusters at all (previously covered by the
v1 `Plug_v7` quirk) and one that exposes seMetering (0x0702) and
haElectricalMeasurement (0x0B04) as stubs answering every read with a constant
0 — the socket has no metering hardware (zigbee2mqtt: TS011F_plug_2, "Smart
plug (without power monitoring)").

This quirk covers both flavors: the stub clusters are removed when present, so
ZHA does not create dead, always-zero W/V/A/kWh sensors, while the Tuya on/off
extensions (child lock, backlight mode, power-on state) keep working.
"""

from zha.quirks import TUYA_PLUG_ONOFF
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.tuya import (
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZ3000_o1jzcxou", "TS011F")
    .tuya_enchantment()
    .removes(Metering.cluster_id)
    .removes(ElectricalMeasurement.cluster_id)
    .replace_cluster_occurrences(TuyaZBOnOffAttributeCluster)
    .replace_cluster_occurrences(TuyaZBE000Cluster)
    .replace_cluster_occurrences(TuyaZBExternalSwitchTypeCluster)
    .exposes_feature(TUYA_PLUG_ONOFF)
    .add_to_registry()
)
