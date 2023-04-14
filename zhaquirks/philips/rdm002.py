"""Signify RDM002 device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_PRESS,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    SHORT_PRESS,
    SHORT_RELEASE,
    TRIPLE_PRESS,
)
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    PhilipsBasicCluster,
    PhilipsRemoteCluster,
)


class PhilipsRdmRemoteCluster(PhilipsRemoteCluster):
    """Philips remote cluster for RDM devices."""

    BUTTONS = {
        1: BUTTON_1,
        2: BUTTON_2,
        3: BUTTON_3,
        4: BUTTON_4,
    }
    PRESS_TYPES = {
        0: COMMAND_PRESS,
        1: COMMAND_HOLD,
        2: SHORT_RELEASE,
        3: LONG_RELEASE,
    }


class PhilipsRDM002(CustomDevice):
    """Philips RDM002 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2096
        #  device_version=1
        #  input_clusters=[0, 1, 3, 64512, 4096]
        #  output_clusters=[25, 0, 3, 4, 6, 8, 5, 4096]>
        MODELS_INFO: [(PHILIPS, "RDM002"), (SIGNIFY, "RDM002")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsRdmRemoteCluster.cluster_id,
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
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsRdmRemoteCluster,
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

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_press"},
        (SHORT_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_press"},
        (SHORT_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_press"},
        (SHORT_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_press"},
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_double_press"},
        (DOUBLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_double_press"},
        (DOUBLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_double_press"},
        (DOUBLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_double_press"},
        (TRIPLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_triple_press"},
        (TRIPLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_triple_press"},
        (TRIPLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_triple_press"},
        (TRIPLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_triple_press"},
        (QUADRUPLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_quadruple_press"},
        (QUADRUPLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_quadruple_press"},
        (QUADRUPLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_quadruple_press"},
        (QUADRUPLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_quadruple_press"},
        (QUINTUPLE_PRESS, BUTTON_1): {COMMAND: f"{BUTTON_1}_quintuple_press"},
        (QUINTUPLE_PRESS, BUTTON_2): {COMMAND: f"{BUTTON_2}_quintuple_press"},
        (QUINTUPLE_PRESS, BUTTON_3): {COMMAND: f"{BUTTON_3}_quintuple_press"},
        (QUINTUPLE_PRESS, BUTTON_4): {COMMAND: f"{BUTTON_4}_quintuple_press"},
    }
