"""PLAID SYSTEMS PS-SPRZMS-SLP3 soil moisture sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.plaid import PLAID_SYSTEMS


class PowerConfigurationClusterMains(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MAINS_VOLTAGE_ATTR = 0x0000
    ATTR_ID_BATT_SIZE = 0x0031
    ATTR_ID_BATT_QTY = 0x0033
    _CONSTANT_ATTRIBUTES = {ATTR_ID_BATT_SIZE: 0x08, ATTR_ID_BATT_QTY: 1}

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.MAINS_VOLTAGE_ATTR:
            super()._update_attribute(self.BATTERY_VOLTAGE_ATTR, round(value / 100))

    def _remap(self, attr):
        """Replace battery voltage attribute name/id with mains_voltage."""
        if attr in (self.BATTERY_VOLTAGE_ATTR, "battery_voltage"):
            return self.MAINS_VOLTAGE_ATTR
        return attr

    async def read_attributes(self, attributes, *args, **kwargs):
        """Replace battery voltage with mains voltage."""
        return await super().read_attributes(
            [self._remap(attr) for attr in attributes], *args, **kwargs
        )

    async def configure_reporting(self, attribute, *args, **kwargs):
        """Replace battery voltage with mains voltage."""
        return await super().configure_reporting(
            self._remap(attribute), *args, **kwargs
        )


(
    QuirkBuilder(PLAID_SYSTEMS, "PS-SPRZMS-SLP3")
    .replaces(PowerConfigurationClusterMains, endpoint_id=1)
    .add_to_registry()
)
