"""Aqara W600 Radiator Thermostat Quirk."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, EntityPlatform, EntityType
import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeAccess, ZCLAttributeDef

ZCL_SYSTEM_MODE = Thermostat.AttributeDefs.system_mode
ZCL_RUNNING_STATE = Thermostat.AttributeDefs.running_state


THERMOSTAT_ENABLED_TO_SYSTEM_MODE_MAP = {
    0: Thermostat.SystemMode.Off,
    1: Thermostat.SystemMode.Heat,
}

SYSTEM_MODE_TO_THERMOSTAT_ENABLED_MAP = {
    Thermostat.SystemMode.Off: 0,
    Thermostat.SystemMode.Heat: 1,
    Thermostat.SystemMode.Auto: 1,
}


def valve_position_to_running_state(valve_position):
    """Convert the current valve position / pi heating demand to a ZCL running state."""

    if valve_position > 0:
        return Thermostat.RunningState.Heat_State_On

    return Thermostat.RunningState.Idle


def get_attribute_id_or_name(
    attribute: ZCLAttributeDef,
    attributes: dict[str | int, Any] | list[int | str],
) -> int | str | None:
    """Return the attribute id/name when the id/name of the attribute is in the attributes list or None otherwise."""

    if attribute.id in attributes:
        return attribute.id
    elif attribute.name in attributes:
        return attribute.name
    else:
        return None


class ThermostatCluster(CustomCluster, Thermostat):
    """Aqara W600 thermostat cluster."""

    # remove cooling mode
    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ) -> Any:
        """Redirect system_mode and running_state reads to vendor-specific cluster."""

        successful_r, failed_r = {}, {}
        remaining_attributes = attributes.copy()

        system_mode = get_attribute_id_or_name(ZCL_SYSTEM_MODE, attributes)
        if system_mode is not None:
            remaining_attributes.remove(system_mode)

            thermostat_id = CustomAqaraCluster.AttributeDefs.thermostat_enabled.id

            result = await self.endpoint.aqara_custom.read_attributes(
                [thermostat_id],
                allow_cache,
                only_cache,
                manufacturer,
            )

            failed_r.update(result[1])

            thermostat_enabled = result[0].get(thermostat_id)
            if thermostat_enabled is not None:
                successful_r[ZCL_SYSTEM_MODE.id] = (
                    THERMOSTAT_ENABLED_TO_SYSTEM_MODE_MAP[thermostat_enabled]
                )

        running_state = get_attribute_id_or_name(ZCL_RUNNING_STATE, attributes)
        if running_state is not None:
            remaining_attributes.remove(running_state)

            valve_position_id = CustomAqaraCluster.AttributeDefs.valve_position.id

            result = await self.endpoint.aqara_custom.read_attributes(
                [valve_position_id],
                allow_cache,
                only_cache,
                manufacturer,
            )

            failed_r.update(result[1])

            valve_position = result[0].get(valve_position_id)
            if valve_position is not None:
                successful_r[ZCL_RUNNING_STATE.id] = valve_position_to_running_state(
                    valve_position
                )

        if remaining_attributes:
            result = await super().read_attributes(
                remaining_attributes,
                allow_cache,
                only_cache,
                manufacturer,
                **kwargs,
            )

            successful_r.update(result[0])
            failed_r.update(result[1])

        return successful_r, failed_r

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: int | None = None,
        **kwargs,
    ) -> list:
        """Redirect system_mode writes to vendor-specific cluster."""

        result = []
        remaining_attributes = attributes.copy()

        system_mode = get_attribute_id_or_name(ZCL_SYSTEM_MODE, attributes)
        system_mode_value = None
        if system_mode is not None:
            remaining_attributes.pop(system_mode)
            system_mode_value = attributes.get(system_mode)

        thermostat_enabled = None
        if system_mode_value is not None:
            thermostat_enabled = SYSTEM_MODE_TO_THERMOSTAT_ENABLED_MAP.get(
                system_mode_value
            )

        if thermostat_enabled is not None:
            result += await self.endpoint.aqara_custom.write_attributes(
                {
                    CustomAqaraCluster.AttributeDefs.thermostat_enabled.id: thermostat_enabled
                }
            )

        if remaining_attributes:
            result += await super().write_attributes(attributes, manufacturer, **kwargs)

        return result

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Prevent bad system_mode attribute reports from device."""

        if attrid == ThermostatCluster.AttributeDefs.system_mode.id:
            return

        return super()._update_attribute(attrid, value)


