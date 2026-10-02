"""Tuya TS000F relay modules."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import PowerOnState, TuyaZBE000Cluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class Ts000fExternalSwitchType(t.enum8):
    """External switch type for TS000F relay modules.

    Note: the value order differs from the 0xE001 based
    ExternalSwitchType used by other Tuya devices.
    """

    Momentary = 0x00
    Toggle = 0x01
    State = 0x02


class Ts000fOnOffCluster(CustomCluster, OnOff):
    """OnOff cluster with the TS000F specific attributes."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        switch_type: Final = ZCLAttributeDef(id=0x8001, type=Ts000fExternalSwitchType)
        power_on_state: Final = ZCLAttributeDef(id=0x8002, type=PowerOnState)


(
    TuyaQuirkBuilder("_TZ3218_hdc8bbha", "TS000F")
    .tuya_enchantment()
    .replaces(Ts000fOnOffCluster)
    # give cluster 0xE000 its proper name
    .replaces(TuyaZBE000Cluster)
    .enum(
        attribute_name=Ts000fOnOffCluster.AttributeDefs.power_on_state.name,
        enum_class=PowerOnState,
        cluster_id=OnOff.cluster_id,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .enum(
        attribute_name=Ts000fOnOffCluster.AttributeDefs.switch_type.name,
        enum_class=Ts000fExternalSwitchType,
        cluster_id=OnOff.cluster_id,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
)
