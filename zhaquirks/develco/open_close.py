"""Door/Windows sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Identify,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from . import DEVELCO, DevelcoPowerConfiguration
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class DevelcoIASZone(CustomCluster, IasZone):
    """IAS Zone."""

    manufacturer_client_commands = {
        0x0000: (
            "status_change_notification",
            (
                IasZone.ZoneStatus,
                t.bitmap8,
                t.Optional(t.uint8_t),
                t.Optional(t.uint16_t),
            ),
            False,
        )
    }


class WISZB120(CustomDevice):
    """Custom device representing door/windows sensors."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49353 device_type=1 device_version=1
        # input_clusters=[3, 5, 6] output_clusters=[]>
        # <SimpleDescriptor endpoint=35 profile=260 device_type=1026 device_version=0
        # input_clusters=[0, 1, 3, 15, 32, 1280] output_clusters=[10, 25]>
        # <SimpleDescriptor endpoint=38 profile=260 device_type=770 device_version=0
        # input_clusters=[0, 3, 1026] output_clusters=[3]>
        MODELS_INFO: [(DEVELCO, "WISZB-120")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0xC0C9,
                DEVICE_TYPE: 1,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            35: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            35: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DevelcoPowerConfiguration,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    DevelcoIASZone,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }
