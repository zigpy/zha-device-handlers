"""Konke Button Remote."""

from zha.quirks import KONKE_BUTTON
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import PowerConfigurationCluster
from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.konke import KONKE, KonkeOnOffCluster
from zhaquirks.legacy import CustomDevice

KONKE_CLUSTER_ID = 0xFCC0

# The button tells single from double presses, and reports a hold once
BUTTON_EVENT_ENTITIES = (
    ButtonEventMetadata(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, SHORT_PRESS),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, DOUBLE_PRESS),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, LONG_PRESS),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Server,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    ),
)


class KonkeButtonRemote1(CustomDevice):
    """Konke 1-button remote device."""

    quirk_id = KONKE_BUTTON

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2
        # device_version=0
        # input_clusters=[0, 1, 3, 6, 64704]
        # output_clusters=[3, 64704]>
        MODELS_INFO: [(KONKE, "3AFE280100510001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
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
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    KonkeOnOffCluster,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
            },
        },
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
    }

    button_event_entities = BUTTON_EVENT_ENTITIES


class KonkeButtonRemote2(CustomDevice):
    """Konke 1-button remote device 2nd variant."""

    quirk_id = KONKE_BUTTON

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2
        # device_version=0
        # input_clusters=[0, 1, 3, 4, 5, 6]
        # output_clusters=[3]>
        MODELS_INFO: [(KONKE, "3AFE170100510001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    KonkeOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
    }

    button_event_entities = BUTTON_EVENT_ENTITIES
