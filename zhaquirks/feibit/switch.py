"""Quirk for FeiBit light switches to remove the LevelControl cluster."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.feibit import FEIBIT

(
    QuirkBuilder(FEIBIT, "FNB56-ZSW01LX2.0")
    .removes(LevelControl, endpoint_id=11)
    .add_to_registry()
)


(
    QuirkBuilder(FEIBIT, "FNB56-ZSW02LX2.0")
    .removes(LevelControl.cluster_id, endpoint_id=11)
    .removes(LevelControl.cluster_id, endpoint_id=12)
    .add_to_registry()
)


(
    QuirkBuilder(FEIBIT, "FNB56-ZSW03LX2.0")
    .removes(LevelControl.cluster_id, endpoint_id=1)
    .removes(LevelControl.cluster_id, endpoint_id=2)
    .removes(LevelControl.cluster_id, endpoint_id=3)
    .add_to_registry()
)
