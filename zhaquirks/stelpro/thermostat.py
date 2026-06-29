"""Stelpro thermostat quirks."""

from zhaquirks.builder import HVACMode, register_thermostat_presets

# The Stelpro SORB fan heater can't be turned off, so it only offers HEAT as an
# HVAC mode. This replaces the hardcoded StelproFanHeater class that used to live
# in the ZHA library; the device is otherwise a standard ZCL thermostat, so no
# device quirk is needed - only the HVAC-mode override on the climate entity.
register_thermostat_presets(
    manufacturers={"Stelpro"},
    models={"SORB"},
    hvac_modes=[HVACMode.HEAT],
    name="StelproFanHeater",
)
