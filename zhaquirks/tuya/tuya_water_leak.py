"""Tuya water leak sensors."""

from zhaquirks.builder import EntityPlatform, EntityType
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_siren import NeoBatteryState

(
    TuyaQuirkBuilder("_TYST11_qq9mpfhw", "q9mpfhw")  # Tuya SNTZ009
    .applies_to("_TZE200_qq9mpfhw", "TS0601")  # NEO NAS-WS02B0
    .tuya_water_leak(dp_id=101)
    .tuya_enum(
        dp_id=102,
        attribute_name="power_type",
        enum_class=NeoBatteryState,
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="power_type",
        fallback_name="Power type",
    )
    .skip_configuration()
    .add_to_registry()
)
