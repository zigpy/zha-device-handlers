"""Tuya TS0726 switches."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder

# Zemismart 2-gang switch. Until the attribute read spell is cast, an OnOff
# command sent to either endpoint switches both gangs. Physical buttons are
# unaffected.
TuyaQuirkBuilder("_TZ3000_icoxotza", "TS0726").tuya_enchantment().add_to_registry()
