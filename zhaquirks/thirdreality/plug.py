"""Third Reality plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime, UnitOfPower
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityPlugCluster(CustomCluster):
    """Third Reality's plug private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # reset the accumulated power of the plug
        reset_total_energy: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        # turn off delay
        countdown_to_turn_off: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        # turn on delay
        countdown_to_turn_on: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        
        
class ThirdRealityPlugClustergen3(CustomCluster):
    """Third Reality's plug gen3 private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # reset the accumulated power of the plug
        reset_total_energy: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        # turn off delay
        countdown_to_turn_off: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        # turn on delay
        countdown_to_turn_on: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
                
        # power rise threshold
        power_rise_threshold: Final = ZCLAttributeDef(
            id=0x0040,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        
        # power drop threshold
        power_drop_threshold: Final = ZCLAttributeDef(
            id=0x0041,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        # disable onoff
        metering_only_mode: Final = ZCLAttributeDef(
            id=0x0050,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
      
        
        
# single outlet plugs
(
    QuirkBuilder("Third Reality, Inc", "3RSP02028BZ")
    .applies_to("Third Reality, Inc", "3RSPE01044BZ")
    .replaces(ThirdRealityPlugCluster)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        translation_key="reset_total_energy",
        fallback_name="Reset total energy",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off",
        fallback_name="Countdown to turn off",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on",
        fallback_name="Countdown to turn on",
    )
    .add_to_registry()
)

(
    QuirkBuilder("Third Reality, Inc", "3RSP02064Z")
    .applies_to("Third Reality, Inc", "3RSPU01080Z")
    .applies_to("Third Reality, Inc", "3RSPE02065Z")
    .applies_to("Third Reality, Inc", "3RSP0186Z")
    .applies_to("Third Reality, Inc", "3RSPJ0187Z")
    .replaces(ThirdRealityPlugClustergen3)
    .write_attr_button(
        attribute_name=ThirdRealityPlugClustergen3.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugClustergen3.cluster_id,
        translation_key="reset_total_energy",
        fallback_name="Reset total energy",
    )
    .number(
        attribute_name=ThirdRealityPlugClustergen3.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugClustergen3.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off",
        fallback_name="Countdown to turn off",
    )
    .number(
        attribute_name=ThirdRealityPlugClustergen3.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugClustergen3.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on",
        fallback_name="Countdown to turn on",
    )
    .number(
        attribute_name=ThirdRealityPlugClustergen3.AttributeDefs.power_rise_threshold.name,
        cluster_id=ThirdRealityPlugClustergen3.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=3200,
        mode="box",
        unit=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        translation_key="power_rise_threshold",
        fallback_name="Power rise threshold",
    )
    .number(
        attribute_name=ThirdRealityPlugClustergen3.AttributeDefs.power_drop_threshold.name,
        cluster_id=ThirdRealityPlugClustergen3.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=3200,
        mode="box",
        unit=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        translation_key="power_drop_threshold",
        fallback_name="Power drop threshold",
    )
    .switch(
        cluster_id=ThirdRealityPlugClustergen3.cluster_id,
        attribute_name=ThirdRealityPlugClustergen3.AttributeDefs.metering_only_mode.name,
        translation_key="metering_only_mode",
        fallback_name="Metering only mode",
    )
    .add_to_registry()
)

# double outlet plugs
(
    QuirkBuilder("Third Reality, Inc", "3RDP01072Z")
    .applies_to("Third Reality, Inc", "3RWP01073Z")
    .replaces(ThirdRealityPlugCluster, endpoint_id=1)
    .replaces(ThirdRealityPlugCluster, endpoint_id=2)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        translation_key="reset_total_energy_left_bottom",
        fallback_name="Reset left/bottom total energy",  # ep1 is left
    )
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=2,
        translation_key="reset_total_energy_right_top",
        fallback_name="Reset right/top total energy",  # ep2 is right
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off_left_bottom",
        fallback_name="Countdown to turn off left/bottom",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off_right_top",
        fallback_name="Countdown to turn off right/top",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on_left_bottom",
        fallback_name="Countdown to turn on left/bottom",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on_right_top",
        fallback_name="Countdown to turn on right/top",
    )
    .add_to_registry()
)
