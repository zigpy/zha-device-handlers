"""Quirk for the Heatzy Micro Duo."""

from typing import Final

from zha.application import EntityPlatform, EntityType
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    Status,
    WriteAttributesStatusRecord,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import QuirkBuilder, ReportingConfig
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
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=None,
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
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=None,
        )
        enabled: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            access="rp",
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands received by the endpoint."""

        # Although 0xFC01 is in the manufacturer-specific cluster range, this
        # protocol intentionally uses ordinary ZCL frames.  Declaring this is
        # essential: otherwise zigpy adds the device manufacturer code.
        start_ble_ota: Final = ZCLCommandDef(id=0x00, schema={}, manufacturer_code=None)
        stop_ble_ota: Final = ZCLCommandDef(id=0x01, schema={}, manufacturer_code=None)

    def _update_attribute(self, attrid: int, value: object) -> None:
        """Keep the local switch attribute aligned with the reported OTA state."""

        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.state.id:
            super()._update_attribute(
                self.AttributeDefs.enabled.id,
                _ble_ota_is_active(value),
            )

    async def write_attributes(self, attributes: dict, **kwargs) -> list:
        """Translate switch writes into the product's start and stop commands."""

        enabled = attributes.get(self.AttributeDefs.enabled.name)
        if enabled is None:
            enabled = attributes.get(self.AttributeDefs.enabled.id)
        if enabled is None:
            return await super().write_attributes(attributes, **kwargs)

        command = (
            self.ServerCommandDefs.start_ble_ota
            if enabled
            else self.ServerCommandDefs.stop_ble_ota
        )
        await self.command(command.id)
        await self.read_attributes([self.AttributeDefs.state.id])
        self._update_attribute(self.AttributeDefs.enabled.id, bool(enabled))
        return [[WriteAttributesStatusRecord(Status.SUCCESS)]]

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Read the device's BLE OTA state when ZHA configures the endpoint."""

        await self.read_attributes([self.AttributeDefs.state.id])


def _ble_ota_is_active(state: BleOtaState | None) -> bool:
    """Return whether a reported BLE OTA state represents an open window."""

    return state not in (None, BleOtaState.Disabled)


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
        attribute_initialized_from_cache=False,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=3600,
            reportable_change=1,
        ),
        translation_key="ble_ota_status",
        fallback_name="Bluetooth OTA status",
    )
    .switch(
        attribute_name=HeatzyBleOtaCluster.AttributeDefs.enabled.name,
        endpoint_id=11,
        cluster_id=HeatzyBleOtaCluster.cluster_id,
        unique_id_suffix="ble_ota",
        translation_key="ble_ota",
        fallback_name="Bluetooth OTA",
    )
    .add_to_registry()
)
