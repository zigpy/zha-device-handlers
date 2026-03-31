"""SONOFF S60ZBTPF - Smart Socket with power measurement fix.

This device has a quirk where it continues to report active power consumption
even when the socket is turned off. This quirk fixes that by, when the
`on_off` state becomes False, setting `active_power` and `rms_current` to 0
and `rms_voltage` to `uint16.non_value`, and by blocking subsequent updates
to these three attributes while the socket remains off.
"""

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering


class SonoffS60OnOff(CustomCluster, OnOff):
    """Custom OnOff cluster that resets power readings when the socket is turned off."""

    def _update_attribute(
        self, attrid: int | t.uint16_t | foundation.ZCLAttributeDef, value: Any
    ) -> None:
        """Reset attributes to zero when the socket is turned off."""
        if (
            self.find_attribute(attrid) == OnOff.AttributeDefs.on_off
            and value == t.Bool.false
        ):
            self.endpoint.electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.active_power.id, 0
            )
            self.endpoint.electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.rms_current.id, 0
            )
            self.endpoint.electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.rms_voltage.id,
                foundation.DataType.uint16.non_value,
            )

        super()._update_attribute(attrid, value)


class SonoffS60ElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Custom ElectricalMeasurement cluster that prevents power updates when the socket is turned off."""

    def _update_attribute(
        self, attrid: int | t.uint16_t | foundation.ZCLAttributeDef, value: Any
    ) -> None:
        """Prevent updates when the socket is turned off."""
        if (
            self.endpoint.on_off.get(OnOff.AttributeDefs.on_off.id) == t.Bool.false
            # we should always get the ID here, but just in case, check for def too
            and self.find_attribute(attrid)
            in (
                ElectricalMeasurement.AttributeDefs.active_power,
                ElectricalMeasurement.AttributeDefs.rms_current,
                ElectricalMeasurement.AttributeDefs.rms_voltage,
            )
        ):
            return

        super()._update_attribute(attrid, value)


(
    QuirkBuilder("SONOFF", "S60ZBTPF")
    .applies_to("SONOFF", "S60ZBTPG")
    .replaces(SonoffS60OnOff)
    .replaces(SonoffS60ElectricalMeasurement)
    # firmware v2.0.2 reports instantaneous_demand as supported, always with value 0
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Metering.cluster_id,
        unique_id_suffix="1-1794",  # no actual suffix for this
    )
    .add_to_registry()
)
