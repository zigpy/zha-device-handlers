"""Develco Motion Sensor Pro."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.develco import DEVELCO, FRIENT, DevelcoIasZone, DevelcoPowerConfiguration

MANUFACTURER = 0x1015


class MOSZB140(CustomDevice):
    """Custom device Develco Motion Sensor Pro."""

    manufacturer_id_override = MANUFACTURER

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49353 device_type=1 device_version=1
        # input_clusters=[3, 5, 6] output_clusters=[]>
        # <SimpleDescriptor endpoint=34 profile=260 device_type=263 device_version=0
        # input_clusters=[0, 3, 1030] output_clusters=[]>
        # <SimpleDescriptor endpoint=35 profile=260 device_type=1026 device_version=0
        # input_clusters=[0, 1, 3, 15, 32, 1280] output_clusters=[10, 25]>
        # <SimpleDescriptor endpoint=38 profile=260 device_type=770 device_version=0
        # input_clusters=[0, 3, 1026] output_clusters=[3]>
        # <SimpleDescriptor endpoint=39 profile=260 device_type=262 device_version=0
        # input_clusters=[0, 3, 1024] output_clusters=[]>
        # <SimpleDescriptor endpoint=40 profile=260 device_type=263 device_version=0
        # input_clusters=[0, 3, 1030] output_clusters=[]>
        # <SimpleDescriptor endpoint=41 profile=260 device_type=263 device_version=0
        # input_clusters=[0, 3, 1030] output_clusters=[]>
        MODELS_INFO: [(DEVELCO, "MOSZB-140"), (FRIENT, "MOSZB-140")],
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
            34: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
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
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
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
            39: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            40: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
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
            34: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            35: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DevelcoPowerConfiguration,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    DevelcoIasZone,
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
            39: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            40: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class MOSZB140_Var02(CustomDevice):
    """Custom device Develco Motion Sensor Pro (variation 02)."""

    manufacturer_id_override = MANUFACTURER

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49353 device_type=1 device_version=1
        # input_clusters=[3, 5, 6] output_clusters=[]>
        # <SimpleDescriptor endpoint=34 profile=260 device_type=263 device_version=0
        # input_clusters=[0, 3, 1030] output_clusters=[]>
        # <SimpleDescriptor endpoint=35 profile=260 device_type=1026 device_version=0
        # input_clusters=[0, 1, 3, 15, 32, 1280] output_clusters=[3, 10, 25]>
        # <SimpleDescriptor endpoint=38 profile=260 device_type=770 device_version=0
        # input_clusters=[0, 3, 1026] output_clusters=[]>
        # <SimpleDescriptor endpoint=39 profile=260 device_type=262 device_version=0
        # input_clusters=[0, 3, 1024] output_clusters=[]>
        # <SimpleDescriptor endpoint=40 profile=260 device_type=263 device_version=0
        # input_clusters=[0, 3, 1030] output_clusters=[]>
        # <SimpleDescriptor endpoint=41 profile=260 device_type=263 device_version=0
        # input_clusters=[0, 3, 1030] output_clusters=[]>
        MODELS_INFO: [(DEVELCO, "MOSZB-140"), (FRIENT, "MOSZB-140")],
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
            34: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
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
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            39: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            40: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
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
            34: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            35: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DevelcoPowerConfiguration,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    DevelcoIasZone,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            38: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            39: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            40: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
