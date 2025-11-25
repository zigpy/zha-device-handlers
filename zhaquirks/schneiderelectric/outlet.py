"""Schneider Electric (Wiser) Outlet Quirks."""

from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

from zhaquirks.schneiderelectric import SE_MANUF_NAME, SEBasic


class SEIndicatorLuminanceLevel(t.enum8):
    """Indicator luminance level."""

    Level100 = 0x00
    Level80 = 0x01
    Level60 = 0x02
    Level40 = 0x03
    Level20 = 0x04
    Level0 = 0x05


class SEIndicatorMode(t.enum8):
    """Indicator mode."""

    InverseOfOutput = 0x00
    FollowsOutput = 0x01
    AlwaysOff = 0x02
    AlwaysOn = 0x03


class SELocalControlMode(t.enum8):
    """Local control mode."""

    Active = 0x00
    Inactive = 0x01


class SEOutletConfiguration(CustomCluster):
    """Schneider Electric Outlet Configuration cluster."""

    cluster_id = 0xFC04
    name = "SEOutletConfiguration"

    class AttributeDefs(CustomCluster.AttributeDefs):
        """Attribute definitions."""

        se_indicator_luminance_level: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_indicator_mode: Final = ZCLAttributeDef(
            id=0x0002,
            type=SEIndicatorMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_local_control_mode: Final = ZCLAttributeDef(
            id=0x0050,
            type=SELocalControlMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )


class SEMeteringCluster(CustomCluster, Metering):
    """Custom Metering cluster to fix instantaneous demand value multiplied by 1000."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.instantaneous_demand.id:
            value = value / 1000
        super()._update_attribute(attrid, value)


(
    QuirkBuilder(SE_MANUF_NAME, "SOCKET/OUTLET/1")
    .applies_to(SE_MANUF_NAME, "SOCKET/OUTLET/2")
    .replaces(SEBasic, endpoint_id=6)
    .replaces(SEMeteringCluster, endpoint_id=6)
    .replaces(SEOutletConfiguration, endpoint_id=6)
    .enum(
        cluster_id=SEOutletConfiguration.cluster_id,
        endpoint_id=6,
        attribute_name=SEOutletConfiguration.AttributeDefs.se_indicator_luminance_level.name,
        enum_class=SEIndicatorLuminanceLevel,
        translation_key="indicator_luminance_level",
        fallback_name="Indicator luminance level",
    )
    .enum(
        cluster_id=SEOutletConfiguration.cluster_id,
        endpoint_id=6,
        attribute_name=SEOutletConfiguration.AttributeDefs.se_indicator_mode.name,
        enum_class=SEIndicatorMode,
        translation_key="indicator_mode",
        fallback_name="Indicator mode",
    )
    .enum(
        cluster_id=SEOutletConfiguration.cluster_id,
        endpoint_id=6,
        attribute_name=SEOutletConfiguration.AttributeDefs.se_local_control_mode.name,
        enum_class=SELocalControlMode,
        translation_key="local_control_mode",
        fallback_name="Local control mode",
    )
    .add_to_registry()
)
