"""V2 quirks for Tuya wall switches and switch modules: TS0001-TS0004 and TS000F (with neutral), TS0011-TS0013 (no neutral)."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import (
    BaseEnchantedDevice,
    IndicatorMode,
    PowerOnState,
    TuyaZBOnOffAttributeCluster,
)


class EnchantedSwitchDevice(CustomZigpyDevice, BaseEnchantedDevice):
    """V2 device class that casts the Tuya unlock spell on configuration."""


class CustomElectricalMeasurement(ElectricalMeasurement, CustomCluster):
    """Electrical measurement cluster with corrected current divisor / multiplier."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
    }


class CustomMetering(Metering, CustomCluster):
    """Metering cluster with corrected unit, device type, multiplier and divisor."""

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.unit_of_measure.id: 0x00,  # kWh
        Metering.AttributeDefs.metering_device_type.id: 0x00,  # electric metering
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


# 1 gang switch (with neutral)
TS0001_MANUFACTURERS = (
    "_TZ3000_0ghwhypc",
    "_TZ3000_1adss9de",
    "_TZ3000_3a9beq8a",
    "_TZ3000_46t1rvdu",
    "_TZ3000_4rbqgcuv",
    "_TZ3000_5ng23zjs",
    "_TZ3000_afgzktgb",
    "_TZ3000_ark8nv4y",
    "_TZ3000_bhcpnvud",
    "_TZ3000_fdxihpp7",
    "_TZ3000_g92baclx",
    "_TZ3000_gjrubzje",
    "_TZ3000_hktqahrq",
    "_TZ3000_hzlsaltw",
    "_TZ3000_i9oy2rdq",
    "_TZ3000_iktiy8ue",
    "_TZ3000_ikuxinvo",
    "_TZ3000_jsfzkftc",
    "_TZ3000_kqvb5akv",
    "_TZ3000_kycczpw8",
    "_TZ3000_mkhkxx1p",
    "_TZ3000_mx3vgyea",
    "_TZ3000_npzfdcof",
    "_TZ3000_pgq7ormg",
    "_TZ3000_prits6g4",
    "_TZ3000_q6a3tepg",
    "_TZ3000_q8r0bbvy",
    "_TZ3000_qaabwu5c",
    "_TZ3000_qamj2vnn",
    "_TZ3000_qlai3277",
    "_TZ3000_qnejhcsu",
    "_TZ3000_qorepo2x",
    "_TZ3000_qsp2pwtf",
    "_TZ3000_rmjr4ufz",
    "_TZ3000_skueekg3",
    "_TZ3000_tgddllx4",
    "_TZ3000_tqlv4ug4",
    "_TZ3000_tygpxwqa",
    "_TZ3000_v7gnj3ad",
    "_TZ3000_veu2v775",
    "_TZ3000_x3ewpzyr",
    "_TZ3000_x8mbwtsz",
    "_TZ3000_xfxpoxe0",
    "_TZ3000_xkap8wtb",
    "_TZ3000_zojh9vz7",
    "_TZ3210_tqlv4ug4",
)

# 2 gang switch (with neutral)
TS0002_MANUFACTURERS = (
    "_TZ3000_01gpyda5",
    "_TZ3000_4xfqlgqo",
    "_TZ3000_54hjn4vs",
    "_TZ3000_5gey1ohx",
    "_TZ3000_7ed9cqgi",
    "_TZ3000_aa5t61rh",
    "_TZ3000_aaifmpuq",
    "_TZ3000_bvrlqyj7",
    "_TZ3000_eei0ubpy",
    "_TZ3000_fbjdkph9",
    "_TZ3000_fisb3ajo",
    "_TZ3000_hojntt34",
    "_TZ3000_huvxrx4i",
    "_TZ3000_hznzbl0x",
    "_TZ3000_i9w5mehz",
    "_TZ3000_in5qxhtt",
    "_TZ3000_irrmjcgi",
    "_TZ3000_lmlsduws",
    "_TZ3000_mtnpt6ws",
    "_TZ3000_mufwv0ry",
    "_TZ3000_ogpla3lh",
    "_TZ3000_qaa59zqd",
    "_TZ3000_ruxexjfz",
    "_TZ3000_zbfya6h0",
    "_TZ3000_zmy4lslw",
    "_TZ3210_6smingw0",
)

