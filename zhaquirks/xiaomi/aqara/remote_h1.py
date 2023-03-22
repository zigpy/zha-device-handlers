class RemoteH1DoubleRocker3(XiaomiCustomDevice):
    """Aqara H1 Wireless Remote Double Rocker Version WRS-R02, variant 3."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.remote.b28ac1")],
        ENDPOINTS: {
            1: {
                # "1": {
                #   "profile_id": 260, "device_type": "0x0105",
                #   "in_clusters": ["0x0000", "0x0001", "0x0003"],
                #   "out_clusters": ["0x0003", "0x0006", "0x0008", "0x0300"] }
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                # "2": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003"],
                #   "out_clusters": ["0x0003", "0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                # "3": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003"],
                #   "out_clusters": ["0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            4: {},
            5: {},
            6: {},
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationClusterH1Remote,
                    MultistateInputCluster,
                    AqaraRemoteManuSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        }
    }
    device_automation_triggers = RemoteH1DoubleRocker1.device_automation_triggers


class RemoteH1DoubleRocker4(XiaomiCustomDevice):
    """Aqara H1 Wireless Remote Double Rocker Version WRS-R02, variant 4."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.remote.b28ac1")],
        ENDPOINTS: {
            1: {
                # "1": {
                #   "profile_id": 260, "device_type": "0x0105",
                #   "in_clusters": ["0x0000", "0x0001", "0x0003"],
                #   "out_clusters": ["0x0003", "0x0006", "0x0008", "0x0300"] }
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                # "2": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003"],
                #   "out_clusters": ["0x0003", "0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                # "3": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003"],
                #   "out_clusters": ["0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            4: {
                # "4": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003, 0x0012"],
                #   "out_clusters": ["0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            5: {
                # "5": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003, 0x0012"],
                #   "out_clusters": ["0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            6: {
                # "6": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": ["0x0003, 0x0012"],
                #   "out_clusters": ["0x0006"] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationClusterH1Remote,
                    MultistateInputCluster,
                    AqaraRemoteManuSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        }
    }
    device_automation_triggers = RemoteH1DoubleRocker1.device_automation_triggers


class RemoteH1DoubleRocker5(XiaomiCustomDevice):
    """Aqara H1 Wireless Remote Double Rocker Version WRS-R02, variant 5."""

    signature = {
        MODELS_INFO: [(None, None)],
        ENDPOINTS: {
            1: {
                # "1": {
                #   "profile_id": 260, "device_type": "0x0105",
                #   "in_clusters": [],
                #   "out_clusters": [] }
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
            2: {
                # "2": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": [],
                #   "out_clusters": [] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                # "3": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": [],
                #   "out_clusters": [] },
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
    replacement = {
        MODELS_INFO: [(LUMI, "lumi.remote.b28ac1")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationClusterH1Remote,
                    MultistateInputCluster,
                    AqaraRemoteManuSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        },
    }
    device_automation_triggers = RemoteH1DoubleRocker1.device_automation_triggers
