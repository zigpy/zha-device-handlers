"""Device handler for smarthjemmet.dk QUAD-ZIG-SW."""

from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    MultistateInput,
    OnOff,
    OnOffConfiguration,
    PowerConfiguration,
)
import zigpy.zcl.foundation

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    COMMAND_TRIPLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

MANUFACTURER = "smarthjemmet.dk"
MODEL_ID = "QUAD-ZIG-SW"

ACTION_TYPE = {
    0: COMMAND_RELEASE,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    3: COMMAND_TRIPLE,
    4: COMMAND_HOLD,
}


class CR2032PowerConfigurationCluster(PowerConfigurationCluster):
    """CR2032 Power Configuration Cluster."""

    MIN_VOLTS = 2.2
    MAX_VOLTS = 3.0


class CustomMultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    async def bind(self):
        """Prevent bind."""
        return zigpy.zcl.foundation.Status.SUCCESS

    async def unbind(self):
        """Prevent unbind."""
        return zigpy.zcl.foundation.Status.SUCCESS

    async def _configure_reporting(self, *args, **kwargs):
        """Prevent remote configure reporting."""
        return (
            zigpy.zcl.foundation.ConfigureReportingResponse.deserialize(b"\x00")[0],
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0055:
            if action := ACTION_TYPE.get(value) is not None:
                event_args = {VALUE: value}
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            super()._update_attribute(0, action)


class QUAD_ZIG_SW_BASE(CustomDevice):
    """Base class for QUAD-ZIG-SW."""

    def get_signature_v1():
        """Firmware version 1 signature."""
        return {
            MODELS_INFO: [(MANUFACTURER, MODEL_ID)],
            ENDPOINTS: {
                # <SimpleDescriptor endpoint=1 profile=260 device_type=65534
                # input_clusters=[0, 1, 7]
                # output_clusters=[0, 1, 18]>
                1: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: 65534,
                    INPUT_CLUSTERS: [
                        Basic.cluster_id,
                        PowerConfiguration.cluster_id,
                        OnOffConfiguration.cluster_id,
                    ],
                    OUTPUT_CLUSTERS: [
                        Basic.cluster_id,
                        PowerConfiguration.cluster_id,
                        CustomMultistateInputCluster.cluster_id,
                    ],
                },
                # <SimpleDescriptor endpoint=2 profile=260 device_type=65534
                # input_clusters=[7]
                # output_clusters=[18]>
                2: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: 65534,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
                # <SimpleDescriptor endpoint=3 profile=260 device_type=65534
                # input_clusters=[7]
                # output_clusters=[18]>
                3: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: 65534,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
                # <SimpleDescriptor endpoint=4 profile=260 device_type=65534
                # input_clusters=[7]
                # output_clusters=[18]>
                4: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: 65534,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
                # <SimpleDescriptor endpoint=5 profile=260 device_type=65534
                # input_clusters=[7]
                # output_clusters=[18]>
                5: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: 65534,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
            },
        }

    def get_signature_v2():
        """Firmware version 2 signature."""
        return {
            MODELS_INFO: [(MANUFACTURER, MODEL_ID)],
            ENDPOINTS: {
                # <SimpleDescriptor endpoint=1 profile=260 device_type=65535
                # input_clusters=[0, 1, 7]
                # output_clusters=[0, 1, 18, 6]>
                1: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [
                        Basic.cluster_id,
                        PowerConfiguration.cluster_id,
                        OnOffConfiguration.cluster_id,
                    ],
                    OUTPUT_CLUSTERS: [
                        Basic.cluster_id,
                        PowerConfiguration.cluster_id,
                        CustomMultistateInputCluster.cluster_id,
                        OnOff.cluster_id,
                    ],
                },
                # <SimpleDescriptor endpoint=2 profile=260 device_type=65535
                # input_clusters=[7]
                # output_clusters=[18, 6]>
                2: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [
                        CustomMultistateInputCluster.cluster_id,
                        OnOff.cluster_id,
                    ],
                },
                # <SimpleDescriptor endpoint=3 profile=260 device_type=65535
                # input_clusters=[7]
                # output_clusters=[18, 6]>
                3: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [
                        CustomMultistateInputCluster.cluster_id,
                        OnOff.cluster_id,
                    ],
                },
                # <SimpleDescriptor endpoint=4 profile=260 device_type=65535
                # input_clusters=[7]
                # output_clusters=[18, 6]>
                4: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [
                        CustomMultistateInputCluster.cluster_id,
                        OnOff.cluster_id,
                    ],
                },
                # <SimpleDescriptor endpoint=5 profile=260 device_type=65535
                # input_clusters=[7]
                # output_clusters=[18, 6]>
                5: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                    OUTPUT_CLUSTERS: [
                        CustomMultistateInputCluster.cluster_id,
                        OnOff.cluster_id,
                    ],
                },
            },
        }

    def get_replacement():
        """Return replacement for QUAD-ZIG-SW."""
        return {
            SKIP_CONFIGURATION: True,
            ENDPOINTS: {
                1: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [Basic.cluster_id, CR2032PowerConfigurationCluster],
                    OUTPUT_CLUSTERS: [Basic.cluster_id],
                },
                2: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [
                        CustomMultistateInputCluster,
                        OnOffConfiguration.cluster_id,
                    ],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
                3: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [
                        CustomMultistateInputCluster,
                        OnOffConfiguration.cluster_id,
                    ],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
                4: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [
                        CustomMultistateInputCluster,
                        OnOffConfiguration.cluster_id,
                    ],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
                5: {
                    PROFILE_ID: zha.PROFILE_ID,
                    DEVICE_TYPE: DeviceType.REMOTE_CONTROL,
                    INPUT_CLUSTERS: [
                        CustomMultistateInputCluster,
                        OnOffConfiguration.cluster_id,
                    ],
                    OUTPUT_CLUSTERS: [CustomMultistateInputCluster.cluster_id],
                },
            },
        }

    def get_triggers():
        """Triggers for QUAD-ZIG-SW."""
        triggers = {}
        for i in range(1, 6):
            triggers[(SHORT_PRESS, f"button_{i}")] = {
                COMMAND: COMMAND_SINGLE,
                ENDPOINT_ID: i + 1,
            }
            triggers[(DOUBLE_PRESS, f"button_{i}")] = {
                COMMAND: COMMAND_DOUBLE,
                ENDPOINT_ID: i + 1,
            }
            triggers[(TRIPLE_PRESS, f"button_{i}")] = {
                COMMAND: COMMAND_TRIPLE,
                ENDPOINT_ID: i + 1,
            }
            triggers[(LONG_PRESS, f"button_{i}")] = {
                COMMAND: COMMAND_HOLD,
                ENDPOINT_ID: i + 1,
            }
            triggers[(LONG_RELEASE, f"button_{i}")] = {
                COMMAND: COMMAND_RELEASE,
                ENDPOINT_ID: i + 1,
            }
        return triggers


class QUAD_ZIG_SW_V1(QUAD_ZIG_SW_BASE):
    """Firmware version 1 device class."""

    signature = QUAD_ZIG_SW_BASE.get_signature_v1()
    replacement = QUAD_ZIG_SW_BASE.get_replacement()
    device_automation_triggers = QUAD_ZIG_SW_BASE.get_triggers()


class QUAD_ZIG_SW_V2(QUAD_ZIG_SW_BASE):
    """Firmware version 2 device class."""

    signature = QUAD_ZIG_SW_BASE.get_signature_v2()
    replacement = QUAD_ZIG_SW_BASE.get_replacement()
    device_automation_triggers = QUAD_ZIG_SW_BASE.get_triggers()
