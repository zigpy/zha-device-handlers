"""Xiaomi Mija smoke detector quirks implementations.

Manufacturer ID: 0x115F
Known Options for set_options:
High Sensitivity: 0x04010000,
Medium Sensitivity: 0x04020000,
Low Sensitivity: 0x04030000,
Self Test: 0x03010000

Responses from get_status:
High Sensitivity: 0x0101000011010003,
Medium Sensitivity: 0x0102000011010003,
Low Sensitivity: 0x0103000011010003.
"""
import logging

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Identify,
    MultistateInput,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    DeviceTemperatureCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)

_LOGGER = logging.getLogger(__name__)


class XiaomiSmokeIASCluster(CustomCluster, IasZone):
    """Xiaomi smoke IAS cluster implementation."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.attributes_by_name["zone_type"].id: IasZone.ZoneType.Fire_Sensor
    }

    attributes = IasZone.attributes.copy()
    attributes.update(
        {
            0xFFF0: ("get_status", t.uint32_t, True),
            0xFFF1: ("set_options", t.uint32_t, True),
        }
    )


class XiaomiSmokeAnalogInputCluster(CustomCluster, AnalogInput):
    """Xiaomi AnalogInput cluster to receive reports that are sent to the basic cluster."""

    _CONSTANT_ATTRIBUTES = {
        AnalogInput.attributes_by_name["description"].id: "Smoke Density"
    }

    attributes = AnalogInput.attributes.copy()

    ATTR_ID = AnalogInput.attributes_by_name["present_value"].id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.smoke_density_bus.add_listener(self)

    def smoke_density_reported(self, value):
        """Smoke density reported."""
        self._update_attribute(self.ATTR_ID, value)


class MijiaHoneywellSmokeDetectorSensor(XiaomiQuickInitDevice):
    """MijiaHoneywellSmokeDetectorSensor custom device."""

    def __init__(self, *args, **kwargs):
        """Init method."""
        self.battery_size = 8  # CR123a
        self.smoke_density_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=
        #  input_clusters=[0, 1, 3, 12, 18, 1280]
        #  output_clusters=[25]>
        NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        MODELS_INFO: ((LUMI, "lumi.sensor_smoke"),),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    AnalogInput.cluster_id,
                    MultistateInput.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    XiaomiSmokeAnalogInputCluster,
                    MultistateInput.cluster_id,
                    XiaomiSmokeIASCluster,
                    DeviceTemperatureCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
