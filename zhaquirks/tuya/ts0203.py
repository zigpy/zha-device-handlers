"""Tuya TS0203 door/window contact sensor."""

from zigpy.zcl.clusters.general import OnOff

from zhaquirks.tuya.builder import TuyaQuirkBuilder

# TS0203: Standard Zigbee IAS Zone contact sensor (no Tuya MCU cluster).
# Uses IAS Zone (0x0500) for contact state and Power Configuration (0x0001)
# for battery. The device has On/Off (0x0006) as an output cluster intended
# for binding to lights, but ZHA creates a spurious "Opening" binary sensor
# from it.
(
    TuyaQuirkBuilder("_TZ3000_au1rjicn", "TS0203")
    # Suppress the spurious "Opening" entity created from the On/Off output
    # (client) cluster. The real contact state comes from IAS Zone (0x0500).
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
    .add_to_registry()
)
