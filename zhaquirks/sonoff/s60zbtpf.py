"""SONOFF S60ZBTPF - Smart Socket with power measurement fix.

Firmware before v2.0.3 (`0x00002003`) keeps reporting power, current and voltage while
the socket is turned off. For those versions, the quirk sets `active_power` and
`rms_current` to 0 and `rms_voltage` to `uint16.non_value` when the socket is switched
off, and blocks further updates to the three attributes until it is switched back on.
v2.0.3 fixed the bug, so that version and newer do not get the workaround.

v2.0.2 also reports `instantaneous_demand` as supported, always with value 0. The
metering entity it would create is prevented for all firmware versions, as the device
never provides a useful value for it.

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


# firmware version that fixed the power reporting bug (max_version is exclusive)
S60_POWER_FIX_FW_VERSION = 0x00002003

# base for both firmware variants below, holding what applies to every firmware version.
# It is only cloned from, never added to the registry itself.
s60_base_quirk = (
    QuirkBuilder("SONOFF", "S60ZBTPF")
    .applies_to("SONOFF", "S60ZBTPG")
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Metering.cluster_id,
        unique_id_suffix="1-1794",  # no actual suffix for this
    )
)

(
    # firmware before the fix, and devices not reporting a firmware version at all,
    # get the power reporting workaround
    s60_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(max_version=S60_POWER_FIX_FW_VERSION, allow_missing=True)
    .replaces(SonoffS60OnOff)
    .replaces(SonoffS60ElectricalMeasurement)
    .add_to_registry()
)

(
    # the fixed firmware and newer only need the metering entity prevention
    s60_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(min_version=S60_POWER_FIX_FW_VERSION, allow_missing=False)
    .add_to_registry()
)
