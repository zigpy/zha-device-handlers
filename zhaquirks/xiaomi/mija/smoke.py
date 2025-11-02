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

from typing import Final

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
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
    BatterySize,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    DeviceTemperatureCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)


class XiaomiSmokeIASCluster(CustomCluster, IasZone):
    """Xiaomi smoke IAS cluster implementation."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.attributes_by_name["zone_type"].id: IasZone.ZoneType.Fire_Sensor
    }

    class AttributeDefs(IasZone.AttributeDefs):
        """Attribute definitions."""

        get_status: Final = ZCLAttributeDef(
            id=0xFFF0, type=t.uint32_t, is_manufacturer_specific=True
        )
        set_options: Final = ZCLAttributeDef(
            id=0xFFF1, type=t.uint32_t, is_manufacturer_specific=True
        )


class MijiaHoneywellSmokeDetectorSensor(XiaomiQuickInitDevice):
    """MijiaHoneywellSmokeDetectorSensor custom device."""

    def __init__(self, *args, **kwargs):
        """Init method."""
        self.battery_size = BatterySize.CR123A
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
                    AnalogInput.cluster_id,
                    MultistateInput.cluster_id,
                    XiaomiSmokeIASCluster,
                    DeviceTemperatureCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
