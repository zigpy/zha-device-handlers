"""SONOFF S60ZBTPF - Smart Socket with power measurement fix.

Firmware versions before v2.0.3 (0x00002003) have a bug where the device keeps
reporting active power consumption even when the socket is turned off. The quirk
for those versions fixes that by, when the `on_off` state becomes False, setting
`active_power` and `rms_current` to 0 and `rms_voltage` to `uint16.non_value`, and
by blocking subsequent updates to these three attributes while the socket remains
off. v2.0.3 fixed this bug, so the workaround is not applied to that version and
newer.

v2.0.2 additionally reports `instantaneous_demand` as supported (always with value
0), which v2.0.3 fixed by marking it unsupported. The metering entity it would
create is prevented for all firmware versions, as it is never useful here.

See https://github.com/zigpy/zigpy-ota/issues/164 for more details.
"""

from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


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


# firmware version v2.0.3 that fixed the power reporting bug
S60_POWER_FIX_FW_VERSION = 0x00002003

# shared base for both firmware variants below: the instantaneous_demand metering
# entity prevention applies regardless of firmware. The base intentionally carries
# no manufacturer/model data so it is not registered on its own; each clone adds the
# models via `applies_to`.
# firmware v2.0.2 reports instantaneous_demand as supported, always with value 0.
s60_base_quirk = QuirkBuilder().prevent_default_entity_creation(
    endpoint_id=1,
    cluster_id=Metering.cluster_id,
    unique_id_suffix="1-1794",  # no actual suffix for this
)

(
    # firmware before v2.0.3 keeps reporting power while the socket is off,
    # so apply the workaround to those versions (max_version is exclusive).
    # Also apply it when the firmware version is missing, just to be safe.
    s60_base_quirk.clone()
    .applies_to("SONOFF", "S60ZBTPF")
    .applies_to("SONOFF", "S60ZBTPG")
    .firmware_version_filter(max_version=S60_POWER_FIX_FW_VERSION, allow_missing=True)
    .replaces(SonoffS60OnOff)
    .replaces(SonoffS60ElectricalMeasurement)
    .add_to_registry()
)

(
    # firmware v2.0.3 and newer fixed the power reporting bug, so the workaround
    # is not applied. The instantaneous_demand metering entity is still prevented.
    s60_base_quirk.clone()
    .applies_to("SONOFF", "S60ZBTPF")
    .applies_to("SONOFF", "S60ZBTPG")
    .firmware_version_filter(min_version=S60_POWER_FIX_FW_VERSION, allow_missing=False)
    .add_to_registry()
)
