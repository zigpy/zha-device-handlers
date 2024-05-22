"""Tuya based cover and blinds."""

import logging

from zigpy.profiles import zha
from zigpy.quirks.v2 import add_to_registry_v2
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    ATTR_COVER_DIRECTION_SETTING_NAME,
    WINDOW_COVER_COMMAND_SMALL_STEP_NAME,
    WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
    TuyaManufacturerWindowCover,
    TuyaManufCluster,
    TuyaWindowCover,
    TuyaWindowCoverControl,
)
from zhaquirks.tuya.mcu import (
    CoverCommandStepDirection,
    CoverSettingLimitOperation,
    CoverSettingMotorDirection,
    TuyaNewManufClusterForWindowCover,
    TuyaNewWindowCoverControl,
    TuyaPowerConfigurationCluster,
)

_LOGGER = logging.getLogger(__name__)


class TuyaZemismartSmartCover0601(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_fzo2pocs", "TS0601"),
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
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_inv_controls(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    tuya_cover_command = {0x0000: 0x0002, 0x0001: 0x0000, 0x0002: 0x0001}

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_cowvfni3", "TS0601"),
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
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_inv_position(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    tuya_cover_inverted_by_default = True

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_zpzndjez", "TS0601"),
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
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_3(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_fzo2pocs", "TS0601"),
            ("_TZE200_iossyxra", "TS0601"),
            ("_TZE200_pw7mji0l", "TS0601"),
            ("_TZE200_9vpe3fl1", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_3_inv_position(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    tuya_cover_inverted_by_default = True

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_zpzndjez", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_2(TuyaWindowCover):
    """Tuya Zemismart curtain cover motor."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x000a, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81 input_clusters=[0, 10, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_3i3exuay", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Time.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_2_inv_position(TuyaWindowCover):
    """Tuya Zemismart curtain cover motor."""

    tuya_cover_inverted_by_default = True

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x000a, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81 input_clusters=[0, 10, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_wmcdj3aq", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Time.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaMoesCover0601(TuyaWindowCover):
    """Tuya blind controller device."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        #                    maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                    maximum_outgoing_transfer_size=82, descriptor_capability_field=0)",
        # "endpoints": {
        # "1": { "profile_id": 260, "device_type": "0x0051", "in_clusters": [ "0x0000", "0x0004","0x0005","0xef00"], "out_clusters": ["0x000a","0x0019"] }
        # },
        # "manufacturer": "_TZE200_zah67ekd",
        # "model": "TS0601",
        # "class": "zigpy.device.Device"
        # }
        MODELS_INFO: [
            ("_TZE200_zah67ekd", "TS0601"),
            ("_TZE200_nueqqe6k", "TS0601"),
            ("_TZE200_gubdgai2", "TS0601"),
            ("_TZE200_5sbebbzs", "TS0601"),
            ("_TZE200_hsgrhjpf", "TS0601"),
            ("_TZE200_68nvbio9", "TS0601"),
            ("_TZE200_ergbiejo", "TS0601"),
            ("_TZE200_nhyj64w2", "TS0601"),
            ("_TZE200_cf1sl3tj", "TS0601"),
            ("_TZE200_7eue9vhc", "TS0601"),
            ("_TZE200_bv1jcqqu", "TS0601"),
            ("_TZE200_nw1r9hp6", "TS0601"),
            ("_TZE200_gaj531w3", "TS0601"),
            ("_TZE200_icka1clh", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaMoesCover0601_alt_controls(TuyaWindowCover):
    """Tuya blind controller device."""

    tuya_cover_command = {0x0000: 0x0002, 0x0001: 0x0001, 0x0002: 0x0000}

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        #                    maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                    maximum_outgoing_transfer_size=82, descriptor_capability_field=0)",
        # "endpoints": {
        # "1": { "profile_id": 260, "device_type": "0x0051", "in_clusters": [ "0x0000", "0x0004","0x0005","0xef00"], "out_clusters": ["0x000a","0x0019"] }
        # },
        # "manufacturer": "_TZE200_zah67ekd",
        # "model": "TS0601",
        # "class": "zigpy.device.Device"
        # }
        MODELS_INFO: [
            ("_TZE200_rddyvrci", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaMoesCover0601_inv_position(TuyaWindowCover):
    """Tuya blind controller device."""

    tuya_cover_inverted_by_default = True

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        #                    maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                    maximum_outgoing_transfer_size=82, descriptor_capability_field=0)",
        # "endpoints": {
        # "1": { "profile_id": 260, "device_type": "0x0051", "in_clusters": [ "0x0000", "0x0004","0x0005","0xef00"], "out_clusters": ["0x000a","0x0019"] }
        # },
        # "model": "TS0601",
        # "class": "zigpy.device.Device"
        # }
        MODELS_INFO: [
            ("_TZE200_xuzcvlku", "TS0601"),
            ("_TZE200_yenbr4om", "TS0601"),
            ("_TZE200_xaabybja", "TS0601"),
            ("_TZE200_zuz7f94z", "TS0601"),
            ("_TZE200_3i3exuay", "TS0601"),
            ("_TZE200_nogaemzt", "TS0601"),
            ("_TZE200_dng9fn0k", "TS0601"),
            ("_TZE200_9p5xmj5r", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaCloneCover0601(TuyaWindowCover):
    """Tuya blind controller device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256 device_version=0
        # input_clusters=[0, 3, 4, 5, 6]
        # output_clusters=[25]>
        # },
        # "manufacturer": "_TYST11_wmcdj3aq",
        # "model": "mcdj3aq",
        # "class": "zigpy.device.Device"
        # }
        MODELS_INFO: [("_TYST11_wmcdj3aq", "mcdj3aq")],  # Not tested
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }


def register_v2_quirks() -> None:
    """Register v2 Quirks."""

    # Tuya window cover device.
    #
    # This variant supports:
    #     - multiple data points included in tuya set_data_response.
    #     - non-inverted control inputs,
    #     - battery percentage remaining
    #
    # Most/all the quirks above are based on TuyaManufacturerWindowCover that only decodes
    # ONE attribute from the Tuya set_data_response packet. This quirk is based on
    # TuyaNewManufClusterForWindowCover which can handle multiple updates in one zigby frame.
    #
    # "_TZE200_eevqq1uv", "TS0601" - Zemismart ZM25R3 roller blind motor
    add_to_registry_v2("_TZE200_68nvbio9", "TS0601"
    ).also_applies_to("_TZE200_eevqq1uv", "TS0601"
    ).replaces(TuyaNewManufClusterForWindowCover
    ).adds(TuyaNewWindowCoverControl
    ).adds(TuyaPowerConfigurationCluster
    ).command_button(
        WINDOW_COVER_COMMAND_SMALL_STEP_NAME,
        TuyaNewWindowCoverControl.cluster_id,
        None,
        {"direction": CoverCommandStepDirection.Open},
        entity_type=EntityType.STANDARD,
        translation_key="small_step_open",
    ).command_button(
        WINDOW_COVER_COMMAND_SMALL_STEP_NAME,
        TuyaNewWindowCoverControl.cluster_id,
        None,
        {"direction": CoverCommandStepDirection.Close},
        entity_type=EntityType.STANDARD,
        translation_key="small_step_close",
    ).enum(
        ATTR_COVER_DIRECTION_SETTING_NAME,
        CoverSettingMotorDirection,
        TuyaNewWindowCoverControl.cluster_id,
        translation_key="motor_direction",
    ).command_button(
        WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
        TuyaNewWindowCoverControl.cluster_id,
        None,
        {"operation": CoverSettingLimitOperation.SetOpen},
        translation_key="set_open_limit",
    ).command_button(
        WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
        TuyaNewWindowCoverControl.cluster_id,
        None,
        {"operation": CoverSettingLimitOperation.SetClose},
        translation_key="set_close_limit",
    ).command_button(
        WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
        TuyaNewWindowCoverControl.cluster_id,
        None,
        {"operation": CoverSettingLimitOperation.ClearOpen},
        translation_key="clear_open_limit",
    ).command_button(
        WINDOW_COVER_COMMAND_UPDATE_LIMITS_NAME,
        TuyaNewWindowCoverControl.cluster_id,
        None,
        {"operation": CoverSettingLimitOperation.ClearClose},
        translation_key="clear_close_limit",
    )


(
    register_v2_quirks()
)
