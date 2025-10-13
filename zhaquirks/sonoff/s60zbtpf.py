"""SONOFF S60ZBTPF - Smart Socket with power measurement fix.

This device has a quirk where it continues to report active power consumption
even when the socket is turned off. This quirk fixes that by setting the
`active_power` and `rms_current` to 0 when the `on_off` state is False.
"""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id
CURRENT_ID = ElectricalMeasurement.AttributeDefs.rms_current.id
VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id
ON_OFF_ID = OnOff.AttributeDefs.on_off.id


class SonoffS60OnOff(CustomCluster, OnOff):
    """Custom OnOff cluster that resets power readings when the socket is turned off."""

    def _update_attribute(self, attrid, value):
        """Reset attributes to zero when the socket is turned off."""

        if attrid == ON_OFF_ID and value == t.Bool.false:
            self.debug(
                "Socket turned off, resetting power and current measurements to zero"
            )
            self.endpoint.electrical_measurement.update_attribute(POWER_ID, 0)
            self.endpoint.electrical_measurement.update_attribute(CURRENT_ID, 0)
            self.endpoint.electrical_measurement.update_attribute(VOLTAGE_ID, None)

        super()._update_attribute(attrid, value)


class SonoffS60ElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Custom ElectricalMeasurement cluster that prevents power updates when the socket is turned off."""

    def _update_attribute(self, attrid, value):
        """Prevent updates when the socket is turned off."""

        if self.endpoint.on_off.get(ON_OFF_ID) == t.Bool.false:
            if attrid == POWER_ID:
                self.debug("Socket turned off, preventing power measurement update")
                return

            if attrid == CURRENT_ID:
                self.debug("Socket turned off, preventing current measurement update")
                return

            if attrid == VOLTAGE_ID:
                self.debug("Socket turned off, preventing voltage measurement update")
                return

        super()._update_attribute(attrid, value)


(
    QuirkBuilder("SONOFF", "S60ZBTPF")
    .also_applies_to("SONOFF", "S60ZBTPG")
    .replaces(SonoffS60OnOff)
    .replaces(SonoffS60ElectricalMeasurement)
    .add_to_registry()
)
