"""Linxura Aura Smart Button with twelve buttons and standard battery reporting."""

from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import CLUSTER_ID, COMMAND, DOUBLE_PRESS, LONG_PRESS, SHORT_PRESS
from zhaquirks.linxura import LINXURA
from zhaquirks.linxura.button import LinxuraIASCluster


class LinxuraAuraIASCluster(LinxuraIASCluster):
    """Decode Aura's twelve buttons using the Linxura IAS event format."""

    button_count = 12


(
    QuirkBuilder(LINXURA, "Aura Smart Button")
    .replaces(LinxuraAuraIASCluster)
    .device_automation_triggers(
        {
            (press_type, f"button_{button}"): {
                COMMAND: f"button_{button}_{press_type}",
                CLUSTER_ID: IasZone.cluster_id,
            }
            for press_type in (SHORT_PRESS, DOUBLE_PRESS, LONG_PRESS)
            for button in range(1, 13)
        }
    )
    .add_to_registry()
)
