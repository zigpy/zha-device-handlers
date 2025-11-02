"""Frient Smoke & Heat & Water Alarm."""

from typing import Final

from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasWd, IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.develco import DevelcoIasZone, DevelcoPowerConfiguration


class FrientSmokeHeatWaterIasZone(DevelcoIasZone):
    """Custom IAS Zone cluster for Smoke Alarm, Heat Alarm and Water Alarm with test support bit exposed."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.zone_status.id:
            # Update test state from zone_status bit 8
            status_value = int(getattr(value, "value", value))
            test_state = bool(status_value & 0b0000000100000000)
            super()._update_attribute(self.AttributeDefs.test.id, test_state)

    class AttributeDefs(IasZone.AttributeDefs):
        """Attribute definitions."""

        test: Final = ZCLAttributeDef(
            id=0xFFF2,  # Custom attribute ID
            type=t.Bool,
        )


(
    QuirkBuilder("frient A/S", "SMSZB-120")
    .applies_to("Develco Products A/S", "SMSZB-120")
    .applies_to("frient A/S", "HESZB-120")
    .applies_to("Develco Products A/S", "HESZB-120")
    .applies_to("frient A/S", "FLSZB-110")
    .applies_to("Develco Products A/S", "FLSZB-110")
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .replaces(FrientSmokeHeatWaterIasZone, endpoint_id=35)
    .binary_sensor(
        attribute_name="test",
        cluster_id=IasZone.cluster_id,
        endpoint_id=35,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="test",
        fallback_name="IAS test",
    )
    .number(
        attribute_name="max_duration",
        cluster_id=IasWd.cluster_id,
        endpoint_id=35,
        min_value=0,
        max_value=65535,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="max_duration",
        fallback_name="Max duration",
        unique_id_suffix="max_duration",
    )
    .prevent_default_entity_creation(
        endpoint_id=35,
        cluster_id=IasWd.cluster_id,
        function=lambda entity: entity.translation_key
        in (
            "default_siren_tone",
            "default_siren_level",
            "default_strobe_level",
            "default_strobe",
        ),
    )
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    .add_to_registry()
)
