"""PLAID SYSTEMS PS-SPRZMS-SLP3 soil moisture sensor."""

from typing import Final

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import BatterySize
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import PowerConfigurationCluster
from zhaquirks.plaid import PLAID_SYSTEMS


class PowerConfigurationClusterMains(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    class AttributeDefs(PowerConfigurationCluster.AttributeDefs):  # type: ignore[name-defined]
        """Attribute definitions for Power Configuration cluster with bad voltage."""

        # The manufacturer uses the mains_voltage attribute to report battery voltage
        battery_voltage: Final = ZCLAttributeDef(id=0x0000, type=t.uint16_t, access="r")
        mains_voltage: Final = None

    async def read_attribute_override_battery_size(self) -> int:
        """Return constant battery size."""
        return BatterySize.CR123A

    async def read_attribute_override_battery_quantity(self) -> int:
        """Return constant battery quantity."""
        return 1

    async def read_attribute_override_battery_voltage(self) -> int:
        """Read battery_voltage from mains_voltage."""
        success, failure = await super().read_attributes(
            [self.AttributeDefs.mains_voltage]
        )
        return round(success[self.AttributeDefs.battery_voltage] / 100)


(
    QuirkBuilder(PLAID_SYSTEMS, "PS-SPRZMS-SLP3")
    .replaces(PowerConfigurationClusterMains, endpoint_id=1)
    .add_to_registry()
)
