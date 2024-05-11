"""Quirks implementations for Schneider Electric devices."""

from collections.abc import Coroutine
from typing import Any, Final, Union

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, OnOff
from zigpy.zcl.clusters.lighting import Ballast
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

SE_MANUF_NAME = "Schneider Electric"
SE_MANUF_ID = 4190


class SEBasic(CustomCluster, Basic):
    """Schneider Electric manufacturer specific Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        # The Application FW Version attribute specifies the firmware version of the application. The format of this
        # attribute is XXX.YYY.ZZZ V.
        # XXX = major version
        # YYY = minor version
        # ZZZ = patch version
        # V = Build Type (One of the following: D = Development version, T0, T1 = Verification version, V = Validation
        # version, R = Official Release version).
        se_application_fw_version: Final = ZCLAttributeDef(
            id=0xE001,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        # The Application HWVersion attribute specifies the hardware version of the application design in format
        # AAA.BBB.CCC. Meaning:
        # AAA - major version
        # BBB - minor version
        # CCC - patch version
        # If version is 000.000.000, HW version is not available.
        se_application_hw_version: Final = ZCLAttributeDef(
            id=0xE002,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        # Device serial number. Hexadecimal string of 15 chars length.
        se_device_serial_number: Final = ZCLAttributeDef(
            id=0xE004,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        # The ProductIdentifier attribute specifies the unique internal numerical identifier of the product. See device
        # description for this value.
        se_product_identifier: Final = ZCLAttributeDef(
            id=0xE007,
            type=t.enum16,
            is_manufacturer_specific=True,
        )
        # The ProductRange attribute specifies the name of the range to which the product belongs.
        se_product_range: Final = ZCLAttributeDef(
            id=0xE008,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        # The ProductModel attribute specifies the name of the product model. Same value as model identifier attribute
        # 0x0005.
        se_product_model: Final = ZCLAttributeDef(
            id=0xE009,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        # The ProductFamily attribute specifies the name of the family to which the product belongs.
        se_product_family: Final = ZCLAttributeDef(
            id=0xE00A,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        # VendorURL, value: "http://www.schneider-electric.com"
        se_vendor_url: Final = ZCLAttributeDef(
            id=0xE00B,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )


class SEOnTimeReloadOptions(t.bitmap8):
    """Valid values for the SE OnTimeReloadOptions attr."""

    # OnTimeReload timer can be canceled by receiving OFF command -> light is going OFF immediately.
    # If this bit is not set, the timer can not be canceled, it is always restarted.
    OnTimeReloadCanceledByOffCommand = 0x1

    # Impulse mode active. Whenever output should be switched ON, it will be switched ON only for 200msec.
    # OnTimeReload attributes is ignored, also bit0 inside this attribute has no sense. If this bit is not set,
    # impulse mode is disabled.
    ImpulseMode = 0x2


class SEOnOff(CustomCluster, OnOff):
    """Schneider Electric manufacturer specific OnOff cluster."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        # Has meaning only if attribute OnTimeReload is not 0. Defines number of seconds before the light is switched
        # off automatically when the user is somehow inform the light will be switched off automatically. Value 0 or
        # 0xFFFF disables pre-warning. For switch is just short switch OFF and ON, for dimmer device goes to 60
        # percent and starts slowly dim down. During this time user can reload the time and postpone automatic switch
        # off for time defined in OnTimeReload. If you enter value greater than 6553, after reboot you will read again
        # value 6553. If you enter 0xFFFF, functionality will be disabled.
        se_pre_warning_time: Final = ZCLAttributeDef(
            id=0xE000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        # Defines number of seconds before the light is switched off automatically. Time is in seconds.
        # Value 0 disable the functionality. When brightness is changed, or ON command is received, timer is always
        # restarted. Check OnTimeReloadOptions for possible impulse mode (if attribute is implemented).
        se_on_time_reload: Final = ZCLAttributeDef(
            id=0xE001,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )

        se_on_time_reload_options: Final = ZCLAttributeDef(
            id=0xE002,
            type=SEOnTimeReloadOptions,
            is_manufacturer_specific=True,
        )


class SEControlMode(t.enum8):
    """Dimming mode for PUCK/DIMMER/* and NHROTARY/DIMMER/1."""

    Auto = 0
    RC = 1
    RL = 2
    RL_LED = 3


class SEWiringMode(t.enum8):
    """Dimmer wiring mode.  Default value depends on how the dimmer is connected to the mains."""

    TwoWiredMode = 0
    ThreeWiredMode = 1


class SEDimmingCurve(t.enum8):
    """Dimmer dimming curve."""

    Logarithmic = 0
    Linear = 1  # Not supported in current FW, but defined in the spec
    Exponential = 2  # Not supported in current FW, but defined in the spec


class SEBallast(CustomCluster, Ballast):
    """Schneider Electric Ballast cluster."""

    manufacturer_id_override = SE_MANUF_ID

    class AttributeDefs(Ballast.AttributeDefs):
        """Attribute definitions."""

        se_control_mode: Final = ZCLAttributeDef(
            id=0xE000, type=SEControlMode, is_manufacturer_specific=True
        )
        se_wiring_mode: Final = ZCLAttributeDef(
            id=0xE002, type=t.enum8, is_manufacturer_specific=True
        )
        se_dimming_curve: Final = ZCLAttributeDef(
            id=0xE002, type=t.enum8, is_manufacturer_specific=True
        )


class SEWindowCovering(CustomCluster, WindowCovering):
    """Schneider Electric manufacturer specific Window Covering cluster."""

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Attribute definitions."""

        unknown_attribute_65533: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        lift_duration: Final = ZCLAttributeDef(
            id=0xE000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57360: Final = ZCLAttributeDef(
            id=0xE010,
            type=t.bitmap8,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57362: Final = ZCLAttributeDef(
            id=0xE012,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57363: Final = ZCLAttributeDef(
            id=0xE013,
            type=t.bitmap8,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57364: Final = ZCLAttributeDef(
            id=0xE014,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57365: Final = ZCLAttributeDef(
            id=0xE015,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57366: Final = ZCLAttributeDef(
            id=0xE016,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57367: Final = ZCLAttributeDef(
            id=0xE017,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid: Union[int, t.uint16_t], value: Any):
        if attrid == WindowCovering.AttributeDefs.current_position_lift_percentage.id:
            # Invert the percentage value
            value = 100 - value
        super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args: Any,
        **kwargs: Any,
    ) -> Coroutine:
        """Override the command method to invert the percent lift value."""
        command = self.server_commands[command_id]

        # Override default command to invert percent lift value.
        if command.id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            percent = args[0]
            percent = 100 - percent
            return await super().command(command_id, percent, **kwargs)

        return await super().command(command_id, *args, **kwargs)


class SESwitchIndication(t.enum8):
    """Available LED indicator signal combinations.

    Shutter movement can be indicated with a red LED signal. A green LED
    light permanently provides orientation, if desired.
    """

    # For lights: LED is on when load is on.  For shutter controllers: red LED is on while shutter is moving.
    FollowsLoad = 0x00
    # For lights: LED is always on. For shutter controllers: red LED is on while shutter is moving, green LED indicates
    # direction.
    AlwaysOn = 0x01
    # For lights: LED is on when load is off.  For shutter controllers: red LED is never on, green LED indicates
    # direction.
    InverseOfLoad = 0x02
    # LED(s) are always off.
    AlwaysOff = 0x03


class SESwitchAction(t.enum8):
    """Valid values for the SE SwitchAction attribute."""

    # Behave like a light switch (Up = On, Down = Off)
    Light = 0x00
    # Behave like an inverted light switch (Up = Off, Down = On)
    LightOpposite = 0xFE
    # Behave like a dimmer (Up/rotate right = on and/or dim up, Down/rotate left = off and/or dim down)
    Dimmer = 0x01
    # Behave like an inverted dimmer (Up/rotate right = off and/or dim down, Down/rotate left = on and/or dim up)
    DimmerOpposite = 0xFD
    # Behave like a standard shutter controller (up/rotate right = move shutter up, down/rotate left = move shutter
    # down, short press to stop movement)
    StandardShutter = 0x02
    # Behave like an inverted standard shutter controller (up/rotate right = move shutter down, down/rotate left = move
    # shutter up, short press to stop movement)
    StandardShutterOpposite = 0xFC
    # Behave like a Schneider shutter controller using SE custom Window Covering cluster (up/rotate right = move
    # shutter up, down/rotate left = move shutter down, short press to stop movement)
    SchneiderShutter = 0x03
    # Behave like an inverted Schneider shutter controller using SE custom Window Covering cluster (up/rotate right =
    # move shutter down, down/rotate left = move shutter up, short press to stop movement)
    SchneiderShutterOpposite = 0xFB
    # Recall scenes according to the Up/DownSceneID attributes, and group using the Up/DownGroupID attributes.
    Scene = 0x04
    # No observable function?
    ToggleLight = 0x05
    # No observable function?
    ToggleDimmer = 0x06
    # No observable function?
    AlternateLight = 0x07
    # No observable function?
    AlternateDimmer = 0x08
    NotUsed = 0x7F


class SESpecific(CustomCluster):
    """Schneider Electric manufacturer specific cluster."""

    name = "Schneider Electric Manufacturer Specific"
    ep_attribute = "schneider_electric_manufacturer"
    cluster_id = 0xFF17

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        se_switch_indication: Final = ZCLAttributeDef(
            id=0x0000,
            type=SESwitchIndication,
            is_manufacturer_specific=True,
        )
        # Default values depends on endpoint and device type. More info you find in device description.
        se_switch_actions: Final = ZCLAttributeDef(
            id=0x0001,
            type=SESwitchAction,
            is_manufacturer_specific=True,
        )
        # The UpSceneID attribute represents the Scene Id field value of any Scene command cluster transmitted by the
        # device when user activates is rocker up side according to the rocker configuration. See SwitchActions
        # attribute.
        se_up_scene_id: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        # The UpGroupID attribute represents the Group Id field value of any Scene command cluster transmitted by the
        # device when user activates is rocker up side according to the rocker configuration. Value greater than 0xFFF7
        # means, no command is sent. See SwitchActions attribute.
        se_up_group_id: Final = ZCLAttributeDef(
            id=0x0011,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        # The DownSceneID attribute represents the Scene Id field value of any Scene command cluster transmitted by the
        # device when user activates is rocker down side according to the rocker configuration. See SwitchActions
        # attribute.
        se_down_scene_id: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        # The DownGroupID attribute represents the Group Id field value of any Scene command cluster transmitted by the
        # device when user activates is rocker down side according to the rocker configuration. Value greater than
        # 0xFFF7 means, no command is sent. See SwitchActions attribute.
        se_down_group_id: Final = ZCLAttributeDef(
            id=0x0021,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        se_cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
