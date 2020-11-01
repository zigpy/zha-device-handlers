"""Device handler for iMagic by Greatstar."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import IMAGIC
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

MANUFACTURER_SPECIFIC_PROFILE_ID = 0xFC01
MANUFACTURER_SPECIFIC_PROFILE_ID2 = 0xFC02


class Greatstar(CustomDevice):
    """Custom device representing iMagic by Greatstar motion sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=0x0402
        #  device_version=0
        #  input_clusters=["0x0000", "0x0001", "0x0003","0x0020","0x0402", "0x0405", "0x0500", "0x0b05","0xfc01","0xfc02"]
        #  output_clusters=["0x0003","0x0019"]>
        MODELS_INFO: [(IMAGIC, "1117-S")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                    MANUFACTURER_SPECIFIC_PROFILE_ID,
                    MANUFACTURER_SPECIFIC_PROFILE_ID2,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    PowerConfigurationCluster,
                    Identify,
                    PollControl,
                    TemperatureMeasurement,
                    RelativeHumidity,
                    IasZone,
                    Diagnostic,
                    MANUFACTURER_SPECIFIC_PROFILE_ID,
                    MANUFACTURER_SPECIFIC_PROFILE_ID2,
                ],
                OUTPUT_CLUSTERS: [Identify, Ota],
            }
        }
    }
