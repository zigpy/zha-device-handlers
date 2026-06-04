"""Third Reality plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfPower, UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
     
class BasicClusterWithLedGen3(CustomCluster, Basic):
    """Basic cluster with red LED brightness custom attribute."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        # Red LED brightness adjustment
        red_led_brightness: Final = ZCLAttributeDef(
            id=0xFF01,
            type=t.uint8_t,
            manufacturer_code=0x1407,
        )


class ThirdRealityPlugCluster(CustomCluster):
    """Third Reality's plug private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # reset the accumulated power of the plug
        reset_total_energy: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            manufacturer_code=0x1407,
        )

        # turn off delay
        countdown_to_turn_off: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            manufacturer_code=0x1407,
        )

        # turn on delay
        countdown_to_turn_on: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            manufacturer_code=0x1407,
        )


class ThirdRealityPlugClusterGen2(CustomCluster):
    """Third Reality's plug private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # LED brightness adjustment
        red_led_brightness: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint8_t,
            manufacturer_code=0x1233,
        )

        # reset the accumulated power of the plug
        reset_total_energy: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            manufacturer_code=0x1233,
        )

        # turn off delay
        countdown_to_turn_off: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            manufacturer_code=0x1233,
        )

        # turn on delay
        countdown_to_turn_on: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            manufacturer_code=0x1233,
        )


