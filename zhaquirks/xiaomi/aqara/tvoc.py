"""Quirk for lumi.airmonitor.acn01 tvoc air monitor."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import AnalogInput, Basic, Identify, Ota
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import Bus, LocalDataCluster, PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, TVOC_REPORTED, BasicCluster, XiaomiCustomDevice

_LOGGER = logging.getLogger(__name__)


class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster, relay tvoc to the correct cluster."""

    cluster_id = AnalogInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await super().configure_reporting(
            0x0055,
            10,
            3600,
            5,
        )
        return result

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if value is not None and value >= 0:
            self.endpoint.device.tvoc_bus.listener_event(TVOC_REPORTED, value)


class EmulatedTVOCMeasurement(LocalDataCluster):
    """TVOC measurement cluster to receive reports from the AnalogInput cluster."""

    cluster_id = 0x042E
    name = "VOC Level"
    ep_attribute = "voc_level"

    attributes = {
        0x0000: ("measured_value", t.Single),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.tvoc_bus.add_listener(self)

    def tvoc_reported(self, value):
        """VOC reported."""
        self._update_attribute(0x0000, value)


class TVOCMonitor(XiaomiCustomDevice):
    """Aqara LUMI lumi.airmonitor.acn01."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.tvoc_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=770
        # device_version=1
        # input_clusters=[0, 1, 3, 12, 1026, 1029]
        # output_clusters=[19]>
        MODELS_INFO: [(LUMI, "lumi.airmonitor.acn01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    PowerConfigurationCluster,
                    RelativeHumidity.cluster_id,
                    AnalogInputCluster,
                    EmulatedTVOCMeasurement,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
