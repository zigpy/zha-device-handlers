"""Aqara Z1 Pro single rocker switch quirks."""

import logging
import sys

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    ACTION,
    ARGS,
    ATTRIBUTE_ID,
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_SLIDER_EVENT,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    SLIDER,
    SLIDER_DOUBLE,
    SLIDER_DOWN,
    SLIDER_HOLD,
    SLIDER_SINGLE,
    SLIDER_UP,
    VALUE,
)
from zhaquirks.xiaomi import (
    AnalogInputCluster,
    AqaraZ1ProManufacturerSpecificCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    OnOffCluster,
    XiaomiCustomDevice,
)
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster

# Set up logging with a more visible format
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# Add a console handler to ensure logs go to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
_LOGGER.addHandler(console_handler)

# Log at module level to verify the file is being loaded
_LOGGER.debug(
    "AqaraZ1ProSingleRockerSwitch quirk module is being loaded! ZHA Profile ID: 0x%04x, Device Type: 0x%04x",
    zha.PROFILE_ID,
    zha.DeviceType.ON_OFF_SWITCH,
)


class AqaraZ1ProSingleRockerSwitch(XiaomiCustomDevice):
    """Aqara Z1 Pro Single Rocker Switch."""

    MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFCC0
    XIAOMI_COMMAND_SINGLE = "1_single"

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        _LOGGER.debug(
            "AqaraZ1ProSingleRockerSwitch device initialized with IEEE: %s", self.ieee
        )

    signature = {
        MODELS_INFO: [("Aqara", "lumi.switch.acn056")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # input_clusters=[0, 3, 4, 5, 6, 18, 1794, 2820, 64704]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    MeteringCluster.cluster_id,
                    ElectricalMeasurementCluster.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=0
            # input_clusters=[64704]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=0
            # input_clusters=[64704]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=0
            # input_clusters=[64704]
            # output_clusters=[]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=21 profile=260 device_type=0
            # input_clusters=[12]
            # output_clusters=[]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    AqaraZ1ProManufacturerSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {
            COMMAND: XIAOMI_COMMAND_SINGLE,
            CLUSTER_ID: 18,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: 85, VALUE: 1},
        },
        (SHORT_PRESS, SLIDER): {
            COMMAND: COMMAND_SLIDER_EVENT,
            CLUSTER_ID: 64704,
            ENDPOINT_ID: 1,
            ARGS: {ACTION: SLIDER_SINGLE, VALUE: 1},
        },
        (DOUBLE_PRESS, SLIDER): {
            COMMAND: COMMAND_SLIDER_EVENT,
            CLUSTER_ID: 64704,
            ENDPOINT_ID: 1,
            ARGS: {ACTION: SLIDER_DOUBLE, VALUE: 2},
        },
        (LONG_PRESS, SLIDER): {
            COMMAND: COMMAND_SLIDER_EVENT,
            CLUSTER_ID: 64704,
            ENDPOINT_ID: 1,
            ARGS: {ACTION: SLIDER_HOLD, VALUE: 3},
        },
        (DIM_UP, SLIDER): {
            COMMAND: COMMAND_SLIDER_EVENT,
            CLUSTER_ID: 64704,
            ENDPOINT_ID: 1,
            ARGS: {ACTION: SLIDER_UP, VALUE: 4},
        },
        (DIM_DOWN, SLIDER): {
            COMMAND: COMMAND_SLIDER_EVENT,
            CLUSTER_ID: 64704,
            ENDPOINT_ID: 1,
            ARGS: {ACTION: SLIDER_DOWN, VALUE: 5},
        },
    }
