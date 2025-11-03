"""Frient Electricity Meter Interface LED variant."""

from typing import Final

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
    .add_to_registry()
)
