"""Tuya water leak sensors."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TYST11_qq9mpfhw", "q9mpfhw")  # Tuya SNTZ009
    .applies_to("_TZE200_qq9mpfhw", "TS0601")  # NEO NAS-WS02B0
    .tuya_water_leak(dp_id=101)
    .skip_configuration()
    .add_to_registry()
)
