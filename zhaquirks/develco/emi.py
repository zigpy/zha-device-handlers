"""Frient Electricity Meter Interface."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ManufacturerDevice(CustomDeviceV2):
    """Custom device class used to remap cluster IDs in requests."""

    async def request(
        self,
        *args,
        **kwargs,
    ):
        """Remap cluster IDs for clusters that substitute for others."""
        # TODO: verify these are always kwargs
        endpoint_id = kwargs["src_ep"]
        cluster_id = kwargs["cluster"]

        # ignore ZDO and narrow down to manufacturer specific clusters
        if endpoint_id != 0 and cluster_id >= 0xFC00:
            cluster = self.endpoints[endpoint_id].in_clusters.get(cluster_id)
            substitution_cluster = getattr(cluster, "SUBSTITUTION_FOR", None)

            if substitution_cluster:
                kwargs["cluster"] = t.ClusterId(substitution_cluster)

        return await super().request(
            *args,
            **kwargs,
        )


class ManufacturerMetering(CustomCluster):
    """Fake manufacturer specific cluster for Metering manufacturer attributes."""

    SUBSTITUTION_FOR: int = Metering.cluster_id
    cluster_id = 0xFD10  # TODO: use a different one? (0xEF01?)

    class AttributeDefs(BaseAttributeDefs):
        """Define manufacturer specific attributes."""

        pulse_configuration: Final = ZCLAttributeDef(
            id=0x0300,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


base_quirk = (
    QuirkBuilder()
    .adds(Metering, endpoint_id=2)  # TODO: remove, only for tests
    .replaces(ManufacturerMetering, endpoint_id=2)
    .device_class(ManufacturerDevice)
    .number(
        attribute_name=ManufacturerMetering.AttributeDefs.pulse_configuration.name,
        cluster_id=ManufacturerMetering.cluster_id,
        endpoint_id=2,
        min_value=50,
        max_value=10000,
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
