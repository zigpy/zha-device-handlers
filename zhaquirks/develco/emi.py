"""Frient Electricity Meter Interface."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import TypeValue, ZCLAttributeDef


class MeteringClusterEMI(CustomCluster, Metering):
    """Metering cluster."""

    class AttributeDefs(Metering.AttributeDefs):
        """Define custom attributes."""

        pulse_configuration: Final = ZCLAttributeDef(
            id=0xEF01,  # it's actually 0x0300 but this is with a manufacturer code
            type=t.uint16_t,
            is_manufacturer_specific=True,  # should automatically use 0x1015
        )

    # TODO: clean up and fix batch reads
    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ) -> Any:
        """Redirect reads of custom attribute."""
        # TODO: there's an issue with ZHA reading attributes in chunks during init,
        #  where the manufacturer code is not handled correctly if some attributes
        #  require it and some don't. We'll need to split up those reads later.

        if (
            len(attributes) == 1
            and self.find_attribute(attributes[0])
            == self.AttributeDefs.pulse_configuration
        ):
            # redirect to 0x0300 with manufacturer code
            return await super().read_attributes(
                [0x0300],
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=0x1015,
                **kwargs,
            )

        return await super().read_attributes(
            attributes, allow_cache, only_cache, manufacturer, **kwargs
        )

    # TODO: also clean up
    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: int | None = None,
        **kwargs,
    ) -> list:
        """Redirect writes of custom attribute."""
        # we can just get the first key (name or id) here if we only write one attribute
        if (
            len(attributes) == 1
            and self.find_attribute(key := next(iter(attributes)))
            == self.AttributeDefs.pulse_configuration
        ):
            # redirect to 0x0300 with manufacturer code and fixed type
            value = t.uint16_t(attributes[key])
            return await super().write_attributes_raw(
                [
                    foundation.Attribute(
                        attrid=0x0300, value=TypeValue(type=t.uint16_t, value=value)
                    )
                ],
                manufacturer=0x1015,
                **kwargs,
            )

        return await super().write_attributes(attributes, manufacturer, **kwargs)


base_quirk = (
    QuirkBuilder()
    .replaces(MeteringClusterEMI, endpoint_id=2)  # TODO: check if this ep is correct
    .number(
        attribute_name=MeteringClusterEMI.AttributeDefs.pulse_configuration.name,
        cluster_id=MeteringClusterEMI.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        step=1,
        unit="pulses/kWh",
        mode="box",
        translation_key="pulse_configuration",
        fallback_name="Pulse configuration",
    )
)

(
    base_quirk.clone()
    .applies_to("frient A/S", "EMIZB-141")
    .add_to_registry()
)  # fmt: skip


(
    base_quirk.clone()
    .applies_to("frient A/S", "EMIZB-151")
    # These endpoints are duplicates and completely broken: each one is a "mirror" of
    # endpoint 2 and will set up duplicate attribute reporting for every attribute, the
    # attribute reports will instead be emitted from endpoint 2!
    .prevent_default_entity_creation(endpoint_id=64)
    .prevent_default_entity_creation(endpoint_id=65)
    .prevent_default_entity_creation(endpoint_id=66)
    .prevent_default_entity_creation(endpoint_id=67)
    .add_to_registry()
)
