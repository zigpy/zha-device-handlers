"""IKEA Vallhorn quirk."""

from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class IkeaVallhornManufSpecificConfig(CustomCluster):
    """Ikea Vallhorn manufacturer specific config cluster."""

    name = "IKEA manufacturer specific config"
    cluster_id = 0xFC81

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        on_only_when_dark: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
        )

        on_time: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
        )


(
    QuirkBuilder("IKEA of Sweden", "VALLHORN Wireless Motion Sensor")
    .replaces(IkeaVallhornManufSpecificConfig)
    .switch(
        IkeaVallhornManufSpecificConfig.AttributeDefs.on_only_when_dark.name,
        IkeaVallhornManufSpecificConfig.cluster_id,
        translation_key="on_only_when_dark",
        fallback_name="On only when dark",
    )
    .number(
        IkeaVallhornManufSpecificConfig.AttributeDefs.on_time.name,
        IkeaVallhornManufSpecificConfig.cluster_id,
        step=1,
        min_value=10,
        max_value=65534,
        unit=UnitOfTime.SECONDS,
        translation_key="on_time",
        fallback_name="On time",
    )
    .add_to_registry()
)
