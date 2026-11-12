"""Niko Connected socket outlet (170-33505/170-34605)."""

from typing import Final

from zigpy import types as t
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.niko import NIKO, NIKO_MFG_CODE


class LedOffColor(t.enum24):
    """Color the status LED shows while the socket is turned off."""

    Off = 0x000000
    White = 0x0000FF
    Blue = 0x00FF00
    Red = 0xFF0000
    Purple = 0xFFFFFF


class NikoOutletConfigCluster(CustomCluster):
    """Niko manufacturer specific configuration cluster of the outlet."""

    cluster_id = 0xFC00
    ep_attribute = "niko_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attributes of the outlet configuration cluster."""

        # Color of the status LED while the socket is turned off. While the socket is
        # turned on, the selected color is only shown briefly and the LED returns to
        # white, so the attribute always reads white then.
        led_off_color: Final = ZCLAttributeDef(
            id=0x0100,
            type=LedOffColor,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        # 0 = locked (physical button disabled), 1 = unlocked (default)
        child_lock: Final = ZCLAttributeDef(
            id=0x0101,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        # 0 = status LED disabled, 1 = status LED enabled (default)
        led_enable: Final = ZCLAttributeDef(
            id=0x0104,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )

    async def bind(self):
        """Bind cluster and pre-load attributes."""
        attributes = [attr.name for attr in self.AttributeDefs]
        off_color = self.AttributeDefs.led_off_color.name

        # Reading the off color returns the color the LED shows at that moment (white
        # while the socket is turned on, blue while it blinks during pairing), not the
        # stored setting, and the socket is turned on while pairing or rejoining. So
        # never read it here. The factory default is off, so on a fresh pairing (nothing
        # cached yet) write that default instead. Later binds keep the cached value and
        # never overwrite a color chosen by the user.
        attributes.remove(off_color)
        if self.get(off_color) is None:
            self.create_catching_task(
                self.write_attributes({off_color: LedOffColor.Off})
            )

        self.create_catching_task(self.read_attributes(attributes))
        return await super().bind()


(
    QuirkBuilder(NIKO, "Connected socket outlet")
    .friendly_name(
        manufacturer="Niko",
        model="Connected socket outlet",
    )
    .replaces(NikoOutletConfigCluster)
    .switch(
        NikoOutletConfigCluster.AttributeDefs.child_lock.name,
        NikoOutletConfigCluster.cluster_id,
        off_value=1,
        on_value=0,
        entity_type=EntityType.CONFIG,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        NikoOutletConfigCluster.AttributeDefs.led_enable.name,
        NikoOutletConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .enum(
        NikoOutletConfigCluster.AttributeDefs.led_off_color.name,
        LedOffColor,
        NikoOutletConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="off_led_color",
        fallback_name="Off LED color",
    )
    # The socket reports voltage and current every few seconds with a small jitter,
    # which floods the recorder, so they are disabled by default. Power and energy stay
    # enabled.
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="rms_voltage",
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="rms_current",
        new_entity_registry_enabled_default=False,
    )
    .add_to_registry()
)
