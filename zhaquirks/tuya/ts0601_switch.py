"""Tuya DP based switches."""

from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.quirk_ids import TUYA_PLUG_MANUFACTURER
from zhaquirks.tuya import DPToAttributeMapping, TuyaSwitch
from zhaquirks.tuya.mcu import (
    MoesSwitchManufCluster,
    TuyaOnOff,
    TuyaOnOffManufCluster,
    TuyaOnOffNM,
)


class MoesSwitchManufClusterDP24(MoesSwitchManufCluster):
    """MoesSwitchManufCluster variant where per-gang on/off lives on DPs 24-27.

    Used by the Moes Star Feather family (SFL02-Z-1/2/3/4): the relay state for
    gang N is reported and accepted on DP (23 + N), not the upstream default DP N.
    Mappings for unused gangs are inert when the device's replacement does not
    include that endpoint.
    """

    dp_to_attribute: dict[int, DPToAttributeMapping] = (
        MoesSwitchManufCluster.dp_to_attribute.copy()
    )
    dp_to_attribute.pop(1, None)
    dp_to_attribute.pop(2, None)
    dp_to_attribute.pop(3, None)
    dp_to_attribute.pop(4, None)
    dp_to_attribute[24] = DPToAttributeMapping(
        ep_attribute=TuyaOnOff.ep_attribute,
        attribute_name="on_off",
    )
    dp_to_attribute[25] = DPToAttributeMapping(
        ep_attribute=TuyaOnOff.ep_attribute,
        attribute_name="on_off",
        endpoint_id=2,
    )
    dp_to_attribute[26] = DPToAttributeMapping(
        ep_attribute=TuyaOnOff.ep_attribute,
        attribute_name="on_off",
        endpoint_id=3,
    )
    dp_to_attribute[27] = DPToAttributeMapping(
        ep_attribute=TuyaOnOff.ep_attribute,
        attribute_name="on_off",
        endpoint_id=4,
    )

    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()
    data_point_handlers.pop(1, None)
    data_point_handlers.pop(2, None)
    data_point_handlers.pop(3, None)
    data_point_handlers.pop(4, None)
    data_point_handlers[24] = "_dp_2_attr_update"
    data_point_handlers[25] = "_dp_2_attr_update"
    data_point_handlers[26] = "_dp_2_attr_update"
    data_point_handlers[27] = "_dp_2_attr_update"


