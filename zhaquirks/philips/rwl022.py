"""Philips RWL022 device."""

from typing import Any

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import CustomDevice
from zhaquirks.philips import (
    RWL_BUTTON_NAMES,
    SIGNIFY,
    PhilipsBasicCluster,
    PhilipsRwlRemoteCluster,
)

DEVICE_SPECIFIC_UNKNOWN = 64512

# The second generation dimmer has a power button (on/off toggle) and a Hue button in
# place of the first generation's on and off buttons. Its triggers keep the first
# generation's names.
RWL022_BUTTON_NAMES: dict[int, dict[str, Any]] = {
    **RWL_BUTTON_NAMES,
    1: {
        "unique_id_suffix": "button_toggle",
        "translation_key": "toggle_button",
        "fallback_name": "Toggle button",
    },
    4: {
        "unique_id_suffix": "button_hue",
        "translation_key": "hue_button",
        "fallback_name": "Hue button",
    },
}


class PhilipsRWL022(CustomDevice):
    """Philips RWL022 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2096
        #  device_version=1
        #  input_clusters=[0, 1, 3, 64512, 4096]
        #  output_clusters=[25, 0, 3, 4, 6, 8, 5, 4096]>
        MODELS_INFO: [(SIGNIFY, "RWL022")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsRwlRemoteCluster,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = (
        PhilipsRwlRemoteCluster.generate_device_automation_triggers()
    )

    button_event_entities = PhilipsRwlRemoteCluster.generate_button_event_entities(
        endpoint_id=1, names=RWL022_BUTTON_NAMES
    )
