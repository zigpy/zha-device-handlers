"""Quirk for the Heatzy Micro Duo."""

from typing import Final

from zha.application import EntityPlatform, EntityType
from zha.application.platforms.switch import ConfigurableAttributeSwitch
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


class PilotWireMode(t.enum8):
    """Values defined by the Heatzy FP6 pilot-wire interface."""

    Off = 0x00
    Comfort = 0x01
    Eco = 0x02
    Frost_protection = 0x03
    Comfort_minus_1 = 0x04
    Comfort_minus_2 = 0x05


class BleOtaState(t.enum8):
    """States published by the Micro Duo BLE OTA cluster."""

    Disabled = 0x00
    Advertising = 0x01
    Connected = 0x02
    Receiving = 0x03
    Verifying = 0x04


class HeatzyPilotWireCluster(CustomCluster):
    """Pilot-wire cluster implemented by the Micro Duo firmware."""

    cluster_id = 0xFC00
    name = "Heatzy Pilot Wire"
    ep_attribute = "heatzy_pilot_wire"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        mode: Final = ZCLAttributeDef(
            id=0x0000,
            type=PilotWireMode,
            access="rwp",
        )


class HeatzyBleOtaCluster(CustomCluster):
    """BLE OTA control and state cluster implemented by the Micro Duo firmware."""

    cluster_id = 0xFC01
    name = "Heatzy BLE OTA"
    ep_attribute = "heatzy_ble_ota"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        state: Final = ZCLAttributeDef(
            id=0x0000,
            type=BleOtaState,
            access="rp",
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands received by the endpoint."""

        start_ble_ota: Final = ZCLCommandDef(id=0x00, schema={})
        stop_ble_ota: Final = ZCLCommandDef(id=0x01, schema={})


def _ble_ota_is_active(state: BleOtaState | None) -> bool:
    """Return whether a reported BLE OTA state represents an open window."""

    return state not in (None, BleOtaState.Disabled)


class HeatzyBleOtaSwitch(ConfigurableAttributeSwitch):
    """Control the BLE OTA window and reflect its reported state."""

    _attribute_name = HeatzyBleOtaCluster.AttributeDefs.state.name

    @property
    def is_on(self) -> bool:
        """Return whether the BLE OTA window is active."""

        return _ble_ota_is_active(self._cluster.get(self._attribute_name))

    async def async_turn_on_off(self, state: bool) -> None:
        """Open or close the BLE OTA window through its ZCL command."""

        command = (
            HeatzyBleOtaCluster.ServerCommandDefs.start_ble_ota
            if state
            else HeatzyBleOtaCluster.ServerCommandDefs.stop_ble_ota
        )
        await self._cluster.command(command.id)


(
    QuirkBuilder("Heatzy", "micro-duo")
    .replaces(HeatzyPilotWireCluster, endpoint_id=1)
    .replaces(HeatzyBleOtaCluster, endpoint_id=11)
    .enum(
        attribute_name=HeatzyPilotWireCluster.AttributeDefs.mode.name,
        enum_class=PilotWireMode,
        cluster_id=HeatzyPilotWireCluster.cluster_id,
        endpoint_id=1,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot wire mode",
    )
    .enum(
        attribute_name=HeatzyBleOtaCluster.AttributeDefs.state.name,
        enum_class=BleOtaState,
        cluster_id=HeatzyBleOtaCluster.cluster_id,
        endpoint_id=11,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="ble_ota_status",
        fallback_name="Bluetooth OTA status",
    )
    .adds_entity(
        HeatzyBleOtaSwitch,
        endpoint_id=11,
        cluster_id=HeatzyBleOtaCluster.cluster_id,
        force_create=True,
        unique_id_suffix="ble_ota",
        translation_key="ble_ota",
        fallback_name="Bluetooth OTA",
    )
    .add_to_registry()
)
