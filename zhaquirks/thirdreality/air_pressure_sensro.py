"""Third Reality air pressure sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfPressure
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityAirPressureSensorCluster(CustomCluster):
    """Third Reality's air pressure sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        send_command_up_threshold: Final = ZCLAttributeDef(
            id=0x0040,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        send_command_down_threshold: Final = ZCLAttributeDef(
            id=0x0041,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RAP0149BZ")
    .replaces(ThirdRealityAirPressureSensorCluster)
    .number(
        attribute_name=ThirdRealityAirPressureSensorCluster.AttributeDefs.send_command_down_threshold.name,
        cluster_id=ThirdRealityAirPressureSensorCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfPressure.PA,
        device_class=NumberDeviceClass.PRESSURE,
        translation_key="send_command_down_threshold",
        fallback_name="Send command down threshold",
    )
    .number(
        attribute_name=ThirdRealityAirPressureSensorCluster.AttributeDefs.send_command_up_threshold.name,
        cluster_id=ThirdRealityAirPressureSensorCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfPressure.PA,
        device_class=NumberDeviceClass.PRESSURE,
        translation_key="send_command_up_threshold",
        fallback_name="Send command up threshold",
    )
    .add_to_registry()
)
