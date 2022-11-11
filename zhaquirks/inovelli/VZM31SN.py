"""VZM31-SN Two in One Switch/Dimmer Module."""

from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, Inovelli_VZM31SN_Cluster

INOVELLI_VZM31SN_CLUSTER_ID = 64561
WWAH_CLUSTER_ID = 64599


class InovelliVZM31SNv12(CustomDevice):
    """VZM31-SN 2 in 1 Switch/Dimmer Module Firmware version 2.08 and above."""

    signature = {
        MODELS_INFO: [("Inovelli", "VZM31-SN")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    device_automation_triggers = INOVELLI_AUTOMATION_TRIGGERS


class InovelliVZM31SNv11(CustomDevice):
    """VZM31-SN 2 in 1 Switch/Dimmer Module."""

    signature = {
        MODELS_INFO: [("Inovelli", "VZM31-SN")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    device_automation_triggers = INOVELLI_AUTOMATION_TRIGGERS


class InovelliVZM31SNv10(CustomDevice):
    """VZM31-SN 2 in 1 Switch/Dimmer Module."""

    signature = {
        MODELS_INFO: [("Inovelli", "VZM31-SN")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
        },
    }

    device_automation_triggers = INOVELLI_AUTOMATION_TRIGGERS


class InovelliVZM31SNv9(CustomDevice):
    """VZM31-SN 2 in 1 Switch/Dimmer Module."""

    signature = {
        MODELS_INFO: [("Inovelli", "VZM31-SN")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
        },
    }

    device_automation_triggers = INOVELLI_AUTOMATION_TRIGGERS


class InovelliVZM31SN(CustomDevice):
    """VZM31-SN 2 in 1 Switch/Dimmer Module."""

    signature = {
        MODELS_INFO: [("Inovelli", "VZM31-SN")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    INOVELLI_VZM31SN_CLUSTER_ID,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Inovelli_VZM31SN_Cluster,
                ],
            },
        },
    }

    device_automation_triggers = INOVELLI_AUTOMATION_TRIGGERS
