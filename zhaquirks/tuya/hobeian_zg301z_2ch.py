"""HOBEIAN ZG-301Z-2CH - 2-channel switch module (Tuya ZB).

This is a Tuya ZB (0xEF00) module that only reports physical button presses on the
standard On/Off cluster after the Tuya "attribute read" spell is cast during device
configuration, so it uses `zhaquirks.builder.QuirkBuilder.tuya_enchantment` method.

It also supports setting the external switch type on 0xE001 despite not reporting
it, so the 0xE001 `HobeianExternalSwitchType` cluster is added and exposed as
a config select.

The device exposes a `start_up_on_off` select on each channel's On/Off cluster,
both named "Power-on behavior" by ZHA, which look identical in the HA UI. They
are replaced with per-channel selects named "Power-on behavior (CH1)" / "(CH2)".
"""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import OnOff, OnOffConfiguration, StartUpOnOff

from zhaquirks import CustomCluster
from zhaquirks.tuya import (
    TUYA_CLUSTER_E001_ID,
    ExternalSwitchType,
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class HobeianCH1OnOff(CustomCluster, OnOff):
    """OnOff cluster for channel 1."""

    name = "On/Off cluster for channel 1"


class HobeianCH2OnOff(CustomCluster, OnOff):
    """OnOff cluster for channel 2."""

    name = "On/Off cluster for channel 2"


class HobeianExternalSwitchType(TuyaZBExternalSwitchTypeCluster):
    """Switch type (toggle/state/momentary) cluster on 0xE001."""

    name = "Tuya Switch type"


class HobeianOnOffConfiguration(CustomCluster, OnOffConfiguration):
    """Customized name handler for standard OnOffConfiguration."""

    name = "On/Off Configuration"


class HobeianTuyaE000Cluster(TuyaZBE000Cluster):
    """Customized name handler for Tuya private E000 cluster."""

    name = "Tuya Linkage/Config"


class HobeianTuyaE002Cluster(CustomCluster):
    """Customized name handler for Tuya private E002 cluster."""

    cluster_id = 0xE002
    name = "Tuya Binding/Config"


class HobeianTuyaEE00Cluster(CustomCluster):
    """Customized name handler for Tuya private EE00 cluster."""

    cluster_id = 0xEE00
    name = "Tuya Private Settings"


class HobeianTuyaEF00Cluster(CustomCluster):
    """Customized name handler for Tuya private EF00 cluster."""

    cluster_id = 0xEF00
    name = "Tuya Data Tunnel"


(
    TuyaQuirkBuilder("HOBEIAN", "ZG-301Z-2CH")
    .tuya_enchantment()
    .replaces(HobeianCH1OnOff, endpoint_id=1)
    .replaces(HobeianCH2OnOff, endpoint_id=2)
    # keep 0xE001 on ep1 even though the raw device doesn't report it.
    # It is verified that the actual module's firmware supports it,
    # returns relevant values and properly reacts to changes.
    .replaces(
        HobeianExternalSwitchType,
        cluster_id=TUYA_CLUSTER_E001_ID,
        endpoint_id=1,
    )
    # keep nicer names for the standard/Tuya clusters (no builder rename API; the
    # only mechanism is a naming subclass via .replaces(), same as in ts000f.py)
    .replaces(HobeianTuyaE000Cluster, endpoint_id=1)
    .replaces(HobeianTuyaE002Cluster, endpoint_id=1)
    .replaces(HobeianTuyaEE00Cluster, endpoint_id=1)
    .replaces(HobeianTuyaEF00Cluster, endpoint_id=1)
    .replaces(HobeianOnOffConfiguration, endpoint_id=1)
    # the raw device reports device_type ON_OFF_LIGHT on both endpoints; force the
    # channels to present as switches (otherwise they'd become lighting entities)
    .replaces_endpoint(1, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .replaces_endpoint(2, device_type=zha.DeviceType.ON_OFF_SWITCH)
    # replace the identically-named ZHA-native "Power on behavior" selects (one per
    # channel, both named "Power-on behavior") with per-channel named selects so the
    # two entries are distinguishable in the HA UI.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="StartUpOnOff",
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="StartUpOnOff",
    )
    .enum(
        attribute_name=OnOff.AttributeDefs.start_up_on_off.name,
        enum_class=StartUpOnOff,
        cluster_id=OnOff.cluster_id,
        endpoint_id=1,
        # Need to specify unique_id_suffix to prevent collision
        # with the default value that would result in dropping
        # of this whole custom attribute
        unique_id_suffix="pon_behavior",
        translation_key="power_on_behavior_ch",
        translation_placeholders={"channel": "CH1"},
        fallback_name="Power-on behavior (CH1)",
    )
    .enum(
        attribute_name=OnOff.AttributeDefs.start_up_on_off.name,
        enum_class=StartUpOnOff,
        cluster_id=OnOff.cluster_id,
        endpoint_id=2,
        # Need to specify unique_id_suffix to prevent collision
        # with the default value that would result in dropping
        # of this whole custom attribute
        unique_id_suffix="pon_behavior",
        translation_key="power_on_behavior_ch",
        translation_placeholders={"channel": "CH2"},
        fallback_name="Power-on behavior (CH2)",
    )
    .enum(
        attribute_name="external_switch_type",
        enum_class=ExternalSwitchType,
        cluster_id=TUYA_CLUSTER_E001_ID,
        endpoint_id=1,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
)
