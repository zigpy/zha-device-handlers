"""Tuya TS000X Switches.

The 1 to 4 gang relay modules are matched by their endpoint signature (model only, any
manufacturer), so the same devices match as with the former v1 quirks.
"""

from zha.quirks import TUYA_PLUG_ONOFF
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import signature_matches
from zhaquirks.tuya import (
    TuyaZBE000Cluster,
    TuyaZBElectricalMeasurement,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBMeteringCluster,
    TuyaZBOnOffAttributeCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

# Tuya 1 gang switch module with restore power state support.
SWITCH_1G_GPP_SIGNATURE = {
    MODEL: "TS0001",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=266 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
        # output_clusters=[10, 25]>
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
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=1
        # input_clusters=[]
        # output_clusters=[33]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 1 gang switch with metering support.
SWITCH_1G_METERING_SIGNATURE = {
    MODEL: "TS0001",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=266 device_type=256
        # input_clusters=["0x0000","0x0003","0x0004","0x0005","0x0006","0x0702","0x0b04","0xe000","0xe001"]
        # output_clusters=["0x000a","0x0019"]>
        1: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
            INPUT_CLUSTERS: [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                TuyaZBMeteringCluster.cluster_id,
                TuyaZBElectricalMeasurement.cluster_id,
                TuyaZBE000Cluster.cluster_id,
                TuyaZBExternalSwitchTypeCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=1
        # input_clusters=[]
        # output_clusters=["0x0021"]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 2 gang switch module with restore power state support.
SWITCH_2G_GPP_SIGNATURE = {
    MODEL: "TS0002",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
        # output_clusters=[10, 25]>
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
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
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
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=[33]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 2 gang switch with metering support.
SWITCH_2G_METERING_SIGNATURE = {
    MODEL: "TS0002",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # input_clusters=["0x0000","0x0003","0x0004","0x0005","0x0006","0x0702","0x0b04","0xe000","0xe001"]
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
                TuyaZBMeteringCluster.cluster_id,
                TuyaZBElectricalMeasurement.cluster_id,
                TuyaZBE000Cluster.cluster_id,
                TuyaZBExternalSwitchTypeCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
        # input_clusters=["0x0004", "0x0005", "0x0006"]
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
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=["0x0021"]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 2 gang (variation 03).
SWITCH_2G_VAR03_SIGNATURE = {
    MODEL: "TS0002",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
        # output_clusters=[10, 25]>
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
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
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
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=[33]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 3 gang switch module with restore power state support.
SWITCH_3G_GPP_SIGNATURE = {
    MODEL: "TS0003",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
        # output_clusters=[10, 25]>
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
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
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
        # <SimpleDescriptor endpoint=3 profile=260 device_type=256
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
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=[33]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 3 gang switch with metering support.
SWITCH_3G_METERING_SIGNATURE = {
    MODEL: "TS0003",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # input_clusters=["0x0000","0x0003","0x0004","0x0005","0x0006","0x0702","0x0b04","0xe000","0xe001"]
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
                TuyaZBMeteringCluster.cluster_id,
                TuyaZBElectricalMeasurement.cluster_id,
                TuyaZBE000Cluster.cluster_id,
                TuyaZBExternalSwitchTypeCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
        # input_clusters=["0x0004", "0x0005", "0x0006"]
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
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
        # input_clusters=["0x0004", "0x0005", "0x0006"]
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
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=["0x0021"]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 3 gang switch module.
SWITCH_3G_GPP_VAR2_SIGNATURE = {
    MODEL: "TS0003",
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
                TuyaZBE000Cluster.cluster_id,
                TuyaZBExternalSwitchTypeCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [
                Time.cluster_id,
                Ota.cluster_id,
            ],
        },
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
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 4 gang switch module with restore power state support.
SWITCH_4G_GPP_SIGNATURE = {
    MODEL: "TS0004",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 57344, 57345]
        # output_clusters=[10, 25]>
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
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
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
        # <SimpleDescriptor endpoint=3 profile=260 device_type=256
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
        # <SimpleDescriptor endpoint=3 profile=260 device_type=256
        # device_version=1
        # input_clusters=[4, 5, 6, 57345]
        # output_clusters=[]>
        4: {
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
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=[33]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 4 gang switch with metering support.
SWITCH_4G_METERING_SIGNATURE = {
    MODEL: "TS0004",
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # input_clusters=["0x0000","0x0003","0x0004","0x0005","0x0006","0x0702","0x0b04","0xe000","0xe001"]
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
                TuyaZBMeteringCluster.cluster_id,
                TuyaZBElectricalMeasurement.cluster_id,
                TuyaZBE000Cluster.cluster_id,
                TuyaZBExternalSwitchTypeCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
        # input_clusters=["0x0004", "0x0005", "0x0006"]
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
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
        # input_clusters=["0x0004", "0x0005", "0x0006"]
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
        # <SimpleDescriptor endpoint=2 profile=260 device_type=256
        # input_clusters=["0x0004", "0x0005", "0x0006"]
        # output_clusters=[]>
        4: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
            INPUT_CLUSTERS: [
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
            ],
            OUTPUT_CLUSTERS: [],
        },
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=["0x0021"]>
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}

# Tuya 4 gang switch module.
SWITCH_4G_GPP_VAR2_SIGNATURE = {
    MODEL: "TS0004",
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
                TuyaZBE000Cluster.cluster_id,
                TuyaZBExternalSwitchTypeCluster.cluster_id,
            ],
            OUTPUT_CLUSTERS: [
                Time.cluster_id,
                Ota.cluster_id,
            ],
        },
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
        4: {
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
        242: {
            PROFILE_ID: zgp.PROFILE_ID,
            DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
            INPUT_CLUSTERS: [],
            OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
        },
    },
}


def _add_quirk(signature: dict) -> None:
    """Add the quirk for the signature of a TS000X switch module."""
    (
        TuyaQuirkBuilder(None, signature[MODEL])
        .filter(signature_matches(signature))
        .replace_cluster_occurrences(
            TuyaZBOnOffAttributeCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(TuyaZBE000Cluster, replace_client_instances=False)
        .replace_cluster_occurrences(
            TuyaZBExternalSwitchTypeCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(
            TuyaZBMeteringCluster, replace_client_instances=False
        )
        .replace_cluster_occurrences(
            TuyaZBElectricalMeasurement, replace_client_instances=False
        )
        .exposes_feature(TUYA_PLUG_ONOFF)
        .tuya_enchantment()
        .add_to_registry()
    )


_add_quirk(SWITCH_1G_GPP_SIGNATURE)
_add_quirk(SWITCH_1G_METERING_SIGNATURE)
_add_quirk(SWITCH_2G_GPP_SIGNATURE)
_add_quirk(SWITCH_2G_METERING_SIGNATURE)
_add_quirk(SWITCH_2G_VAR03_SIGNATURE)
_add_quirk(SWITCH_3G_GPP_SIGNATURE)
_add_quirk(SWITCH_3G_METERING_SIGNATURE)
_add_quirk(SWITCH_3G_GPP_VAR2_SIGNATURE)
_add_quirk(SWITCH_4G_GPP_SIGNATURE)
_add_quirk(SWITCH_4G_METERING_SIGNATURE)
_add_quirk(SWITCH_4G_GPP_VAR2_SIGNATURE)
