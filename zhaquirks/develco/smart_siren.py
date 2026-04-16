"""Smart siren."""

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.develco import DEVELCO, FRIENT


class FrientIasWd(CustomCluster, IasWd):
    """IAS WD cluster wrapper with local squawk volume setting."""

    class AttributeDefs(IasWd.AttributeDefs):
        """Attribute definitions."""

        squawk_level = ZCLAttributeDef(
            id=0xFFF0,
            type=IasWd.Squawk.SquawkLevel,
            access="rw",
        )

    def _resolve_attr_id(
        self, attr: str | int | foundation.ZCLAttributeDef
    ) -> int | None:
        """Resolve an attribute identifier to an int attr id."""
        if isinstance(attr, str):
            attr_def = self.attributes_by_name.get(attr)
            return attr_def.id if attr_def is not None else None
        if isinstance(attr, foundation.ZCLAttributeDef):
            return attr.id
        if isinstance(attr, int):
            return attr
        return None

    async def read_attributes_raw(
        self,
        attributes: list[str | int | foundation.ZCLAttributeDef],
        manufacturer: int | None = None,
        **kwargs,
    ) -> tuple[list[foundation.ReadAttributeRecord], ...]:
        """Handle local squawk_level reads while delegating other attributes."""
        local_attr_id = self.AttributeDefs.squawk_level.id
        local_records: list[foundation.ReadAttributeRecord] = []
        remote_attrs: list[str | int | foundation.ZCLAttributeDef] = []

        for attr in attributes:
            attr_id = self._resolve_attr_id(attr)
            if attr_id == local_attr_id:
                value = self.get(
                    local_attr_id,
                    IasWd.Squawk.SquawkLevel.Low_level_sound,
                )
                local_records.append(
                    foundation.ReadAttributeRecord(
                        attrid=local_attr_id,
                        status=foundation.Status.SUCCESS,
                        value=foundation.TypeValue(
                            value=self.AttributeDefs.squawk_level.type(value)
                        ),
                    )
                )
            else:
                remote_attrs.append(attr)

        if not remote_attrs:
            return (local_records,)

        remote_result = await super().read_attributes_raw(
            remote_attrs,
            manufacturer=manufacturer,
            **kwargs,
        )
        remote_records = list(remote_result[0])
        return (remote_records + local_records, *remote_result[1:])

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Handle local squawk_level writes while delegating other attributes."""
        local_attr_id = self.AttributeDefs.squawk_level.id
        remote_attrs: dict[str | int | foundation.ZCLAttributeDef, Any] = {}
        local_write = False

        for attr, value in attributes.items():
            attr_id = self._resolve_attr_id(attr)
            if attr_id is None:
                raise KeyError(f"Unknown attribute: {attr!r}")

            if attr_id == local_attr_id:
                self._update_attribute(
                    local_attr_id, self.AttributeDefs.squawk_level.type(value)
                )
                local_write = True
            else:
                remote_attrs[attr] = value

        if remote_attrs:
            return await super().write_attributes(
                remote_attrs,
                manufacturer=manufacturer,
                **kwargs,
            )

        if local_write:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        # Empty writes are a no-op and should be treated as successful.
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def squawk(self, squawk: int | IasWd.Squawk, *args, **kwargs):
        """Apply selected local squawk volume to any squawk command."""
        local_attr_id = self.AttributeDefs.squawk_level.id
        configured_level = self.get(
            local_attr_id,
            IasWd.Squawk.SquawkLevel.Low_level_sound,
        )
        squawk_cmd = IasWd.Squawk(int(squawk))
        squawk_cmd.level = IasWd.Squawk.SquawkLevel(configured_level)
        return await self.command(
            IasWd.ServerCommandDefs.squawk.id,
            *args,
            squawk=squawk_cmd,
            **kwargs,
        )


BASE_SIREN_QUIRK = (
    QuirkBuilder()
    .replaces(FrientIasWd, endpoint_id=43)
    # Hide the default `ias_zone` entity
    .prevent_default_entity_creation(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.translation_key == "ias_zone",
    )
    # Hide unsupported strobe controls.
    .prevent_default_entity_creation(
        endpoint_id=43,
        cluster_id=IasWd.cluster_id,
        function=lambda entity: entity.translation_key
        in (
            "default_strobe_level",
            "default_strobe",
        ),
    )
    # Allow setting IAS WD max warning duration in seconds.
    .number(
        attribute_name=IasWd.AttributeDefs.max_duration.name,
        cluster_id=IasWd.cluster_id,
        endpoint_id=43,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="max_duration",
        fallback_name="Maximum siren duration",
    )
    .enum(
        attribute_name=FrientIasWd.AttributeDefs.squawk_level.name,
        enum_class=IasWd.Squawk.SquawkLevel,
        cluster_id=IasWd.cluster_id,
        endpoint_id=43,
        translation_key="squawk_volume",
        fallback_name="Squawk volume",
    )
    .command_button(
        command_name=IasWd.ServerCommandDefs.squawk.name,
        cluster_id=IasWd.cluster_id,
        endpoint_id=43,
        command_kwargs={"squawk": 0x00},
        unique_id_suffix="squawk_armed",
        translation_key="squawk_armed",
        fallback_name="Squawk armed",
    )
    .command_button(
        command_name=IasWd.ServerCommandDefs.squawk.name,
        cluster_id=IasWd.cluster_id,
        endpoint_id=43,
        command_kwargs={"squawk": 0x10},
        unique_id_suffix="squawk_disarmed",
        translation_key="squawk_disarmed",
        fallback_name="Squawk disarmed",
    )
    # This is a mains-powered device that has a backup battery
    .sensor(
        attribute_name=PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=43,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        divisor=2,  # ZCL reports battery in units of 0.5%, so 200 => 100%
        fallback_name="Battery",
        unique_id_suffix="battery",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .binary_sensor(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.POWER,
        # AC mains bit is 0 when on mains power, 1 when on battery, so we need to invert it for correct reporting
        attribute_converter=lambda value: not bool(value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="power",
        fallback_name="AC Power",
    )
)

(
    # Devices with tamper
    BASE_SIREN_QUIRK.clone()
    .applies_to(FRIENT, "SIRZB-110")
    .applies_to(FRIENT, "SIRZB-112")
    .applies_to(DEVELCO, "SIRZB-110")
    .applies_to(DEVELCO, "SIRZB-112")
    # Create a tamper sensor
    .binary_sensor(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .add_to_registry()
)

(
    # Device without tamper
    BASE_SIREN_QUIRK.clone()
    .applies_to(FRIENT, "SIRZB-111")
    .applies_to(DEVELCO, "SIRZB-111")
    .add_to_registry()
)
