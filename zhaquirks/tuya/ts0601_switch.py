"""Tuya DP-based switches."""

from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.tuya import PowerOnState
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import MoesBacklight, TuyaAttributesCluster


class TuyaElectricalMeasurement(TuyaAttributesCluster, ElectricalMeasurement):
    """Tuya custom Electrical Measurement cluster using TuyaAttributesCluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
    }

    def __init__(self, *args, **kwargs):
        """Init cluster and mark unused attributes as unsupported."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            ElectricalMeasurement.AttributeDefs.ac_frequency.id
        )
        self.add_unsupported_attribute(
            ElectricalMeasurement.AttributeDefs.power_factor.id
        )
        self.add_unsupported_attribute(
            ElectricalMeasurement.AttributeDefs.apparent_power.id
        )


# 1 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_7tdtqgwv", "TS0601")
    .applies_to("_TZE200_amp6tsvy", "TS0601")
    .applies_to("_TZE200_oisqyl4o", "TS0601")
    .applies_to("_TZ3000_uim07oem", "TS0601")
    .applies_to("_TZE200_wfxuhoea", "TS0601")
    .applies_to("_TZE200_tviaymwx", "TS0601")
    .applies_to("_TZE204_ptaqh9tk", "TS0601")
    .applies_to("_TZE200_d0ypnbvn", "TS0601")
    .applies_to("_TZE204_6fk3gewc", "TS0601")
    .applies_to("_TZE204_d0ypnbvn", "TS0601")
    .applies_to("_TZE204_v5xjyphj", "TS0601")
    .applies_to("_TZE204_gbagoilo", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 1 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE200_gbagoilo", "TS0601")
    .applies_to("_TZE284_xnwxmj8z", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .adds(TuyaElectricalMeasurement)
    .tuya_dp(
        dp_id=21,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=22,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=23,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 2 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_g1ib5ldv", "TS0601")
    .applies_to("_TZE200_wunufsil", "TS0601")
    .applies_to("_TZE200_nkjintbl", "TS0601")
    .applies_to("_TZE204_wvovwe9h", "TS0601")
    .applies_to("_TZE200_7deq70b8", "TS0601")
    .applies_to("_TZE204_nh9m9emk", "TS0601")
    .applies_to("_TZE200_wvovwe9h", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 2 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE200_nh9m9emk", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .adds(TuyaElectricalMeasurement)
    .tuya_dp(
        dp_id=21,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=22,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=23,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 3 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_tz32mtza", "TS0601")
    .applies_to("_TZE200_vhy3iakz", "TS0601")
    .applies_to("_TZE200_2hf7x9n3", "TS0601")
    .applies_to("_TZE200_kyfqmmyl", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 3 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE204_2imwyigp", "TS0601")
    .applies_to("_TZE200_2imwyigp", "TS0601")
    .applies_to("_TZE200_go3tvswy", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .adds(TuyaElectricalMeasurement)
    .tuya_dp(
        dp_id=21,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=22,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=23,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 4 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_aqnazj70", "TS0601")
    .applies_to("_TZE200_1ozguk6x", "TS0601")
    .applies_to("_TZE200_k6jhsr0q", "TS0601")
    .applies_to("_TZE200_1n2kyphz", "TS0601")
    .applies_to("_TZE200_mexisfik", "TS0601")
    .applies_to("_TZE204_58of2pfn", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 4 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE204_mexisfik", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .adds(TuyaElectricalMeasurement)
    .tuya_dp(
        dp_id=21,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=22,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .tuya_dp(
        dp_id=23,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 5 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_jwsjbxjs", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_onoff(dp_id=5)
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 5 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE200_leaqthqq", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_onoff(dp_id=5)
    .skip_configuration()
    .add_to_registry()
)

# 6 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE200_9mahtqtg", "TS0601")
    .applies_to("_TZE200_wnp4d4va", "TS0601")
    .applies_to("_TZE200_emxxanvi", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_onoff(dp_id=5)
    .tuya_onoff(dp_id=6)
    .skip_configuration()
    .add_to_registry()
)

# 8 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE200_wktrysab", "TS0601")
    .applies_to("_TZE204_wktrysab", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_onoff(dp_id=5)
    .tuya_onoff(dp_id=6)
    .tuya_onoff(dp_id=0x65)
    .tuya_onoff(dp_id=0x66)
    .skip_configuration()
    .add_to_registry()
)

# 12 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE204_dqolcpcp", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_onoff(dp_id=5)
    .tuya_onoff(dp_id=6)
    .tuya_onoff(dp_id=0x65)
    .tuya_onoff(dp_id=0x66)
    .tuya_onoff(dp_id=0x67)
    .tuya_onoff(dp_id=0x68)
    .tuya_onoff(dp_id=0x69)
    .tuya_onoff(dp_id=0x6A)
    .skip_configuration()
    .add_to_registry()
)

# 16 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE204_vmcgja59", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_onoff(dp_id=2)
    .tuya_onoff(dp_id=3)
    .tuya_onoff(dp_id=4)
    .tuya_onoff(dp_id=5)
    .tuya_onoff(dp_id=6)
    .tuya_onoff(dp_id=0x65)
    .tuya_onoff(dp_id=0x66)
    .tuya_onoff(dp_id=0x67)
    .tuya_onoff(dp_id=0x68)
    .tuya_onoff(dp_id=0x69)
    .tuya_onoff(dp_id=0x6A)
    .tuya_onoff(dp_id=0x6B)
    .tuya_onoff(dp_id=0x6C)
    .tuya_onoff(dp_id=0x6D)
    .tuya_onoff(dp_id=0x6E)
    .skip_configuration()
    .add_to_registry()
)
