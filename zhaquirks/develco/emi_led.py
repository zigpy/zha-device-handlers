"""Frient Electricity Meter Interface LED variant."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks.builder import NumberDeviceClass, QuirkBuilder, UnitOfEnergy
from zhaquirks.clusters import CustomCluster
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
            access="w",
            is_manufacturer_specific=True,
        )

    async def write_attributes(self, attributes, allow_response=True, **kwargs):
        """Write attributes and cache values locally on success."""
        result = await super().write_attributes(attributes, **kwargs)
        if (
            result
            and isinstance(result[0], list)
            and all(r.status == Status.SUCCESS for r in result[0])
        ):
            for k, v in attributes.items():
                if isinstance(k, str) and k in self.attributes_by_name:
                    self._attr_cache[self.attributes_by_name[k].id] = v
                elif k in self.attributes:
                    self._attr_cache[k] = v
        return result


(
    QuirkBuilder("frient A/S", "EMIZB-141")
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
    .number(
        # Allow a user to set the current summation value,
        # so it can show the same value as the physical meter.
        attribute_name=ManufacturerMetering.AttributeDefs.current_summation.name,
        cluster_id=ManufacturerMetering.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=0xFFFFFFFFFFFF,  # uint48 max value
        step=1,
        unit=UnitOfEnergy.WATT_HOUR,
        mode="box",
        device_class=NumberDeviceClass.ENERGY,
        unique_id_suffix="current_summation_delivered",
        translation_key="current_summation",
        fallback_name="Current summation delivered",
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