class AqaraDisplayOrientation(t.enum8):
    """Aqara display orientation attribute values."""

    Normal = 0x00
    Flipped = 0x01


class AqaraValveAdaptStatus(t.enum8):
    """Aqara valve adapt status attribute values."""

    NotReady = 0x00
    ReadyToCalibrate = 0x01
    Error = 0x02
    CalibrationInProgress = 0x03


class CustomAqaraCluster(CustomCluster):
    """Custom Aqara W600 cluster."""

    cluster_id = t.uint16_t(0xFCC0)
    ep_attribute = "aqara_custom"

    class AttributeDefs(CustomCluster.AttributeDefs):
        """Aqara W600 manufacturer-specific attributes."""

        calibrate_valve: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0270),
            type=t.uint8_t,
        )

        calibrate_state: Final = ZCLAttributeDef(
            id=t.uint16_t(0x027B),
            type=AqaraValveAdaptStatus,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Report,
        )

        thermostat_enabled: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0271),
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
        )

        window_detection: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0273),
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
        )

        valve_detection: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0274),
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
        )

        child_lock: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0277),
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
        )

        display_orientation: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0330),
            type=AqaraDisplayOrientation,
            zcl_type=DataTypeId.uint8,
        )

        valve_position: Final = ZCLAttributeDef(
            id=t.uint16_t(0x0360),
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read | ZCLAttributeAccess.Report,
        )

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Redirect custom cluster reports to the thermostat cluster."""

        if attrid == CustomAqaraCluster.AttributeDefs.thermostat_enabled.id:
            self.endpoint.thermostat.update_attribute(
                ZCL_SYSTEM_MODE.id,
                THERMOSTAT_ENABLED_TO_SYSTEM_MODE_MAP[value],
            )

        if attrid == CustomAqaraCluster.AttributeDefs.valve_position.id:
            self.endpoint.thermostat.update_attribute(
                ZCL_RUNNING_STATE.id,
                valve_position_to_running_state(value),
            )

        super()._update_attribute(attrid, value)


(
    QuirkBuilder("Aqara", "lumi.airrtc.aeu005")
    .firmware_version_filter(min_version=0x0000192B)
    .replaces(ThermostatCluster)
    .replaces(CustomAqaraCluster)
    .write_attr_button(
        CustomAqaraCluster.AttributeDefs.calibrate_valve.name,
        1,
        CustomAqaraCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="calibrate_valve",
        fallback_name="Calibrate valve",
    )
    .enum(
        CustomAqaraCluster.AttributeDefs.calibrate_state.name,
        AqaraValveAdaptStatus,
        CustomAqaraCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="valve_adapt_status",
        fallback_name="Valve adaptation status",
    )
    .switch(
        CustomAqaraCluster.AttributeDefs.window_detection.name,
        CustomAqaraCluster.cluster_id,
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .switch(
        CustomAqaraCluster.AttributeDefs.child_lock.name,
        CustomAqaraCluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .enum(
        CustomAqaraCluster.AttributeDefs.display_orientation.name,
        AqaraDisplayOrientation,
        CustomAqaraCluster.cluster_id,
        translation_key="display_orientation",
        fallback_name="Display orientation",
    )
    .sensor(
        CustomAqaraCluster.AttributeDefs.valve_position.name,
        CustomAqaraCluster.cluster_id,
        unit=PERCENTAGE,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="pi_heating_demand",
        fallback_name="Pi heating demand",
    )
    .add_to_registry()
)