class ThirdRealityPlugClusterGen3(CustomCluster):
    """Third Reality's plug gen3 private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # reset the accumulated power of the plug
        reset_total_energy: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            manufacturer_code=0x1407,
        )

        # turn off delay
        countdown_to_turn_off: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            manufacturer_code=0x1407,
        )

        # turn on delay
        countdown_to_turn_on: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            manufacturer_code=0x1407,
        )

        # power rise threshold
        power_rise_threshold: Final = ZCLAttributeDef(
            id=0x0040,
            type=t.uint16_t,
            manufacturer_code=0x1407,
        )

        # power drop threshold
        power_drop_threshold: Final = ZCLAttributeDef(
            id=0x0041,
            type=t.uint16_t,
            manufacturer_code=0x1407,
        )
        # disable onoff
        metering_only_mode: Final = ZCLAttributeDef(
            id=0x0050,
            type=t.uint8_t,
            manufacturer_code=0x1407,
        )


# single outlet plugs
(
    QuirkBuilder("Third Reality, Inc", "3RSP02028BZ")
    .applies_to("Third Reality, Inc", "3RSPE01044BZ")
    .replaces(ThirdRealityPlugClusterGen2)
    .write_attr_button(
        attribute_name=ThirdRealityPlugClusterGen2.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugClusterGen2.cluster_id,
        unique_id_suffix="reset_total_energy",
        translation_key="reset_total_energy",
        fallback_name="Reset total energy",
    )
    .number(
        attribute_name=ThirdRealityPlugClusterGen2.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugClusterGen2.cluster_id,
        unique_id_suffix="countdown_to_turn_off",
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
        attribute_name=ThirdRealityPlugClusterGen2.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugClusterGen2.cluster_id,
        unique_id_suffix="countdown_to_turn_on",
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
        attribute_name=ThirdRealityPlugClusterGen2.AttributeDefs.red_led_brightness.name,
        cluster_id=ThirdRealityPlugClusterGen2.cluster_id,
        unique_id_suffix="red_led_brightness",
        endpoint_id=1,
        min_value=0,
        max_value=100,
        mode="box",
        unit=PERCENTAGE,
        translation_key="red_led_brightness",
        fallback_name="Red LED brightness",
    )
    .add_to_registry()
)


(
    QuirkBuilder("Third Reality, Inc", "3RSP02064Z")
    .applies_to("Third Reality, Inc", "3RSPU01080Z")
    .applies_to("Third Reality, Inc", "3RSPE02065Z")
    .applies_to("Third Reality, Inc", "3RSP0186Z")
    .applies_to("Third Reality, Inc", "3RSPJ0187Z")
    .replaces(ThirdRealityPlugClusterGen3)
    .replaces(BasicClusterWithLedGen3)
    .write_attr_button(
        attribute_name=ThirdRealityPlugClusterGen3.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugClusterGen3.cluster_id,
        unique_id_suffix="reset_total_energy",
        translation_key="reset_total_energy",
        fallback_name="Reset total energy",
    )
    .number(
        attribute_name=ThirdRealityPlugClusterGen3.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugClusterGen3.cluster_id,
        unique_id_suffix="countdown_to_turn_off",
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
        attribute_name=ThirdRealityPlugClusterGen3.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugClusterGen3.cluster_id,
        unique_id_suffix="countdown_to_turn_on",
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
        attribute_name=ThirdRealityPlugClusterGen3.AttributeDefs.power_rise_threshold.name,
        cluster_id=ThirdRealityPlugClusterGen3.cluster_id,
        unique_id_suffix="power_rise_threshold",
        endpoint_id=1,
        min_value=0,
        max_value=3277,
        mode="box",
        unit=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        translation_key="power_rise_threshold",
        fallback_name="Power rise threshold",
    )
    .number(
        attribute_name=ThirdRealityPlugClusterGen3.AttributeDefs.power_drop_threshold.name,
        cluster_id=ThirdRealityPlugClusterGen3.cluster_id,
        unique_id_suffix="power_drop_threshold",
        endpoint_id=1,
        min_value=0,
        max_value=3277,
        mode="box",
        unit=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        translation_key="power_drop_threshold",
        fallback_name="Power drop threshold",
    )
    .switch(
        cluster_id=ThirdRealityPlugClusterGen3.cluster_id,
        attribute_name=ThirdRealityPlugClusterGen3.AttributeDefs.metering_only_mode.name,
        unique_id_suffix="metering_only_mode",
        translation_key="metering_only_mode",
        fallback_name="Metering only mode",
    )
    .number(
        attribute_name=BasicClusterWithLedGen3.AttributeDefs.red_led_brightness.name,
        cluster_id=BasicClusterWithLedGen3.cluster_id,
        unique_id_suffix="red_led_brightness",
        endpoint_id=1,
        min_value=0,
        max_value=100,
        mode="box",
        unit=PERCENTAGE,
        translation_key="red_led_brightness",
        fallback_name="Red LED brightness",
    )
    .add_to_registry()
)

# double outlet plugs
(
    QuirkBuilder("Third Reality, Inc", "3RDP01072Z")
    .replaces(ThirdRealityPlugCluster, endpoint_id=1)
    .replaces(ThirdRealityPlugCluster, endpoint_id=2)
    .replaces(BasicClusterWithLedGen3)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="reset_total_energy_left",
        endpoint_id=1,
        translation_key="reset_total_energy_left",
        fallback_name="Reset left total energy",  # ep1 is left
    )
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="reset_total_energy_right",
        endpoint_id=2,
        translation_key="reset_total_energy_right",
        fallback_name="Reset right total energy",  # ep2 is right
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_off_left",
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off_left",
        fallback_name="Countdown to turn off left",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_off_right",
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off_right",
        fallback_name="Countdown to turn off right",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_on_left",
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on_left",
        fallback_name="Countdown to turn on left",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_on_right",
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on_right",
        fallback_name="Countdown to turn on right",
    )
    .number(
        attribute_name=BasicClusterWithLedGen3.AttributeDefs.red_led_brightness.name,
        cluster_id=BasicClusterWithLedGen3.cluster_id,
        unique_id_suffix="-1-red_led_brightness",
        endpoint_id=1,
        min_value=0,
        max_value=100,
        mode="box",
        unit=PERCENTAGE,
        translation_key="red_led_brightness",
        fallback_name="Red LED brightness",
    )
    .add_to_registry()
)
(
    QuirkBuilder("Third Reality, Inc", "3RWP01073Z")
    .replaces(ThirdRealityPlugCluster, endpoint_id=1)
    .replaces(ThirdRealityPlugCluster, endpoint_id=2)
    .replaces(BasicClusterWithLedGen3)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,  # 1 reset total energy
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="reset_total_energy_bottom",
        endpoint_id=1,
        translation_key="reset_total_energy_bottom",
        fallback_name="Reset bottom total energy",  # ep1 is bottom
    )
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_total_energy.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="reset_total_energy_top",
        endpoint_id=2,
        translation_key="reset_total_energy_top",
        fallback_name="Reset top total energy",  # ep2 is top
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_off_bottom",
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off_bottom",
        fallback_name="Countdown to turn off bottom",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_off.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_off_top",
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_off_top",
        fallback_name="Countdown to turn off top",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_on_bottom",
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on_bottom",
        fallback_name="Countdown to turn on bottom",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.countdown_to_turn_on.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        unique_id_suffix="countdown_to_turn_on_top",
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="countdown_to_turn_on_top",
        fallback_name="Countdown to turn on top",
    )
    .number(
        attribute_name=BasicClusterWithLedGen3.AttributeDefs.red_led_brightness.name,
        cluster_id=BasicClusterWithLedGen3.cluster_id,
        unique_id_suffix="-2-red_led_brightness",
        endpoint_id=1,
        min_value=0,
        max_value=100,
        mode="box",
        unit=PERCENTAGE,
        translation_key="red_led_brightness",
        fallback_name="Red LED brightness",
    )
    .add_to_registry()
)
