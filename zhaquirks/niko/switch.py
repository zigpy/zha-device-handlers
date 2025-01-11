"""Niko Connected Switches (552-721X1 and 552-721X2)."""

from zigpy import types as t
from zigpy.quirks.v2 import CustomCluster, EntityType, QuirkBuilder
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Scenes
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    SHORT_PRESS,
    SHORT_RELEASE,
    ZHA_SEND_EVENT,
)
from zhaquirks.niko import NIKO, NIKO_MFG_CODE

BUTTONS = [
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
]

PRESS_TYPES = {
    0x1: SHORT_PRESS,
    0x4: SHORT_RELEASE,
    0x2: LONG_PRESS,
    0x3: LONG_RELEASE,
}


class NikoCluster(CustomCluster):
    """Niko custom cluster for device configuration."""

    attr_config = {}

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeReportedEvent.event_type, self._handle_attribute_event)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_attribute_event)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration."""
        await self.write_attributes(self.attr_config, manufacturer=NIKO_MFG_CODE)

    async def write_attributes(self, attributes, **kwargs):
        """Write the attributes and inform the config cluster."""
        result = await super().write_attributes(attributes, **kwargs)
        self._notify_cluster("niko_config", attributes)
        return result

    def _handle_attribute_event(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ):
        """Inform the buttons cluster of attribute updates."""
        attrid = event.attribute_id
        value = event.value
        self._notify_cluster("buttons", {attrid: value})

    def _notify_cluster(self, ep_attribute, attributes):
        """Notifies the cluster of attributes changes."""
        if ep_attribute != self.ep_attribute:
            cluster = getattr(self.endpoint, ep_attribute)
            for attrid, value in attributes.items():
                if isinstance(attrid, int):
                    attrid = self.attributes[attrid].name
                callback_name = f"{attrid}_changed"
                if hasattr(cluster, callback_name):
                    getattr(cluster, callback_name)(value)


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

    async def bind(self):
        """Bind cluster and pre-load attributes."""
        self.create_catching_task(self.read_attributes(self.attributes))
        return await super().bind()

    def led_1_on_changed(self, value: bool):
        """Process a write to the led_1_on attribute."""
        self.create_catching_task(self.write_led_on(0, value))

    def led_3_on_changed(self, value: bool):
        """Process a write to the led_3_on attribute."""
        self.create_catching_task(self.write_led_on(1, value))

    def led_1_switch_sync_changed(self, value: LedSwitchSyncOptions):
        """Process a write to the led_1_switch_sync attribute."""
        self.create_catching_task(self.write_led_switch_sync(0, value))

    def led_3_switch_sync_changed(self, value: LedSwitchSyncOptions):
        """Process a write to the led_3_switch_sync attribute."""
        self.create_catching_task(self.write_led_switch_sync(1, value))

    def alert_color_changed(self, value: LedsAlertColors):
        """Process a write to the alert_color attribute."""
        self.create_catching_task(self.write_leds_alert(value))

    async def write_led_on(self, led: int, value: bool):
        """Set the status LED to on or off using the leds_on attribute."""
        # Determine the previous state of the specific status LED
        state = self.get(self.AttributeDefs.leds_on.id) or 0
        mask = 1 << led
        previous = bool(state & mask)

        # If the status LED changed, update the leds_on attribute
        if value != previous:
            state = (state | mask) if value else state & ~mask
            await self.write_attributes({self.AttributeDefs.leds_on.id: state})

    async def write_led_switch_sync(self, led: int, value: LedSwitchSyncOptions):
        """Set LED/switch synchronization using the leds_switch_sync attribute."""
        # Determine previous state of individual LED
        state = self.get(self.AttributeDefs.leds_switch_sync.id) or 0
        shift = led << 2
        previous = state >> shift & 0xF

        # Update if the LED's state changed
        if value != previous:
            state = state & ~(0xF << shift) | (value << shift)
            await self.write_attributes({self.AttributeDefs.leds_switch_sync.id: state})

    async def write_leds_alert(self, value: LedsAlertColors):
        """Write the leds_alert attribute."""
        await self.write_attributes({self.AttributeDefs.leds_alert.id: value})


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


class ButtonsCluster(NikoCluster, LocalDataCluster):
    """Virtual cluster to manage individual button state and attributes."""

    cluster_id = 0xFC02
    ep_attribute = "buttons"

    # pylint: disable=R0903
    class AttributeDefs(BaseAttributeDefs):
        """Attributes for button configuration."""

        # Button press state
        button_1_pressed = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            access="rp",
            is_manufacturer_specific=True,
        )
        button_2_pressed = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,
            access="rp",
            is_manufacturer_specific=True,
        )
        button_3_pressed = ZCLAttributeDef(
            id=0x0003,
            type=t.Bool,
            access="rp",
            is_manufacturer_specific=True,
        )
        button_4_pressed = ZCLAttributeDef(
            id=0x0004,
            type=t.Bool,
            access="rp",
            is_manufacturer_specific=True,
        )

        # Status lights
        led_1_on = ZCLAttributeDef(
            id=0x0011,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )
        led_3_on = ZCLAttributeDef(
            id=0x0013,
            type=t.Bool,
            access="rwp",
            is_manufacturer_specific=True,
        )

        # Status light synchronization with switches
        led_1_switch_sync = ZCLAttributeDef(
            id=0x0021,
            type=LedSwitchSyncOptions,
            access="rw",
            is_manufacturer_specific=True,
        )
        led_3_switch_sync = ZCLAttributeDef(
            id=0x0023,
            type=LedSwitchSyncOptions,
            access="rw",
            is_manufacturer_specific=True,
        )

        # Status light alerts
        alert_color = ZCLAttributeDef(
            id=0x0100,
            type=LedsAlertColors,
            access="rw",
            is_manufacturer_specific=True,
        )

    _VALID_ATTRIBUTES = [attr.id for attr in AttributeDefs]

    PRESSED_ATTRIBUTES = [
        AttributeDefs.button_1_pressed,
        AttributeDefs.button_2_pressed,
        AttributeDefs.button_3_pressed,
        AttributeDefs.button_4_pressed,
    ]
    LED_ON_ATTRIBUTES = [
        AttributeDefs.led_1_on,
        AttributeDefs.led_3_on,
    ]
    LED_SWITCH_SYNC_ATTRIBUTES = [
        AttributeDefs.led_1_switch_sync,
        AttributeDefs.led_3_switch_sync,
    ]

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self.presses = [0] * len(self.PRESSED_ATTRIBUTES)
        for attr in self.attributes:
            self.update_attribute(attr, t.Bool.false)

    def buttons_state_changed(self, state):
        """Emit events based on button state changes."""
        for b, button in enumerate(BUTTONS):
            code = state >> (4 * b + 4) & 0xF
            press = PRESS_TYPES.get(code)
            if press and self.presses[b] != code:
                self.presses[b] = code
                down = t.Bool(press in {SHORT_PRESS, LONG_PRESS})
                self._update_attribute(self.PRESSED_ATTRIBUTES[b].id, down)
                self.listener_event(
                    ZHA_SEND_EVENT,
                    f"{button}_{press}",
                    {BUTTON: button, PRESS_TYPE: press},
                )

    def leds_on_changed(self, value):
        """Reflect leds_on in individual led_on_x attributes."""
        for i, attr in enumerate(self.LED_ON_ATTRIBUTES):
            on = t.Bool(value >> i & 0b1)
            self._update_attribute(attr.id, on)

    def leds_switch_sync_changed(self, value):
        """Reflect leds_switch_sync in individual leds_switch_sync_x attributes."""
        for i, attr in enumerate(self.LED_SWITCH_SYNC_ATTRIBUTES):
            sync = (value >> 4 * i) & 0xF
            self._update_attribute(attr.id, sync)

    def leds_alert_changed(self, value: LedsAlert):
        """Mirror leds_alert in the alert_color property."""
        self._update_attribute(self.AttributeDefs.alert_color.id, value)


class NikoQuirkBuilder(QuirkBuilder):
    """QuirkBuilder for Niko devices."""

    def __init__(self, model):
        """Initialize the quirk builder."""
        super().__init__(NIKO, model)
        self.replaces(NikoConfigCluster, endpoint_id=1)
        self.replaces(NikoStateCluster, endpoint_id=1)
        self.adds(ButtonsCluster)

    def setup_buttons(self, button_count):
        """Set up the device's physical buttons."""
        # Button triggers
        self.device_automation_triggers(
            {
                (press_type, button): {COMMAND: f"{button}_{press_type}"}
                for press_type in PRESS_TYPES.values()
                for button in BUTTONS[:button_count]
            }
        )

        # Button entities
        for b, key in enumerate(BUTTONS[:button_count]):
            self.binary_sensor(
                ButtonsCluster.PRESSED_ATTRIBUTES[b].name,
                ButtonsCluster.cluster_id,
                entity_type=EntityType.STANDARD,
                translation_key=key,
                fallback_name=f"Button {b + 1}",
            )

        # Status LED entities
        for b, key in enumerate(BUTTONS[::2]):
            self.switch(
                ButtonsCluster.LED_ON_ATTRIBUTES[b].name,
                ButtonsCluster.cluster_id,
                entity_type=EntityType.STANDARD,
                translation_key=f"{key}_led_indicator",
                fallback_name=f"Button {2 * b + 1} LED",
                initially_disabled=True,
            )

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
        for b, key in enumerate(BUTTONS[::2]):
            self.enum(
                ButtonsCluster.LED_SWITCH_SYNC_ATTRIBUTES[b].name,
                LedSwitchSyncOptions,
                ButtonsCluster.cluster_id,
                entity_type=EntityType.CONFIG,
                translation_key=f"{key}_sync",
                fallback_name=f"Button {b + 1} LED Switch Sync",
            )
        self.enum(
            ButtonsCluster.AttributeDefs.alert_color.name,
            LedsAlertColors,
            ButtonsCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="alert",
            fallback_name="Alert",
            initially_disabled=True,
        )
        return self


(
    NikoQuirkBuilder("Single connectable switch,10A")
    .friendly_name(manufacturer="Niko", model="Connected single switch")
    .setup_buttons(2)
    .add_to_registry()
)

(
    NikoQuirkBuilder("Double connectable switch,10A")
    .friendly_name(manufacturer="Niko", model="Connected double switch")
    .setup_buttons(4)
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