# 3 gang switch (with neutral)
TS0003_MANUFACTURERS = (
    "_TZ3000_4o16jdca",
    "_TZ3000_66fekqhh",
    "_TZ3000_aknpkt02",
    "_TZ3000_aracgljk",
    "_TZ3000_bvij6kod",
    "_TZ3000_empogkya",
    "_TZ3000_fawk5xjv",
    "_TZ3000_hbic3ka3",
    "_TZ3000_iv4eq7eh",
    "_TZ3000_lsunm46z",
    "_TZ3000_lubfc1t5",
    "_TZ3000_lvhy15ix",
    "_TZ3000_mhhxxjrs",
    "_TZ3000_mw1pqqqt",
    "_TZ3000_mzcp0of6",
    "_TZ3000_nnwehhst",
    "_TZ3000_nwidmc4n",
    "_TZ3000_odzoiovu",
    "_TZ3000_ok0ggpk7",
    "_TZ3000_pf7swkqp",
    "_TZ3000_pfc7i3kt",
    "_TZ3000_rhkfbfcv",
    "_TZ3000_uilitwsy",
    "_TZ3000_v4l4b0lp",
    "_TZ3000_vsasbzkf",
    "_TZ3210_ok0ggpk7",
)

# 4 gang switch (with neutral)
TS0004_MANUFACTURERS = (
    "_TZ3000_3n2minvf",
    "_TZ3000_5ajpkyq6",
    "_TZ3000_knoj8lpk",
    "_TZ3000_liygxtcq",
    "_TZ3000_ltt60asa",
    "_TZ3000_mmkbptmx",
    "_TZ3000_tyg4yiat",
)

# 1 gang switch (TS000F, with neutral)
TS000F_1G_MANUFACTURERS = (
    "_TZ3000_dlhhrhs8",
    "_TZ3000_fdxihpp7",
    "_TZ3000_hdc8bbha",
    "_TZ3000_hktqahrq",
    "_TZ3000_m9af2l6g",
    "_TZ3000_mx3vgyea",
    "_TZ3000_skueekg3",
    "_TZ3000_xkap8wtb",
    "_TZ3218_7fiyo3kv",
)

# 2 gang switch (TS000F, with neutral)
TS000F_2G_MANUFACTURERS = ("_TZ3000_m8f3z8ju",)

# 1 gang switch (no neutral)
TS0011_MANUFACTURERS = (
    "_TZ3000_ji4araar",
    "_TZ3000_qmi1cfuq",
    "_TZ3000_tw4ztbp4",
    "_TZ3000_txpirhfq",
)

# 2 gang switch (no neutral)
TS0012_MANUFACTURERS = (
    "_TZ3000_4zf0crgo",
    "_TZ3000_biakwrag",
    "_TZ3000_jl7qyupf",
    "_TZ3000_kpatq5pq",
    "_TZ3000_ljhbw1c9",
    "_TZ3000_nPGIPl5D",
)

# 3 gang switch (no neutral)
TS0013_MANUFACTURERS = (
    "_TZ3000_avotanj3",
    "_TZ3000_sznawwyw",
    "_TZ3000_t7ugva7q",
    "_TZ3000_ypgri8yz",
)


def _register_switch(
    model: str, manufacturers: tuple[str, ...], num_endpoints: int
) -> None:
    """Register a v2 quirk for a Tuya wall switch family."""
    builder = QuirkBuilder(manufacturers[0], model)
    for manufacturer in manufacturers[1:]:
        builder.applies_to(manufacturer, model)
    for ep_id in range(1, num_endpoints + 1):
        builder.replaces_endpoint(ep_id, device_type=zha.DeviceType.ON_OFF_SWITCH)
    builder.replace_cluster_occurrences(TuyaZBOnOffAttributeCluster)
    # No-op when the cluster isn't present (no-neutral variants).
    builder.replace_cluster_occurrences(CustomMetering)
    builder.replace_cluster_occurrences(CustomElectricalMeasurement)
    builder.zigpy_device_class(EnchantedSwitchDevice)
    # Suppress HA's auto-discovered backlight_mode select; we expose indicator_mode instead.
    builder.prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="backlight_mode",
    )
    builder.enum(
        TuyaZBOnOffAttributeCluster.AttributeDefs.indicator_mode.name,
        IndicatorMode,
        OnOff.cluster_id,
        endpoint_id=1,
        unique_id_suffix=f"{OnOff.cluster_id}-indicator_mode",
        translation_key="indicator_mode",
        fallback_name="Indicator mode",
    )
    builder.enum(
        TuyaZBOnOffAttributeCluster.AttributeDefs.power_on_state.name,
        PowerOnState,
        OnOff.cluster_id,
        endpoint_id=1,
        unique_id_suffix=f"{OnOff.cluster_id}-power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    builder.add_to_registry()


_register_switch("TS0001", TS0001_MANUFACTURERS, 1)
_register_switch("TS0002", TS0002_MANUFACTURERS, 2)
_register_switch("TS0003", TS0003_MANUFACTURERS, 3)
_register_switch("TS0004", TS0004_MANUFACTURERS, 4)
_register_switch("TS000F", TS000F_1G_MANUFACTURERS, 1)
_register_switch("TS000F", TS000F_2G_MANUFACTURERS, 2)
_register_switch("TS0011", TS0011_MANUFACTURERS, 1)
_register_switch("TS0012", TS0012_MANUFACTURERS, 2)
_register_switch("TS0013", TS0013_MANUFACTURERS, 3)
