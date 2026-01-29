"""Device handler for WAXMAN leakSMART."""

# pylint: disable=W0102
from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ApplianceEventAlerts
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseCommandDefs

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import CLUSTER_COMMAND
from zhaquirks.waxman import WAXMAN

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC02  # decimal = 64514
MOISTURE_TYPE = 0x002A
WAXMAN_CMDID = 0x0001
ZONE_STATE = 0
ZONE_TYPE = 0x0001


class EmulatedIasZone(LocalDataCluster, IasZone):
    """Emulated IAS zone cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ias_bus.add_listener(self)
        super()._update_attribute(ZONE_TYPE, MOISTURE_TYPE)

    async def bind(self):
        """Bind cluster."""
        return await self.endpoint.device.app_cluster.bind()

    async def write_attributes(self, attributes, manufacturer=None):
        """Ignore write_attributes."""
        return (0,)

    def update_state(self, value):
        """Update IAS state."""
        super().listener_event(CLUSTER_COMMAND, None, ZONE_STATE, [value])


class WAXMANApplianceEventAlerts(CustomCluster, ApplianceEventAlerts):
    """WAXMAN specific ApplianceEventAlert cluster."""

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        alerts_notification = foundation.ZCLCommandDef(
            id=WAXMAN_CMDID,
            schema={"param1": t.uint8_t, "state": t.bitmap24},
            is_manufacturer_specific=True,
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.app_cluster = self

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == WAXMAN_CMDID:
            state = bool(args[1] & 0x1000)

            self.endpoint.device.ias_bus.listener_event("update_state", state)


class WAXMANLeakSmartCustomDevice(CustomDeviceV2):
    """Custom device for WAXMAN leakSMART with Bus support."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(WAXMAN, "leakSMART Water Sensor V2")
    .device_class(WAXMANLeakSmartCustomDevice)
    .removes(MANUFACTURER_SPECIFIC_CLUSTER_ID, endpoint_id=1)
    .replaces(WAXMANApplianceEventAlerts, endpoint_id=1)
    .adds(EmulatedIasZone, endpoint_id=1)
    .add_to_registry()
)
