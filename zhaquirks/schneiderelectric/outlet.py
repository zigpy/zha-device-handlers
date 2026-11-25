"""Schneider Electric (Wiser) Outlet Quirks."""

from typing import Final

from zha.application.helpers import write_attributes_safe
from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.number import NumberConfigurationEntity
from zha.units import PERCENTAGE
from zigpy import types as t
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.schneiderelectric import SE_MANUF_ID, SE_MANUF_NAME, SEBasic


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
    """Schneider Electric Outlet Configuration cluster (VISA config, 0xFC04)."""

    cluster_id = 0xFC04
    name = "SEOutletConfiguration"
    ep_attribute = "se_outlet_configuration"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # IndicatorLuminanceLevel: brightness of the indication front LED.
        # 0 = 100%, 1 = 80%, 2 = 60%, 3 = 40%, 4 = 20%, 5 = 0%.
        se_indicator_luminance_level: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=SE_MANUF_ID,
        )
        se_indicator_mode: Final = ZCLAttributeDef(
            id=0x0002,
            type=SEIndicatorMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            manufacturer_code=SE_MANUF_ID,
        )
        se_local_control_mode: Final = ZCLAttributeDef(
            id=0x0050,
            type=SELocalControlMode,
            access="rw",
            manufacturer_code=SE_MANUF_ID,
        )


class SEMeteringCluster(CustomCluster, Metering):
    """Custom Metering cluster to fix instantaneous demand value multiplied by 1000."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.instantaneous_demand.id:
            value = value / 1000
        super()._update_attribute(attrid, value)


class SEIndicatorLuminanceNumber(NumberConfigurationEntity):
    """Indicator LED brightness in percent; the device stores 0 = 100% ... 5 = 0%."""

    _attribute_name = (
        SEOutletConfiguration.AttributeDefs.se_indicator_luminance_level.name
    )
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 20
    _attr_native_unit_of_measurement = PERCENTAGE
    _server_cluster_config = {
        SEOutletConfiguration.cluster_id: ClusterConfig(
            attributes={
                SEOutletConfiguration.AttributeDefs.se_indicator_luminance_level: (
                    AttrConfig(read_on_startup=True)
                ),
            },
        ),
    }

    @property
    def native_value(self) -> float | None:
        """Return the brightness in percent."""
        value = self._cluster.get(self._attribute_name)
        if value is None:
            return None
        return 100 - 20 * value

    async def async_set_native_value(self, value: float) -> None:
        """Write the brightness, converted to the device's 0-5 level."""
        await write_attributes_safe(
            self._cluster, {self._attribute_name: round((100 - value) / 20)}
        )
        self.maybe_emit_state_changed_event()


(
    QuirkBuilder(SE_MANUF_NAME, "SOCKET/OUTLET/1")
    .applies_to(SE_MANUF_NAME, "SOCKET/OUTLET/2")
    .replaces(SEBasic, endpoint_id=6)
    .replaces(SEMeteringCluster, endpoint_id=6)
    .replaces(SEOutletConfiguration, endpoint_id=6)
    .adds_entity(
        SEIndicatorLuminanceNumber,
        endpoint_id=6,
        cluster_id=SEOutletConfiguration.cluster_id,
        unique_id_suffix=SEOutletConfiguration.AttributeDefs.se_indicator_luminance_level.name,
        translation_key="indicator_luminance_level",
        fallback_name="Indicator luminance level",
    )
    .enum(
        attribute_name=SEOutletConfiguration.AttributeDefs.se_indicator_mode.name,
        enum_class=SEIndicatorMode,
        cluster_id=SEOutletConfiguration.cluster_id,
        endpoint_id=6,
        translation_key="indicator_mode",
        fallback_name="Indicator mode",
    )
    .enum(
        attribute_name=SEOutletConfiguration.AttributeDefs.se_local_control_mode.name,
        enum_class=SELocalControlMode,
        cluster_id=SEOutletConfiguration.cluster_id,
        endpoint_id=6,
        translation_key="local_control_mode",
        fallback_name="Local control mode",
    )
    .add_to_registry()
)
