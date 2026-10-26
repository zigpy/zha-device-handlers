"""Device handler for centralite 3450L."""

# pylint disable=C0103
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    OnOff,
    OnOffConfiguration,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zhaquirks import PowerConfigurationCluster
from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.legacy import CustomDevice


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


class CentraLite3450L(CustomDevice):
    """Custom device representing centralite 3450L."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=6
        #  device_version=0
        #  input_clusters=[0, 1, 3, 7, 20, b05]
        #  output_clusters=[3, 6, 19]>
        MODELS_INFO: [(CENTRALITE, "3450-L"), (CENTRALITE, "3450-L2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOffConfiguration.cluster_id,
                    PollControl.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                #  input_clusters=[7]
                #  output_clusters=[6]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            3: {
                #  input_clusters=[7]
                #  output_clusters=[6]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            4: {
                #  input_clusters=[7]
                #  output_clusters=[6]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
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
                    CustomPowerConfigurationCluster,
                    Identify.cluster_id,
                    OnOffConfiguration.cluster_id,
                    PollControl.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                #  input_clusters=[7]
                #  output_clusters=[6]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            3: {
                #  input_clusters=[7]
                #  output_clusters=[6]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            4: {
                #  input_clusters=[7]
                #  output_clusters=[6]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [OnOffConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 2},
        (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 3},
        (SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_PRESS, ENDPOINT_ID: 4},
    }

    # Each button sends on from its endpoint when pressed and off when released
    button_event_entities = tuple(
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_START,
                    event_data={
                        COMMAND: COMMAND_ON,
                        CLUSTER_ID: OnOff.cluster_id,
                        ENDPOINT_ID: endpoint_id,
                    },
                ),
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={
                        COMMAND: COMMAND_OFF,
                        CLUSTER_ID: OnOff.cluster_id,
                        ENDPOINT_ID: endpoint_id,
                    },
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=endpoint_id,
            unique_id_suffix=f"button_{endpoint_id}",
            translation_key="numbered_button",
            translation_placeholders={"button_number": str(endpoint_id)},
            fallback_name=f"Button {endpoint_id}",
        )
        for endpoint_id in (1, 2, 3, 4)
    )
