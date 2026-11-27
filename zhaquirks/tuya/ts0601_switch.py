"""Tuya DP based switches."""

from zha.quirks import TUYA_PLUG_MANUFACTURER
import zigpy.device
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaSwitch
from zhaquirks.tuya.mcu import (
    MoesSwitchManufCluster,
    TuyaOnOff,
    TuyaOnOffManufCluster,
    TuyaOnOffNM,
)


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


GREEN_POWER_ENDPOINT_ID = 242


def _reports_one_endpoint(device: zigpy.device.Device) -> bool:
    """Match a device that reports all its gangs on one Tuya MCU endpoint.

    The multi-gang switches below report one endpoint (plus a Green Power proxy
    endpoint on some models), whose Tuya MCU cluster carries the DPs of all
    gangs. Units that report an endpoint per gang, or an OnOff server cluster of
    their own, are left alone.
    """
    if set(device.endpoints) - {0, GREEN_POWER_ENDPOINT_ID} != {1}:
        return False
    in_clusters = device.endpoints[1].in_clusters
    return (
        TuyaOnOffManufCluster.cluster_id in in_clusters
        and OnOff.cluster_id not in in_clusters
    )


def _add_gangs(
    builder: QuirkBuilder,
    gangs: int,
    onoff_cluster: type[TuyaOnOff],
    device_type: int = zha.DeviceType.ON_OFF_LIGHT,
) -> QuirkBuilder:
    """Give each gang its own endpoint with a Tuya MCU OnOff cluster.

    The DPs are mapped to the gang endpoints by the manufacturer cluster that
    replaces the Tuya MCU cluster on endpoint 1. Each gang is a child device, with
    the id and name ZHA's automatic split gives the channels of the multi-gang models
    on its allowlist, which can't match `TS0601` by model.
    """
    builder = builder.filter(_reports_one_endpoint).replaces_endpoint(
        1, device_type=device_type
    )
    for endpoint_id in range(2, gangs + 1):
        builder = builder.adds_endpoint(endpoint_id, device_type=device_type)
    for endpoint_id in range(1, gangs + 1):
        builder = builder.adds(onoff_cluster, endpoint_id=endpoint_id).child_device(
            str(endpoint_id),
            endpoint_id=endpoint_id,
            translation_key="channel",
            translation_placeholders={"index": str(endpoint_id)},
            fallback_name=f"Channel {endpoint_id}",
        )
    # The settings of the Tuya MCU cluster on endpoint 1 (power-on state, backlight)
    # are the whole device's, so they stay on the main device
    return builder.change_entity_metadata(
        endpoint_id=1,
        cluster_id=TuyaOnOffManufCluster.cluster_id,
        new_child_device_id=None,
    )


# 2 gangs
(
    _add_gangs(
        QuirkBuilder("_TZE200_g1ib5ldv", "TS0601")
        .applies_to("_TZE200_wunufsil", "TS0601")
        .applies_to("_TZE200_nkjintbl", "TS0601")
        .applies_to("_TZE204_wvovwe9h", "TS0601"),
        gangs=2,
        onoff_cluster=TuyaOnOff,
    )
    .replaces(MoesSwitchManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 2 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE200_7deq70b8", "TS0601")
        .applies_to("_TZE200_nh9m9emk", "TS0601")  # reported in #1634
        .applies_to("_TZE204_nh9m9emk", "TS0601"),  # reported in #4100
        gangs=2,
        onoff_cluster=TuyaOnOffNM,
    )
    .replaces(MoesSwitchManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 2 gangs, reported as an on/off light without output clusters
(
    _add_gangs(
        QuirkBuilder("_TZE200_wvovwe9h", "TS0601"),  # reported in #4077
        gangs=2,
        onoff_cluster=TuyaOnOff,
    )
    .replaces(MoesSwitchManufCluster)
    .add_to_registry()
)

# 3 gangs
(
    _add_gangs(
        QuirkBuilder("_TZE200_tz32mtza", "TS0601").applies_to(
            "_TZE200_vhy3iakz", "TS0601"
        ),
        gangs=3,
        onoff_cluster=TuyaOnOff,
    )
    .replaces(MoesSwitchManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 3 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE200_2hf7x9n3", "TS0601")  # reported in #1597
        .applies_to("_TZE200_go3tvswy", "TS0601")  # reported in #1634
        .applies_to("_TZE204_2imwyigp", "TS0601"),
        gangs=3,
        onoff_cluster=TuyaOnOffNM,
    )
    .replaces(MoesSwitchManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 3 gangs, with the Time cluster as an input cluster
(
    _add_gangs(
        QuirkBuilder("_TZE200_kyfqmmyl", "TS0601"),  # reported in #2469
        gangs=3,
        onoff_cluster=TuyaOnOff,
    )
    .replaces(MoesSwitchManufCluster)
    .add_to_registry()
)

# 4 gangs
(
    _add_gangs(
        QuirkBuilder("_TZE200_aqnazj70", "TS0601")
        .applies_to("_TZE200_1ozguk6x", "TS0601")
        .applies_to("_TZE200_k6jhsr0q", "TS0601"),
        gangs=4,
        onoff_cluster=TuyaOnOff,
    )
    .replaces(MoesSwitchManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 4 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE200_1n2kyphz", "TS0601")
        .applies_to("_TZE200_mexisfik", "TS0601")  # reported in #1634
        .applies_to("_TZE204_58of2pfn", "TS0601"),  # 4-channel relay
        gangs=4,
        onoff_cluster=TuyaOnOffNM,
    )
    .replaces(MoesSwitchManufCluster)
    .add_to_registry()
)

# 5 gangs
(
    _add_gangs(
        QuirkBuilder("_TZE200_leaqthqq", "TS0601"),
        gangs=5,
        onoff_cluster=TuyaOnOffNM,
    )
    .replaces(TuyaOnOffManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 5 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE200_jwsjbxjs", "TS0601"),  # reported in #4219
        gangs=5,
        onoff_cluster=TuyaOnOffNM,
    )
    .replaces(MoesSwitchManufCluster)
    .add_to_registry()
)

# 6 gangs, with or without a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE200_9mahtqtg", "TS0601")
        .applies_to("_TZE200_wnp4d4va", "TS0601")
        .applies_to("_TZE200_emxxanvi", "TS0601"),
        gangs=6,
        onoff_cluster=TuyaOnOffNM,
    )
    .replaces(TuyaOnOffManufCluster)
    .exposes_feature(TUYA_PLUG_MANUFACTURER)
    .add_to_registry()
)

# 8 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE200_wktrysab", "TS0601").applies_to(
            "_TZE204_wktrysab", "TS0601"
        ),
        gangs=8,
        onoff_cluster=TuyaOnOffNM,
        device_type=zha.DeviceType.ON_OFF_SWITCH,
    )
    .replaces(TuyaOnOffManufCluster)
    .add_to_registry()
)

# 12 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE204_dqolcpcp", "TS0601"),
        gangs=12,
        onoff_cluster=TuyaOnOffNM,
        device_type=zha.DeviceType.ON_OFF_SWITCH,
    )
    .replaces(TuyaOnOffManufCluster)
    .add_to_registry()
)

# 16 gangs, with a Green Power proxy endpoint
(
    _add_gangs(
        QuirkBuilder("_TZE204_vmcgja59", "TS0601"),
        gangs=16,
        onoff_cluster=TuyaOnOffNM,
        device_type=zha.DeviceType.ON_OFF_SWITCH,
    )
    .replaces(TuyaOnOffManufCluster)
    .add_to_registry()
)
