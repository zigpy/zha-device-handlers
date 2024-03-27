"""Quirk IDs used for matching quirked devices in ZHA."""

# Konke
KONKE_BUTTON = "konke.button_remote"  # remote with custom handling in cluster handler

# Tuya
TUYA_PLUG_ONOFF = "tuya.plug_on_off_attributes"  # plugs with configurable attributes on the OnOff cluster
TUYA_PLUG_MANUFACTURER = "tuya.plug_manufacturer_attributes"  # plugs with configurable attributes on a custom cluster

# Xiaomi
XIAOMI_AQARA_VIBRATION_AQ1 = (
    "xiaomi.aqara_vibration_aq1"  # vibration sensor with custom cluster handler
)

# Danfoss
DANFOSS_ALLY_THERMOSTAT = "danfoss.ally_thermostat"  # Thermostatic Radiator Valves based on Danfoss Ally with custom clusters
