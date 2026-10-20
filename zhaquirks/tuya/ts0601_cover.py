"""Tuya based cover and blinds."""

from zigpy.profiles import zha
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
from typing import Any

from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks.tuya import (
    COVER_EVENT,
    TUYA_CLUSTER_ID,
    TUYA_GET_DATA,
    TUYA_SET_DATA,
    TUYA_SET_DATA_RESPONSE,
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


class InvertedTuyaManufacturerWindowCover(TuyaManufacturerWindowCover):
    """Invert position, handle DP 21 continuous angle tilt, and ACK incoming reports."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Any = None,
    ) -> None:
        if hdr.command_id in (TUYA_GET_DATA, TUYA_SET_DATA_RESPONSE):
            tuya_payload = args[0]
            dp_id = tuya_payload.command_id & 0xFF
            dp_type = tuya_payload.command_id >> 8

            # DP 21: Tilt angle in degrees (0 - 180) -> map to 0 - 100%
            if dp_id == 21 and dp_type == 2:
                try:
                    angle = tuya_payload.data[4]
                    tilt_pct = max(0, min(100, round(angle / 1.8)))
                    self.endpoint.device.cover_bus.listener_event(
                        COVER_EVENT,
                        WindowCovering.AttributeDefs.current_position_tilt_percentage.id,
                        tilt_pct,
                    )
                except Exception as e:
                    self.warning("Error parsing DP 21 angle: %s", e)

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

        # ACK to prevent motor retransmit storms
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, foundation.Status.SUCCESS)

    def _update_attribute(self, attrid, value):
        if attrid == 0x0008:
            try:
                inverted_value = 100 - int(value)
                super()._update_attribute(attrid, inverted_value)
                return
            except (ValueError, TypeError) as e:
                self.debug(f"Error inverting position {value}: {e}")
        super()._update_attribute(attrid, value)


class TuyaDreamBlindsControl(TuyaWindowCoverControl):
    """Window covering control cluster with 0-180 degree tilt/dimming support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_attribute(
            WindowCovering.AttributeDefs.window_covering_type.id,
            WindowCovering.WindowCoveringType.Tilt_blind_tilt_and_lift,
        )

    def get(self, key: int | str, default: Any | None = None) -> Any:
        attr_def = self.find_attribute(key)
        if attr_def and attr_def.id == WindowCovering.AttributeDefs.window_covering_type.id:
            return WindowCovering.WindowCoveringType.Tilt_blind_tilt_and_lift
        if attr_def and attr_def.id == WindowCovering.AttributeDefs.current_position_tilt_percentage.id:
            val = super().get(key, default)
            return 50 if val is None else val
        return super().get(key, default)

    def cover_event(self, attribute, value):
        if attribute == WindowCovering.AttributeDefs.current_position_tilt_percentage.id:
            self._update_attribute(attribute, value)
        else:
            super().cover_event(attribute, value)

    def command(
        self,
        command_id: foundation.GeneralCommand | int | Any,
        *args,
        manufacturer: int | Any = None,
        expect_reply: bool = True,
        tsn: int | Any = None,
        **kwargs: Any,
    ):
        # 0x0008 = go_to_tilt_percentage
        if command_id == 8:
            target_pct = args[0]
            # Map 0-100% to 0-180 degrees
            angle = max(0, min(180, round(target_pct * 1.8)))

            tuya_payload = TuyaManufCluster.Command()
            tuya_payload.status = 0
            tuya_payload.tsn = tsn if tsn else 0
            tuya_payload.command_id = (2 << 8) + 21  # DP 21 (0x0215, Type 2 VALUE)
            tuya_payload.function = 0
            tuya_payload.data = [4, 0, 0, 0, angle]

            self._update_attribute(
                WindowCovering.AttributeDefs.current_position_tilt_percentage.id,
                target_pct,
            )
            return self.endpoint.tuya_manufacturer.command(
                TUYA_SET_DATA, tuya_payload, expect_reply=True
            )

        return super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


class TuyaDreamBlindsCover0601(TuyaWindowCover):
    """Quirk for Tuya Vertical Dream Blinds (_TZE204_wzre8hu2 TS0601)."""

    signature = {
        MODELS_INFO: [
            ("_TZE204_wzre8hu2", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0051,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 0xa1e0,
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
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    InvertedTuyaManufacturerWindowCover,
                    TuyaDreamBlindsControl,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 0xa1e0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
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
