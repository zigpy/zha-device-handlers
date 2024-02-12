"""Tuya 1,2,3 gang no neutral light switch."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    EnchantedDevice,
    TuyaSwitch,
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)


# NoNeutralSwitch family = without tuya cluster and Identify.
class TuyaSingleNoNeutralSwitch(EnchantedDevice, TuyaSwitch):
    """Tuya 1 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        MODEL: "TS0011",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
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
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaDoubleNoNeutralSwitch(EnchantedDevice, TuyaSwitch):
    """Tuya 2 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0012",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class TuyaTripleNoNeutralSwitch(EnchantedDevice, TuyaSwitch):
    """Tuya 3 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0013",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


# Switch_2 family = Normal NoNeutralSwitch (without tuya cluster) and with Identify.
class TuyaSingleNoNeutralSwitch_2(EnchantedDevice, TuyaSwitch):
    """Tuya 1 gang no neutral light switch (v2)."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        MODEL: "TS0011",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[a, 19]>
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
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaDoubleNoNeutralSwitch_2(EnchantedDevice, TuyaSwitch):
    """Tuya 2 gang no neutral light switch (v2)."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0012",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=["0x0000", "0x0003", "0x0004", "0x0005", "0x0006"]
            # output_clusters=["0x000a", "0x0019"]>
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
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class TuyaTripleNoNeutralSwitch_2(EnchantedDevice, TuyaSwitch):
    """Tuya 3 gang no neutral light switch (v2)."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0013",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[a, 19]>
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
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


# No Neutral switches with tuya clusters.
class Tuya_Single_No_N(EnchantedDevice, TuyaSwitch):
    """Tuya 1 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        MODEL: "TS0011",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
        },
    }


class Tuya_Double_No_N(EnchantedDevice, TuyaSwitch):
    """Tuya 2 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0012",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[3, 4, 5, 6, 57344, 57345]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class Tuya_Double_No_N_Plus(EnchantedDevice, TuyaSwitch):
    """Tuya 2 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0,
        # user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        # mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4417, maximum_buffer_size=66,
        # maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66,
        # descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False,
        # *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False,
        # *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        MODEL: "TS0012",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6, 57345]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class Tuya_Double_Var05(EnchantedDevice, TuyaSwitch):
    """Tuya 2 gang no neutral light switch (variation 05)."""

    signature = {
        MODEL: "TS0012",
        ENDPOINTS: {
            1: {
                # "profile_id": 260,
                # "device_type": "0x0100",
                # "in_clusters": ["0x0000","0x0003","0x0004","0x0005","0x0006","0xe000","0xe001"],
                # "out_clusters": ["0x000a","0x0019"]
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            2: {
                # "profile_id": 260,
                # "device_type": "0x0100",
                # "in_clusters": ["0x0004","0x0005","0x0006"],
                # "out_clusters": []
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class Tuya_Triple_No_N(EnchantedDevice, TuyaSwitch):
    """Tuya 3 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0013",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class Tuya_Triple_No_N_Plus(EnchantedDevice, TuyaSwitch):
    """Tuya 3 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0,
        # user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        # mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4417, maximum_buffer_size=66,
        # maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66,
        # descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False,
        # *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False,
        # *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        MODEL: "TS0013",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6, 57345]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6, 57345]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class TuyaTripleGang_var05(EnchantedDevice, TuyaSwitch):
    """Tuya 3 gang light switch (variation 05)."""

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0,
        # user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        # mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4417, maximum_buffer_size=66,
        # maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66,
        # descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False,
        # *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False,
        # *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        MODEL: "TS0013",
        ENDPOINTS: {
            # "profile_id": 260, "device_type": "0x0100",
            # "in_clusters": ["0x0000","0x0003","0x0004","0x0005","0x0006","0xe000","0xe001"],
            # "out_clusters": ["0x000a","0x0019"]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # "profile_id": 260, "device_type": "0x0100",
            # "in_clusters": ["0x0004","0x0005","0x0006"],
            # "out_clusters": []
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # "profile_id": 260, "device_type": "0x0100",
            # "in_clusters": ["0x0004","0x0005","0x0006"],
            # "out_clusters": []
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaZBE000Cluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
