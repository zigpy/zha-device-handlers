"""Modules for Yokis remote."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    OnOff,
    PowerConfiguration,
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    CLUSTER_ID,
    COMMAND,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.yokis import (
    YOKIS,
    YokisChannelCluster,
    YokisDeviceCluster,
    YokisDimmerCluster,
    YokisInputCluster,
    YokisLightControlCluster,
    YokisPilotWireCluster,
    YokisTemperatureMeasurementCluster,
    YokisWindowCoveringCluster,
)


class TLM1_TLC1_UP(CustomDevice):
    """Quirk for Yokis TLM1-UP and TLC1-UP."""

    signature = {
        MODELS_INFO: [
            (YOKIS, "TLC1-UP"),
            (YOKIS, "TLM1-UP"),
            (YOKIS, "TLM1T503-UP"),
            (YOKIS, "TLM1TNO-UP"),
            (YOKIS, "TLM1TDK-UP"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=9 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 3, 1026, 64523]
            # output_clusters=[3]>
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    YokisTemperatureMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    YokisTemperatureMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
    }


class TLM2_UP(CustomDevice):
    """Quirk for Yokis TLM2-UP."""

    signature = {
        MODELS_INFO: [
            (YOKIS, "TLM2-UP"),
            (YOKIS, "TLM2T503-UP"),
            (YOKIS, "TLM2TNO-UP"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=9 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 3, 1026, 64523]
            # output_clusters=[3]>
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    YokisTemperatureMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    YokisTemperatureMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
    }


class TLM4_GALET4_UP(CustomDevice):
    """Quirk for Yokis TLM4-UP and GALET4-UP."""

    signature = {
        MODELS_INFO: [
            (YOKIS, "TLM4-UP"),
            (YOKIS, "TLM4T503-UP"),
            (YOKIS, "GALET4-UP"),
            (YOKIS, "TLM4TNO-UP"),
            (YOKIS, "TLM4TDK-UP"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=9 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 3, 1026, 64523]
            # output_clusters=[3]>
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    YokisTemperatureMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    YokisTemperatureMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 4,
        },
    }


class TLC2_MONITOR2_E2BP_E2BPA_UP(CustomDevice):
    """Quirk for Yokis TLC2-UP, MONITOR2-UP, E2BP-UP and E2BPA-UP."""

    signature = {
        MODELS_INFO: [
            (YOKIS, "TLC2-UP"),
            (YOKIS, "MONITOR2-UP"),
            (YOKIS, "E2BP-UP"),
            (YOKIS, "E2BPA-UP"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
    }


class TLC4_E4BP_E4BPX_UP(CustomDevice):
    """Quirk for Yokis TLC4-UP, E4BP-UP and E4BPX-UP."""

    signature = {
        MODELS_INFO: [(YOKIS, "TLC4-UP"), (YOKIS, "E4BP-UP"), (YOKIS, "E4BPX-UP")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 4,
        },
    }


class TLC8_MONITOR_UP(CustomDevice):
    """Quirk for Yokis TLC8-UP and MONITOR-UP."""

    signature = {
        MODELS_INFO: [(YOKIS, "TLC8-UP"), (YOKIS, "MONITOR-UP")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=5 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=6 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=7 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=8 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 1, 3, 1000, 64513, 64514, 64521]
            # output_clusters=[3, 6, 8, 258, 1000, 64514, 64518, 64519, 64520, 64522]>
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    YokisDeviceCluster.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisChannelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    YokisInputCluster.cluster_id,
                    YokisLightControlCluster.cluster_id,
                    YokisDimmerCluster.cluster_id,
                    YokisWindowCoveringCluster.cluster_id,
                    YokisPilotWireCluster.cluster_id,
                ],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 2,
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 3,
        },
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 4,
        },
        (SHORT_PRESS, BUTTON_5): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 5,
        },
        (SHORT_PRESS, BUTTON_6): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 6,
        },
        (SHORT_PRESS, BUTTON_7): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 7,
        },
        (SHORT_PRESS, BUTTON_8): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 8,
        },
    }
