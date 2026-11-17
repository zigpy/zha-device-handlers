"""Muller "nativ" connected electric radiators.

Sold as Noirot (Lavaroc, Nativ), Airelec and Intuis. All of them report an
empty `manufacturer_name` and the model `"intuisradiator"` right padded with
spaces to fill the whole character string, so Home Assistant shows them as
"unk_manufacturer".

The thermostat cluster carries one manufacturer-specific attribute, 0xFC00,
which enables the built-in presence/absence detector. While it is on, the
radiator reports occupancy on both `Thermostat.occupancy` and the Occupancy
Sensing cluster, and falls back to `unoccupied_heating_setpoint` when the room
is detected as empty. The firmware clamps that setpoint to 7..19 degC.

The attribute is only accepted when the ZCL header carries manufacturer code
0x122E, which is also what the node descriptor advertises.
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

MULLER_MANUFACTURER_ID: Final = 0x122E

#: The radiator fills the whole ZCL character string: 31 characters plus the
#: length byte. Built explicitly so the padding cannot be miscounted.
NATIV_MODEL: Final = "intuisradiator".ljust(31)

PRESENCE_DETECTION_ATTR_ID: Final = 0xFC00

#: Bounds enforced by the radiator itself when writing the absence setpoint.
ABSENCE_SETPOINT_MIN: Final = 7.0
ABSENCE_SETPOINT_MAX: Final = 19.0


class NativThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster with the Muller presence detector attribute."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Manufacturer specific attributes."""

        presence_detection: Final = ZCLAttributeDef(
            # the radiator stores this as an uint8, not a bool
            id=PRESENCE_DETECTION_ATTR_ID,
            type=t.uint8_t,
            access="rwps",
            manufacturer_code=MULLER_MANUFACTURER_ID,
        )


(
    QuirkBuilder(None, NATIV_MODEL)
    # some stacks strip the padding from the model attribute
    .also_applies_to(None, NATIV_MODEL.strip())
    .friendly_name(manufacturer="Muller", model="nativ radiator")
    .replaces(NativThermostatCluster)
    .switch(
        NativThermostatCluster.AttributeDefs.presence_detection.name,
        NativThermostatCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=3600, reportable_change=1
        ),
        translation_key="presence_detection",
        fallback_name="Presence detection",
    )
    # the climate entity only exposes this setpoint while the radiator reports
    # the room as empty, so surface it separately to let it be configured
    .number(
        Thermostat.AttributeDefs.unoccupied_heating_setpoint.name,
        NativThermostatCluster.cluster_id,
        min_value=ABSENCE_SETPOINT_MIN,
        max_value=ABSENCE_SETPOINT_MAX,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_type=EntityType.CONFIG,
        translation_key="absence_setpoint",
        fallback_name="Absence setpoint",
    )
    .add_to_registry()
)
