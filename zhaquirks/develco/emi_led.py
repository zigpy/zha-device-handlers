"""Frient Electricity Meter Interface LED variant."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.develco import ManufacturerDeviceV2


class ManufacturerMetering(CustomCluster):
    """Fake manufacturer specific cluster for Metering manufacturer attributes."""

    SUBSTITUTION_FOR = Metering.cluster_id  # requires ManufacturerDeviceV2
    cluster_id = 0xFD10

    class AttributeDefs(BaseAttributeDefs):
        """Define manufacturer specific attributes."""

        pulse_configuration: Final = ZCLAttributeDef(
            id=0x0300,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        current_summation: Final = ZCLAttributeDef(
            id=0x0301,
            type=t.uint48_t,
            access="r",
            is_manufacturer_specific=True,
        )


class FrientMetering(CustomCluster, Metering):
    """Frient EMI P1 Metering cluster definition."""

    # fix device issue (conflicting with manufacturer specific interface mode attr)
    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.divisor.id: 1000,
        Metering.AttributeDefs.multiplier.id: 1,
    }

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Update attribute with value."""
        # prevent attribute_updated events for divisor and multiplier
        if attrid in (
            Metering.AttributeDefs.divisor.id,
            Metering.AttributeDefs.multiplier.id,
        ):
            return
        super()._update_attribute(attrid, value)


(
    QuirkBuilder("frient A/S", "EMIZB-141")
    .replaces(FrientMetering, endpoint_id=2)
    .replaces(ManufacturerMetering, endpoint_id=2)
    .device_class(ManufacturerDeviceV2)
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
    .write_attr_button(
        attribute_name=ManufacturerMetering.AttributeDefs.current_summation.name,
        attribute_value=0,
        cluster_id=ManufacturerMetering.cluster_id,
        endpoint_id=2,
        translation_key="reset_summation_delivered",
        fallback_name="Reset summation delivered",
    )
    .add_to_registry()
)
