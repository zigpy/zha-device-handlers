"""BEGA luminaires."""

from __future__ import annotations

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.quirk_ids import BEGA_LIGHT_SWITCHABLE_WHITE


class LevelControlBega(CustomCluster, LevelControl):
    """Bega LevelControl cluster with custom attributes."""

    class AttributeDefs(LevelControl.AttributeDefs):
        """Attribute definitions for Bega LevelControl cluster."""

        # False: warm-white, True: cool-white
        switchable_white: Final = ZCLAttributeDef(
            id=0x4001, type=t.Bool, manufacturer_code=0x1105
        )

        # Color temperature for "False" in Kelvin, 0xFFFF when not supported
        switchable_color_temperature_1: Final = ZCLAttributeDef(
            id=0x4002, type=t.uint16_t, manufacturer_code=0x1105
        )

        # Color temperature for "True" in Kelvin, 0xFFFF when not supported
        switchable_color_temperature_2: Final = ZCLAttributeDef(
            id=0x4003, type=t.uint16_t, manufacturer_code=0x1105
        )


(
    QuirkBuilder()
    # Color temperature is not available on all of these lights, but the attributes are
    .applies_to("BEGA Gantenbrink-Leuchten KG", "Smart Dimmable Light")
    .applies_to("BEGA Gantenbrink-Leuchten KG", "Smart Dimmable Light Boost")
    # To add custom attributes
    .replaces(LevelControlBega)
    # Expose a feature to match the ZHA entity against
    .exposes_feature(BEGA_LIGHT_SWITCHABLE_WHITE)
    # To prevent non-functional binary sensor from being created
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .add_to_registry()
)
