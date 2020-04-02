"""Door/Windows sensors."""

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters import general, measurement, security

from . import DEVELCO, DevelcoPowerConfiguration
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class DevelcoIASZone(CustomCluster, security.IasZone):
    """IAS Zone."""

    manufacturer_client_commands = {
        0x0000: (
            "status_change_notification",
            (
                security.IasZone.ZoneStatus,
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
                    general.Identify.cluster_id,
                    general.Scenes.cluster_id,
                    general.OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            35: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.PowerConfiguration.cluster_id,
                    general.Identify.cluster_id,
                    general.BinaryInput.cluster_id,
                    general.PollControl.cluster_id,
                    security.IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [general.Time, general.Ota.cluster_id],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                    measurement.TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [general.Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    general.Identify.cluster_id,
                    general.Scenes.cluster_id,
                    general.OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            35: {
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    DevelcoPowerConfiguration,
                    general.Identify.cluster_id,
                    general.BinaryInput.cluster_id,
                    general.PollControl.cluster_id,
                    DevelcoIASZone,
                ],
                OUTPUT_CLUSTERS: [general.Time, general.Ota.cluster_id],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.Identify.cluster_id,
                    measurement.TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [general.Identify.cluster_id],
            },
        }
    }
