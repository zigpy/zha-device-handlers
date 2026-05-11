"""Aqara Wall Outlet H2 UK (WP-P09D / lumi.plug.aeu002).

Dual-socket UK wall outlet with per-socket power monitoring. All three
endpoints expose standard ZCL ElectricalMeasurement and report active_power
10x too low, so this quirk multiplies the reported value by 10 on the way
in.

Endpoint mapping (switch and power endpoints do not align on this device):
  EP1: switch=socket 1, power=total
  EP2: switch=socket 2, power=socket 1 + USB
  EP3: switch=USB,      power=socket 2

The standard Aqara plug pattern (zhaquirks.xiaomi.ElectricalMeasurementCluster,
a LocalDataCluster with ac_power_divisor=10) is not used here. That pattern
assumes power arrives pre-scaled x10 via the Lumi proprietary cluster or
AnalogInput, which then divides by 10 to net x1. This device emits power
purely via standard ZCL on all three endpoints, so the LocalDataCluster
would block the only path that carries readings.

Using _CONSTANT_ATTRIBUTES to set ac_power_multiplier or ac_power_divisor
on a plain CustomCluster was tested and produced no scaling change. The
device appears to adjust its reporting scale based on what ZHA reads back
from those attributes during cluster initialisation, creating a feedback
loop. The _update_attribute override is the only approach that produced
correct values, validated with a reference Athom smart plug across the
3W-2500W range.

The Xiaomi BasicCluster is retained on EP1 to handle the Xiaomi-specific
attribute payload sent during device initialisation.
"""

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.xiaomi import BasicCluster


class AqaraH2UKElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """ElectricalMeasurement that scales active_power x10.

    Device reports active_power 10x too low via standard ZCL on all three
    endpoints. Scaling validated against a reference plug across 3W-2500W.
    """

    def _update_attribute(
        self, attrid: int | t.uint16_t | foundation.ZCLAttributeDef, value: Any
    ) -> None:
        """Multiply active_power by 10 before caching."""
        if (
            self.find_attribute(attrid)
            == ElectricalMeasurement.AttributeDefs.active_power
            and value is not None
        ):
            value = value * 10
        super()._update_attribute(attrid, value)


(
    QuirkBuilder("Aqara", "lumi.plug.aeu002")
    .friendly_name(model="Wall Outlet H2 UK", manufacturer="Aqara")
    .replaces(BasicCluster)
    .replaces(AqaraH2UKElectricalMeasurement)
    .replaces(AqaraH2UKElectricalMeasurement, endpoint_id=2)
    .replaces(AqaraH2UKElectricalMeasurement, endpoint_id=3)
    .add_to_registry()
)