class TuyaSingleSwitchTI(TuyaSwitch):
    """Tuya single channel switch time on in cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000,0x0004, 0x0005,0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 10, 61184] output_clusters=[25]>
        MODELS_INFO: [("_TZE200_7tdtqgwv", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Time.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }


class TuyaSingleSwitchTO(TuyaSwitch):
    """Tuya single channel switch time on out cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1 input_clusters=[0, 4, 5, 61184] output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_amp6tsvy", "TS0601"),
            ("_TZE200_oisqyl4o", "TS0601"),
            ("_TZ3000_uim07oem", "TS0601"),  # ¿1 or 4 gangs?
            ("_TZE200_wfxuhoea", "TS0601"),
            ("_TZE200_tviaymwx", "TS0601"),
            ("_TZE204_ptaqh9tk", "TS0601"),  # reported in #3099
            ("_TZE200_7tdtqgwv", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaSingleSwitchGP(TuyaSwitch):
    """Tuya single channel switch with GreenPowerProxy cluster device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_d0ypnbvn", "TS0601"),  # reported in #1335
            ("_TZE200_gbagoilo", "TS0601"),  # reported in #1634
            ("_TZE204_6fk3gewc", "TS0601"),
            ("_TZE204_d0ypnbvn", "TS0601"),  # reported in #3220 & #3291
            ("_TZE204_ptaqh9tk", "TS0601"),  # reported in #2780
            ("_TZE204_v5xjyphj", "TS0601"),  # reported in #4078
            ("_TZE204_gbagoilo", "TS0601"),  # reported in #4101
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaSingleSwitchGPDP24(TuyaSwitch):
    """Tuya single channel switch (on/off on DP 24) with GreenPowerProxy.

    Same Zigbee fingerprint as TuyaSingleSwitchGP, but the relay state is on
    DP 24 instead of the upstream MoesSwitchManufCluster default DP 1.
    Confirmed by capturing physical-press DP reports from a Moes SFL02-Z-1
    1-gang touch switch (_TZE200_stvgmdjz / TS0601).
    """

    signature = {
        MODELS_INFO: [
            ("_TZE200_stvgmdjz", "TS0601"),  # Moes SFL02-Z-1 1-gang touch switch
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufClusterDP24,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaDoubleSwitchGPDP24(TuyaSwitch):
    """Tuya double channel switch (on/off on DPs 24-25) with GreenPowerProxy.

    Same Zigbee fingerprint as TuyaDoubleSwitchGP, but the per-gang relay state
    is on DPs 24 (gang 1) and 25 (gang 2) instead of the upstream defaults
    DPs 1 and 2. Used by the Moes Star Feather SFL02-Z-2 2-gang touch switch.
    """

    signature = {
        MODELS_INFO: [
            ("_TZE200_uenof8jd", "TS0601"),  # Moes SFL02-Z-2
            ("_TZE200_tzyy0rtq", "TS0601"),  # Moes SFL02-Z-2
            ("_TZE200_hktk6hze", "TS0601"),  # Nova Digital TPZ-2 (whitelabel)
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufClusterDP24,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaTripleSwitchGPDP24(TuyaSwitch):
    """Tuya triple channel switch (on/off on DPs 24-26) with GreenPowerProxy.

    Same Zigbee fingerprint as TuyaTripleSwitchGP, but the per-gang relay state
    is on DPs 24, 25, and 26 instead of the upstream defaults DPs 1, 2, 3.
    Used by the Moes Star Feather SFL02-Z-3 3-gang touch switch.
    """

    signature = {
        MODELS_INFO: [
            ("_TZE200_rd8cdssd", "TS0601"),  # Nova Digital TPZ-3 (whitelabel)
            ("_TZE200_wv9ukqca", "TS0601"),  # Moes SFL02-Z-3
            ("_TZE200_zo0cfekv", "TS0601"),  # Moes SFL02-Z-3
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufClusterDP24,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaQuadrupleSwitchGPDP24(TuyaSwitch):
    """Tuya quadruple channel switch (on/off on DPs 24-27) with GreenPowerProxy.

    Same Zigbee fingerprint as TuyaQuadrupleSwitchGP, but the per-gang relay
    state is on DPs 24, 25, 26, and 27 instead of the upstream defaults DPs
    1, 2, 3, 4. Used by the Moes Star Feather SFL02-Z-4 4-gang touch switch.
    """

    signature = {
        MODELS_INFO: [
            ("_TZE200_dq8bu0pt", "TS0601"),  # Moes SFL02-Z-4
            ("_TZE200_hmabvy81", "TS0601"),  # Nova Digital TPZ-4 (whitelabel)
            ("_TZE200_9dhenr94", "TS0601"),  # Moes SFL02-Z-4
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufClusterDP24,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaDoubleSwitchTO(TuyaSwitch):
    """Tuya double channel switch time on out cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1 input_clusters=[0, 4, 5, 61184] output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_g1ib5ldv", "TS0601"),
            ("_TZE200_wunufsil", "TS0601"),
            ("_TZE200_nkjintbl", "TS0601"),
            ("_TZE204_wvovwe9h", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaDoubleSwitchGP(TuyaSwitch):
    """Tuya double channel switch with GreenPowerProxy cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        MODELS_INFO: [
            ("_TZE200_7deq70b8", "TS0601"),
            ("_TZE200_nh9m9emk", "TS0601"),  # reported in #1634
            ("_TZE204_nh9m9emk", "TS0601"),  # reported in #4100
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaDoubleSwitchNOC(TuyaSwitch):
    """Tuya double channel switch with No Output Clusters."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_wvovwe9h", "TS0601"),  # reported in #4077
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOff],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaTripleSwitchTO(TuyaSwitch):
    """Tuya triple channel switch time on out cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        MODELS_INFO: [
            # ("_TZE200_kyfqmmyl", "TS0601"),  ## candidate reported in #716
            ("_TZE200_tz32mtza", "TS0601"),
            ("_TZE200_vhy3iakz", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaTripleSwitchGP(TuyaSwitch):
    """Tuya triple channel switch with GreenPowerProxy cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        MODELS_INFO: [
            ("_TZE200_2hf7x9n3", "TS0601"),  # reported #1597
            ("_TZE200_go3tvswy", "TS0601"),  # reported #1634
            ("_TZE204_2imwyigp", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaTripleSwitchVar03(TuyaSwitch):
    """Tuya triple channel switch (variation 03)."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_kyfqmmyl", "TS0601"),  # reported: #2469
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaQuadrupleSwitchTO(TuyaSwitch):
    """Tuya quadruple channel switch time on out cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        MODELS_INFO: [
            ("_TZE200_aqnazj70", "TS0601"),
            ("_TZE200_1ozguk6x", "TS0601"),
            ("_TZE200_k6jhsr0q", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaQuadrupleSwitchGP(TuyaSwitch):
    """Tuya quadruple channel switch with GreenPowerProxy cluster device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_1n2kyphz", "TS0601"),
            ("_TZE200_mexisfik", "TS0601"),  # reported #1634
            ("_TZE204_58of2pfn", "TS0601"),  # 4-channel relay
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaQuintupleSwitchGP(TuyaSwitch):
    """Tuya quintuple channel switch with GreenPowerProxy cluster device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_jwsjbxjs", "TS0601"),  # reported #4219
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaQuintupleSwitchTO(TuyaSwitch):
    """Tuya quintuple channel switch time on out cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81
        # input_clusters=[0x0000,0x0004,0x0005,0xEF00]
        # output_clusters=[0x000A,0x0019]>
        MODELS_INFO: [
            ("_TZE200_leaqthqq", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaSextupleSwitchTO(TuyaSwitch):
    """Tuya sextuple channel switch time on out cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81
        # input_clusters=[0x0000,0x0004,0x0005,0xEF00]
        # output_clusters=[0x000A,0x0019]>
        MODELS_INFO: [
            ("_TZE200_9mahtqtg", "TS0601"),
            ("_TZE200_wnp4d4va", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaSextupleSwitchTOGP(TuyaSwitch):
    """Tuya sextuple channel switch time on out cluster device with GreenPowerProxy cluster device."""

    quirk_id = TUYA_PLUG_MANUFACTURER

    signature = {
        MODELS_INFO: [
            ("_TZE200_9mahtqtg", "TS0601"),
            ("_TZE200_emxxanvi", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # input_clusters=[0x0000,0x0004,0x0005,0xEF00]
            # output_clusters=[0x000A,0x0019]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaSwitchX8GP(TuyaSwitch):
    """Tuya x8 channels switch with GreenPowerProxy cluster device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_wktrysab", "TS0601"),
            ("_TZE204_wktrysab", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # input_clusters=[0x0000,0x0004,0x0005,0xEF00]
            # output_clusters=[0x000A,0x0019]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaSwitchX12GP(TuyaSwitch):
    """Tuya x12 channels switch with GreenPowerProxy cluster device."""

    signature = {
        MODELS_INFO: [
            ("_TZE204_dqolcpcp", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # input_clusters=[0x0000,0x0004,0x0005,0xEF00]
            # output_clusters=[0x000A,0x0019]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaSwitchX16GP(TuyaSwitch):
    """Tuya x16 channels switch with GreenPowerProxy cluster device."""

    signature = {
        MODELS_INFO: [
            ("_TZE204_vmcgja59", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # input_clusters=[0x0000,0x0004,0x0005,0xEF00]
            # output_clusters=[0x000A,0x0019]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffManufCluster,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            9: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            13: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            14: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            15: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            16: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
