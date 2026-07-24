"""Tuya based cover and blinds."""

from zigpy.profiles import zha
from zhaquirks.builder import EntityType
import zigpy.types as t
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
    TUYA_CLUSTER_ID,
    TuyaManufacturerWindowCover,
    TuyaManufCluster,
    TuyaWindowCover,
    TuyaWindowCoverControl,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder


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
            ("_TZE200_sq6affpe", "TS0601"),
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
            ("_TZE200_ba69l9ol", "TS0601"),
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
            ("_TZE200_vdiuwbkq", "TS0601"),
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
            ("_TZE200_1vxgqfba", "TS0601"),
            ("_TZE200_fctwhugx", "TS0601"),
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


class TuyaMoesCover0601_alt_controls2(TuyaWindowCover):
    """Tuya blind controller device."""

    tuya_cover_command = {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001}
    tuya_cover_inverted_by_default = True

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0,
        #                    user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        #                    mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>,
        #                    manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                    maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>,
        #                    *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False,
        #                    *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        # "endpoints": {
        # "1": { "profile_id": 260, "device_type": "0x0051", "in_clusters": [ "0x0000", "0x0004","0x0005","0x0102","0xef00"], "out_clusters": ["0x000a","0x0019"] }
        # },
        # "manufacturer": "_TZE200_2odrmqwq",
        # "model": "TS0601",
        # "class": "zigpy.device.Device"
        # }
        MODELS_INFO: [
            ("_TZE200_2odrmqwq", "TS0601"),
            ("_TZE200_hojryzzd", "TS0601"),
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


class MotorDirection(t.enum8):
    """Motor direction values."""

    Forward = 0x00
    Back = 0x01


class BorderSetting(t.enum8):
    """Border/limit setting values."""

    Up = 0x00
    Down = 0x01
    Up_delete = 0x02
    Down_delete = 0x03
    Remove_top_bottom = 0x04


(
    TuyaQuirkBuilder("_TZE284_3mzb0sdz", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=8, position_control_dp=9)
    .tuya_battery(dp_id=13)
    .tuya_enum(
        dp_id=11,
        attribute_name="motor_direction",
        enum_class=MotorDirection,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .tuya_dp_attribute(
        dp_id=16,
        attribute_name="border",
        type=BorderSetting,
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Up,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_up",
        translation_key="set_upper_limit",
        fallback_name="Set upper limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Down,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_down",
        translation_key="set_lower_limit",
        fallback_name="Set lower limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Up_delete,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_up_delete",
        translation_key="delete_upper_limit",
        fallback_name="Delete upper limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Down_delete,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_down_delete",
        translation_key="delete_lower_limit",
        fallback_name="Delete lower limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Remove_top_bottom,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_remove_all",
        translation_key="delete_all_limits",
        fallback_name="Delete all limits",
    )
    .skip_configuration()
    .add_to_registry()
)


# Curtain motor / roller blind motor (standard Tuya cover protocol)
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_1.html
(
    TuyaQuirkBuilder("_TZE200_5zbp6j0u", "TS0601")
    .applies_to("_TZE200_nkoabg8w", "TS0601")
    .applies_to("_TZE200_4vobcgd3", "TS0601")
    .applies_to("_TZE284_4vobcgd3", "TS0601")
    .applies_to("_TZE200_r0jdjrvi", "TS0601")
    .applies_to("_TZE200_pk0sfzvr", "TS0601")
    .applies_to("_TZE200_fdtjuw7u", "TS0601")
    .applies_to("_TZE200_bqcqqjpb", "TS0601")
    .applies_to("_TZE200_rmymn92d", "TS0601")
    .applies_to("_TZE200_feolm6rk", "TS0601")
    .applies_to("_TZE200_tvrvdj6o", "TS0601")
    .applies_to("_TZE200_b2u1drdv", "TS0601")
    .applies_to("_TZE200_ol5jlkkr", "TS0601")
    .applies_to("_TZE204_guvc7pdy", "TS0601")
    .applies_to("_TZE200_zxxfv8wi", "TS0601")
    .applies_to("_TZE200_1fuxihti", "TS0601")
    .applies_to("_TZE284_1fuxihti", "TS0601")
    .applies_to("_TZE204_1fuxihti", "TS0601")
    .applies_to("_TZE204_57hjqelq", "TS0601")
    .applies_to("_TZE204_vvvtcehj", "TS0601")
    .applies_to("_TZE204_m1wl5fvq", "TS0601")
    .applies_to("_TZE200_en3wvcbx", "TS0601")
    .applies_to("_TZE200_g5wdnuow", "TS0601")
    .applies_to("_TZE200_udank5zs", "TS0601")
    .applies_to("_TZE204_dpqsvdbi", "TS0601")
    .applies_to("_TZE200_nv6nxo0c", "TS0601")
    .applies_to("_TZE200_3ylew7b4", "TS0601")
    .applies_to("_TZE200_llm0epxg", "TS0601")
    .applies_to("_TZE200_n1aauwb4", "TS0601")
    .applies_to("_TZE200_xu4a5rhj", "TS0601")
    .applies_to("_TZE200_bjzrowv2", "TS0601")
    .applies_to("_TZE284_bjzrowv2", "TS0601")
    .applies_to("_TZE204_bjzrowv2", "TS0601")
    .applies_to("_TZE200_axgvo9jh", "TS0601")
    .applies_to("_TZE284_gaj531w3", "TS0601")
    .applies_to("_TZE200_yia0p3tr", "TS0601")
    .applies_to("_TZE200_rsj5pu8y", "TS0601")
    .applies_to("_TZE200_yrugsphv", "TS0601")
    .applies_to("_TZE204_yrugsphv", "TS0601")
    .applies_to("_TZE204_nladmfvf", "TS0601")
    .applies_to("_TZE204_lh3arisb", "TS0601")
    .applies_to("_TZE284_udank5zs", "TS0601")
    .applies_to("_TZE284_b7kbnl6q", "TS0601")
    .applies_to("_TZE200_7shyddj3", "TS0601")
    .applies_to("_TZE204_a2jcoyuk", "TS0601")
    .applies_to("_TZE204_ic7jtutb", "TS0601")
    .applies_to("_TZE204_odlldrxx", "TS0601")
    .applies_to("_TZE204_wzre8hu2", "TS0601")
    .applies_to("_TZE200_odlldrxx", "TS0601")
    .applies_to("_TZE200_m6lwazh9", "TS0601")
    .applies_to("_TZE204_zuq5xxib", "TS0601")
    .applies_to("_TZE204_xu4a5rhj", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .skip_configuration()
    .add_to_registry()
)


# Curtain motor with fixed speed
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_2.html
(
    TuyaQuirkBuilder("_TZE200_eegnwoyw", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .skip_configuration()
    .add_to_registry()
)


class OpeningMode(t.enum8):
    """Opening mode values."""

    Tilt = 0x00
    Lift = 0x01


class MotorSide(t.enum8):
    """Motor side values."""

    Left = 0x00
    Right = 0x01


# Cover motor with battery, illuminance, opening mode
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_6.html
(
    TuyaQuirkBuilder("_TZE200_cpbo62rn", "TS0601")
    .applies_to("_TZE200_libht6ua", "TS0601")
    .applies_to("_TZE284_libht6ua", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .tuya_battery(dp_id=13)
    .tuya_illuminance(dp_id=104)
    .tuya_enum(
        dp_id=4,
        attribute_name="opening_mode",
        enum_class=OpeningMode,
        entity_type=EntityType.CONFIG,
        translation_key="opening_mode",
        fallback_name="Opening mode",
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="motor_side",
        enum_class=MotorSide,
        entity_type=EntityType.CONFIG,
        translation_key="motor_side",
        fallback_name="Motor side",
    )
    .skip_configuration()
    .add_to_registry()
)


# Cover motor with battery
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_7.html
(
    TuyaQuirkBuilder("_TZE200_zvo63cmo", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_battery(dp_id=101)
    .skip_configuration()
    .add_to_registry()
)


class CoverMotorDirection(t.enum8):
    """Cover motor direction values."""

    Forward = 0x00
    Back = 0x01


class MotorWorkingMode(t.enum8):
    """Motor working mode values."""

    Continuous = 0x00
    Intermittently = 0x01


# Cover motor with direction, fault, and stroke limits
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_8.html
(
    TuyaQuirkBuilder("_TZE204_r0jdjrvi", "TS0601")
    .applies_to("_TZE200_g5xqosu7", "TS0601")
    .applies_to("_TZE204_g5xqosu7", "TS0601")
    .applies_to("_TZE284_fzo2pocs", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=CoverMotorDirection,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .tuya_binary_sensor(
        dp_id=12,
        attribute_name="motor_fault",
        translation_key="motor_fault",
        fallback_name="Motor fault",
    )
    .tuya_enum(
        dp_id=106,
        attribute_name="motor_working_mode",
        enum_class=MotorWorkingMode,
        entity_type=EntityType.CONFIG,
        translation_key="motor_working_mode",
        fallback_name="Motor working mode",
    )
    .skip_configuration()
    .add_to_registry()
)


class MotorDirectionNormalReversed(t.enum8):
    """Motor direction normal/reversed values."""

    Normal = 0x00
    Reversed = 0x01


# Cover motor with battery and motor direction
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_9.html
(
    TuyaQuirkBuilder("_TZE200_p2qzzazi", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_battery(dp_id=101)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=MotorDirectionNormalReversed,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .skip_configuration()
    .add_to_registry()
)


# Cover motor with motor direction
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_10.html
(
    TuyaQuirkBuilder("_TZE200_clm4gdw4", "TS0601")
    .applies_to("_TZE200_2vfxweng", "TS0601")
    .applies_to("_TZE200_gnw1rril", "TS0601")
    .applies_to("_TZE204_ycke4deo", "TS0601")
    .applies_to("_TZE284_koxaopnk", "TS0601")
    .applies_to("_TZE284_clm4gdw4", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=MotorDirectionNormalReversed,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .skip_configuration()
    .add_to_registry()
)


# Pro Line Zigbee curtain motor (ZM79E-DT)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZM79E-DT.html
(
    TuyaQuirkBuilder("_TZE200_ax8a8ahx", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2)
    .tuya_enum(
        dp_id=4,
        attribute_name="opening_mode",
        enum_class=OpeningMode,
        entity_type=EntityType.CONFIG,
        translation_key="opening_mode",
        fallback_name="Opening mode",
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="motor_side",
        enum_class=MotorSide,
        entity_type=EntityType.CONFIG,
        translation_key="motor_side",
        fallback_name="Motor side",
    )
    .skip_configuration()
    .add_to_registry()
)


# Cover motor (BX82-TYZ1)
# Z2M reference: https://www.zigbee2mqtt.io/devices/BX82-TYZ1.html
(
    TuyaQuirkBuilder("_TZE204_2rvvqjoa", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=MotorDirectionNormalReversed,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .skip_configuration()
    .add_to_registry()
)


# Cover motor with battery, direction, fault, and border settings
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_3.html
(
    TuyaQuirkBuilder("_TZE200_eevqq1uv", "TS0601")
    .applies_to("_TZE204_ejh6owwz", "TS0601")
    .applies_to("_TZE200_68nvbi09", "TS0601")
    .applies_to("_TZE200_vexa5o82", "TS0601")
    .applies_to("_TZE200_sfqyhvpv", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_battery(dp_id=13)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=CoverMotorDirection,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .tuya_binary_sensor(
        dp_id=12,
        attribute_name="motor_fault",
        translation_key="motor_fault",
        fallback_name="Motor fault",
    )
    .tuya_dp_attribute(
        dp_id=16,
        attribute_name="border",
        type=BorderSetting,
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Up,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_up",
        translation_key="set_upper_limit",
        fallback_name="Set upper limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Down,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_down",
        translation_key="set_lower_limit",
        fallback_name="Set lower limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Up_delete,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_up_delete",
        translation_key="delete_upper_limit",
        fallback_name="Delete upper limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Down_delete,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_down_delete",
        translation_key="delete_lower_limit",
        fallback_name="Delete lower limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Remove_top_bottom,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_remove_all",
        translation_key="delete_all_limits",
        fallback_name="Delete all limits",
    )
    .skip_configuration()
    .add_to_registry()
)


# Ayvolt Blinds
# Z2M reference: https://www.zigbee2mqtt.io/devices/_TZE204_q9xty0ad.html
(
    TuyaQuirkBuilder("_TZE204_q9xty0ad", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=8, position_control_dp=9)
    .tuya_enum(
        dp_id=11,
        attribute_name="motor_direction",
        enum_class=MotorDirectionNormalReversed,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .skip_configuration()
    .add_to_registry()
)


class CoverDotMode(t.enum8):
    """Cover dot mode values."""

    Single = 0x00
    Multi = 0x01


class CoverBorderMode(t.enum8):
    """Cover border mode values."""

    Up = 0x00
    Down = 0x01
    Delete = 0x02


# Cover motor with speed and dot mode
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_11.html
(
    TuyaQuirkBuilder("_TZE284_r3szw0xr", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=9, position_control_dp=8)
    .tuya_enum(
        dp_id=11,
        attribute_name="motor_direction",
        enum_class=MotorDirectionNormalReversed,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="motor_speed",
        type=t.uint16_t,
        min_value=1,
        max_value=5,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="motor_speed",
        fallback_name="Motor speed",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="dot_mode",
        enum_class=CoverDotMode,
        entity_type=EntityType.CONFIG,
        translation_key="dot_mode",
        fallback_name="Dot mode",
    )
    .skip_configuration()
    .add_to_registry()
)


# Curtain motor with battery and direction
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_cover_12.html
(
    TuyaQuirkBuilder("_TZE200_mlglxwp3", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_battery(dp_id=103)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=CoverMotorDirection,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .skip_configuration()
    .add_to_registry()
)


# Zigbee roller shade motor (RM28-LE)
# Z2M reference: https://www.zigbee2mqtt.io/devices/RM28-LE.html
(
    TuyaQuirkBuilder("_TZE200_fodv6bkr", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_battery(dp_id=13)
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=CoverMotorDirection,
        entity_type=EntityType.CONFIG,
        translation_key="motor_direction",
        fallback_name="Motor direction",
    )
    .tuya_binary_sensor(
        dp_id=12,
        attribute_name="motor_fault",
        translation_key="motor_fault",
        fallback_name="Motor fault",
    )
    .tuya_dp_attribute(
        dp_id=16,
        attribute_name="border",
        type=BorderSetting,
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Up,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_up",
        translation_key="set_upper_limit",
        fallback_name="Set upper limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Down,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_down",
        translation_key="set_lower_limit",
        fallback_name="Set lower limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Up_delete,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_up_delete",
        translation_key="delete_upper_limit",
        fallback_name="Delete upper limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Down_delete,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_down_delete",
        translation_key="delete_lower_limit",
        fallback_name="Delete lower limit",
    )
    .write_attr_button(
        attribute_name="border",
        attribute_value=BorderSetting.Remove_top_bottom,
        cluster_id=TUYA_CLUSTER_ID,
        unique_id_suffix="border_remove_all",
        translation_key="delete_all_limits",
        fallback_name="Delete all limits",
    )
    .skip_configuration()
    .add_to_registry()
)


class CoverControlBack(t.enum8):
    """Cover control back direction values."""

    Forward = 0x00
    Back = 0x01


# Cover plug-in receiver (PIMS3028)
# Z2M reference: https://www.zigbee2mqtt.io/devices/PIMS3028.html
(
    TuyaQuirkBuilder("_TZE200_eqpaxqdv", "TS0601")
    .tuya_cover(control_dp=1, position_state_dp=3, position_control_dp=2, invert=False)
    .tuya_enum(
        dp_id=5,
        attribute_name="control_back",
        enum_class=CoverControlBack,
        entity_type=EntityType.CONFIG,
        translation_key="control_back",
        fallback_name="Motor running direction",
    )
    .tuya_switch(
        dp_id=6,
        attribute_name="auto_power",
        entity_type=EntityType.CONFIG,
        translation_key="auto_power",
        fallback_name="Auto power",
    )
    .tuya_binary_sensor(
        dp_id=12,
        attribute_name="fault",
        translation_key="fault",
        fallback_name="Fault",
    )
    .skip_configuration()
    .add_to_registry()
)
