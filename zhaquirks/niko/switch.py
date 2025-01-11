"""Niko Connected Switches (552-721X1 and 552-721X2)."""

from zigpy import types as t
from zigpy.quirks.v2 import CustomCluster, EntityType, QuirkBuilder
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Scenes
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.niko import NIKO, NIKO_MFG_CODE


class NikoCluster(CustomCluster):
    """Niko custom cluster for device configuration."""

    attr_config = {}

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration."""
        await self.write_attributes(self.attr_config, manufacturer=NIKO_MFG_CODE)


class ButtonsDefaultAction(t.enum8):
    """Whether pressing buttons automatically triggers the corresponding switch."""

    Disabled = 0x01
    Enabled = 0x02  # Default


class LedsFunctionality(t.uint8_t):
    """Whether all status LEDs are enabled, or always off."""

    Disabled = 0x00
    Enabled = 0x01  # Default


class LedsAlert(t.uint24_t):
    """Sets all LEDs to an alert color."""

    Off = 0x000000  # Default
    White = 0x0000FF
    Blue = 0x00FF00
    Red = 0xFF0000
    Purple = 0xFFFFFF


class LedsAlertColors(t.enum32):
    """Alert colors for status LEDs."""

    Off = LedsAlert.Off
    White = LedsAlert.White
    Blue = LedsAlert.Blue
    Red = LedsAlert.Red
    Purple = LedsAlert.Purple


class LedSwitchSync(t.bitmap32):
    """Whether to synchronize a LED with its associated switch status."""

    Off = 0x00

    Led_1_On = 0x01  # Default
    Led_1_Inverted = 0x02

    Led_3_On = 0x10  # Default
    Led_3_Inverted = 0x20


class LedSwitchSyncOptions(t.enum8):
    """Synchronization options for status LED."""

    Off = 0x0
    On = 0x1
    Inverted = 0x2


class NikoConfigCluster(NikoCluster):
    """Niko cluster for device configuration."""

    cluster_id = 0xFC00
    ep_attribute = "niko_config"

    # pylint: disable=R0903
    class AttributeDefs(BaseAttributeDefs):
        """Attributes for general device configuration."""

        buttons_default_action = ZCLAttributeDef(
            id=0x0000,
            type=ButtonsDefaultAction,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        leds_alert = ZCLAttributeDef(
            id=0x0100,
            type=LedsAlert,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        leds_functionality = ZCLAttributeDef(
            id=0x0104,
            type=LedsFunctionality,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        leds_on = ZCLAttributeDef(
            id=0x0105,
            type=t.bitmap8,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        leds_switch_sync = ZCLAttributeDef(
            id=0x0107,
            type=t.bitmap32,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )

    attr_config = {
        AttributeDefs.leds_functionality.id: LedsFunctionality.Enabled,
    }


class ButtonStateReporting(t.bitmap8):
    """Report state changes for these buttons."""

    Off = 0b00000  # Default
    Button_1 = 0b00010
    Button_2 = 0b00100
    Button_3 = 0b01000
    Button_4 = 0b10000


class ButtonsState(t.bitmap32):
    """Combined state of all individual buttons."""

    Button_1_Short_Press = 0x00010
    Button_1_Short_Release = 0x00040
    Button_1_Long_Press = 0x00020
    Button_1_Long_Release = 0x00030

    Button_2_Short_Press = 0x00100
    Button_2_Short_Release = 0x00400
    Button_2_Long_Press = 0x00200
    Button_2_Long_Release = 0x00300

    Button_3_Short_Press = 0x01000
    Button_3_Short_Release = 0x04000
    Button_3_Long_Press = 0x02000
    Button_3_Long_Release = 0x03000

    Button_4_Short_Press = 0x10000
    Button_4_Short_Release = 0x40000
    Button_4_Long_Press = 0x20000
    Button_4_Long_Release = 0x30000


class NikoStateCluster(NikoCluster):
    """Niko cluster for device state."""

    cluster_id = 0xFC01
    ep_attribute = "niko_state"

    # pylint: disable=R0903
    class AttributeDefs(BaseAttributeDefs):
        """Attributes for state configuration."""

        report_button_state = ZCLAttributeDef(
            id=0x0001,
            type=ButtonStateReporting,
            access="rw",
            manufacturer_code=NIKO_MFG_CODE,
        )
        buttons_state = ZCLAttributeDef(
            id=0x0002,
            type=ButtonsState,
            access="p",
            manufacturer_code=NIKO_MFG_CODE,
        )

    attr_config = {
        AttributeDefs.report_button_state.id: ButtonStateReporting.Off
        | ButtonStateReporting.Button_1
        | ButtonStateReporting.Button_2
        | ButtonStateReporting.Button_3
        | ButtonStateReporting.Button_4
    }


class NikoQuirkBuilder(QuirkBuilder):
    """QuirkBuilder for Niko devices."""

    def __init__(self, model):
        """Initialize the quirk builder."""
        super().__init__(NIKO, model)
        self.replaces(NikoConfigCluster, endpoint_id=1)
        self.replaces(NikoStateCluster, endpoint_id=1)

    def setup_buttons(self):
        """Set up the device's physical buttons."""
        # Configuration entities
        self.switch(
            NikoConfigCluster.AttributeDefs.buttons_default_action.name,
            NikoConfigCluster.cluster_id,
            off_value=ButtonsDefaultAction.Disabled,
            on_value=ButtonsDefaultAction.Enabled,
            entity_type=EntityType.CONFIG,
            translation_key="switch_mode",
            fallback_name="Switch When Pressed",
        )
        self.switch(
            NikoConfigCluster.AttributeDefs.leds_functionality.name,
            NikoConfigCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="enabled_led_indicator",
            fallback_name="Enable LEDs",
            initially_disabled=True,
        )
        return self


(
    NikoQuirkBuilder("Single connectable switch,10A")
    .friendly_name(manufacturer="Niko", model="Connected single switch")
    .setup_buttons()
    .add_to_registry()
)

(
    NikoQuirkBuilder("Double connectable switch,10A")
    .friendly_name(manufacturer="Niko", model="Connected double switch")
    .setup_buttons()
    # Remove duplicated clusters in second endpoint
    .removes(Basic.cluster_id, endpoint_id=2)
    .removes(Identify.cluster_id, endpoint_id=2)
    .removes(Groups.cluster_id, endpoint_id=2)
    .removes(Scenes.cluster_id, endpoint_id=2)
    .removes(Diagnostic.cluster_id, endpoint_id=2)
    .removes(NikoConfigCluster.cluster_id, endpoint_id=2)
    .removes(NikoStateCluster.cluster_id, endpoint_id=2)
    .add_to_registry()
)
