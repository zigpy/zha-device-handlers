"""Develco smart plugs."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import UnitOfTemperature
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import DeviceTemperature, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef

MANUFACTURER_CODE = 0x1015


class VendorOnOff(CustomCluster, OnOff):
    """OnOff with manufacturer-specific commands."""

    def __init__(self, *args, **kwargs) -> None:
        """Seed attributes so entities start with a defined value."""
        super().__init__(*args, **kwargs)
        # Set defaults so HA shows 0 until a value is written.
        self._update_attribute(self.AttributeDefs.mode_on_value.id, 0)
        self._update_attribute(self.AttributeDefs.mode_off_value.id, 0)

    class AttributeDefs(OnOff.AttributeDefs):
        """Attributes used to drive the vendor commands."""

        mode_value: Final = ZCLAttributeDef(
            id=0x8100, type=t.uint8_t, access="r", manufacturer_code=MANUFACTURER_CODE
        )
        mode_on_value: Final = ZCLAttributeDef(id=0x8102, type=t.uint8_t, access="w")
        mode_off_value: Final = ZCLAttributeDef(id=0x8103, type=t.uint8_t, access="w")
        return_to_state: Final = ZCLAttributeDef(
            id=0x8101, type=t.Bool, access="r", manufacturer_code=MANUFACTURER_CODE
        )

    async def _send_safe_mode(self, command_id: int, mode_value: int) -> None:
        """Send manufacturer-specific safe-mode command without overriding On/Off."""
        cmd_def = foundation.ZCLCommandDef(
            id=command_id,
            name="safe_mode",
            schema={"mode": t.uint8_t},
            is_manufacturer_specific=True,
        ).with_compiled_schema()
        await self.request(
            False,
            command_id,
            cmd_def.schema,
            mode=mode_value,
            manufacturer=MANUFACTURER_CODE,
            expect_reply=False,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, int],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate mode writes into manufacturer-specific commands."""
        attributes_copy = dict(attributes)
        mode_value = None

        if self.AttributeDefs.mode_on_value.id in attributes_copy:
            mode_value = attributes_copy.pop(self.AttributeDefs.mode_on_value.id)
            await self._send_safe_mode(0x01, mode_value)
            self._update_attribute(self.AttributeDefs.mode_on_value.id, mode_value)
        elif self.AttributeDefs.mode_off_value.id in attributes_copy:
            mode_value = attributes_copy.pop(self.AttributeDefs.mode_off_value.id)
            await self._send_safe_mode(0x00, mode_value)
            self._update_attribute(self.AttributeDefs.mode_off_value.id, mode_value)
        elif self.AttributeDefs.mode_on_value.name in attributes_copy:
            mode_value = attributes_copy.pop(self.AttributeDefs.mode_on_value.name)
            await self._send_safe_mode(0x01, mode_value)
            self._update_attribute(self.AttributeDefs.mode_on_value.id, mode_value)
        elif self.AttributeDefs.mode_off_value.name in attributes_copy:
            mode_value = attributes_copy.pop(self.AttributeDefs.mode_off_value.name)
            await self._send_safe_mode(0x00, mode_value)
            self._update_attribute(self.AttributeDefs.mode_off_value.id, mode_value)

        if attributes_copy:
            return await super().write_attributes(attributes_copy, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


(
    QuirkBuilder("frient A/S", "SPLZB-141")
    .applies_to("Develco Products A/S", "SPLZB-131")
    .applies_to("frient A/S", "SPLZB-131")
    .applies_to("Develco Products A/S", "SPLZB-132")
    .applies_to("frient A/S", "SPLZB-132")
    .applies_to("Develco Products A/S", "SPLZB-134")
    .applies_to("frient A/S", "SPLZB-134")
    .applies_to("Develco Products A/S", "SPLZB-137")
    .applies_to("frient A/S", "SPLZB-137")
    .applies_to("Develco Products A/S", "SPLZB-141")
    .applies_to("Develco Products A/S", "SPLZB-142")
    .applies_to("frient A/S", "SPLZB-142")
    .applies_to("Develco Products A/S", "SPLZB-144")
    .applies_to("frient A/S", "SPLZB-144")
    .applies_to("Develco Products A/S", "SPLZB-147")
    .applies_to("frient A/S", "SPLZB-147")
    .applies_to("Develco Products A/S", "SMRZB-143")
    .applies_to("frient A/S", "SMRZB-143")
    .applies_to("Develco Products A/S", "SMRZB-153")
    .applies_to("frient A/S", "SMRZB-153")
    .applies_to("Develco Products A/S", "SMRZB-332")
    .applies_to("frient A/S", "SMRZB-332")
    .applies_to("Develco Products A/S", "SMRZB-342")
    .applies_to("frient A/S", "SMRZB-342")
    .replaces(VendorOnOff, endpoint_id=2)
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=DeviceTemperature.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "DeviceTemperature",
    )
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=ElectricalMeasurement.cluster_id,
        function=lambda entity: entity.device_class == "power",
    )
    .number(
        attribute_name=VendorOnOff.AttributeDefs.mode_on_value.name,
        cluster_id=OnOff.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=255,
        step=1,
        translation_key="mode_on",
        fallback_name="On after (min)",
        unique_id_suffix="mode_on",
    )
    .number(
        attribute_name=VendorOnOff.AttributeDefs.mode_off_value.name,
        cluster_id=OnOff.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=255,
        step=1,
        translation_key="mode_off",
        fallback_name="Off after (min)",
        unique_id_suffix="mode_off",
    )
    .sensor(
        endpoint_id=2,
        cluster_id=DeviceTemperature.cluster_id,
        attribute_name=DeviceTemperature.AttributeDefs.current_temperature.name,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        divisor=1,  # This should be 100 but the device does not follow the spec
        translation_key="device_temperature",
        fallback_name="Device temperature",
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="2",  # Replace the ZHA entity
    )
    .binary_sensor(
        attribute_name=VendorOnOff.AttributeDefs.return_to_state.name,
        cluster_id=OnOff.cluster_id,
        endpoint_id=2,
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=300,
            reportable_change=1,
        ),
        translation_key="return_to_state",
        fallback_name="Return to state",
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="return_to_state",
    )
    .add_to_registry()
)
