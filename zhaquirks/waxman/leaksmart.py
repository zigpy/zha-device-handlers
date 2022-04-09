"""Device handler for WAXMAN leakSMART."""
# pylint: disable=W0102
from typing import Any, List, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import ApplianceEventAlerts
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    CLUSTER_COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
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

    client_commands = {
        WAXMAN_CMDID: foundation.ZCLCommandDef(
            "alerts_notification",
            {"param1": t.uint8_t, "state": t.bitmap24},
            False,
            is_manufacturer_specific=True,
        )
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.app_cluster = self

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == WAXMAN_CMDID:
            state = bool(args[1] & 0x1000)

            self.endpoint.device.ias_bus.listener_event("update_state", state)


class WAXMANleakSMARTv2(CustomDevice):
    """Custom device representing WAXMAN leakSMART v2."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 2818, 64514]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [(WAXMAN, "leakSMART Water Sensor V2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    ApplianceEventAlerts.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    WAXMANApplianceEventAlerts,
                    EmulatedIasZone,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }


class WAXMANleakSMARTv2NOPOLL(CustomDevice):
    """Custom WAXMAN leakSMART v2 without PollControl cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1026, 2818, 64514]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [(WAXMAN, "leakSMART Water Sensor V2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    ApplianceEventAlerts.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    WAXMANApplianceEventAlerts,
                    EmulatedIasZone,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
