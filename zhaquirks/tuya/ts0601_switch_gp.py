import logging
from zigpy.profiles import zha, zgp
from zigpy.zcl.clusters.general import Basic, Groups, Scenes, Time, Ota, GreenPowerProxy
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaSwitch,
    TuyaData,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaOnOffNM,
    MoesSwitchManufCluster,
)
from zigpy.types import LVBytes, CharacterString


class RawBytes(TuyaData):
    def __init__(self, value: bytes):
        self.raw = value

    def serialize(self) -> bytes:
        length = len(self.raw)
        return b"\x00" + length.to_bytes(2, "big") + self.raw

    def __repr__(self):
        return f"<RawBytes {self.raw!r}>"


_LOGGER = logging.getLogger(__name__)


class CustomMoesSwitchManufCluster_1G(MoesSwitchManufCluster):
    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update({
        105: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_1",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
    })
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class CustomMoesSwitchManufCluster_2G(MoesSwitchManufCluster):
    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update({
        105: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_1",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        106: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_2",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
    })
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class CustomMoesSwitchManufCluster_3G(MoesSwitchManufCluster):
    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update({
        105: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_1",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        106: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_2",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        107: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_3",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
    })
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class CustomMoesSwitchManufCluster_4G(MoesSwitchManufCluster):
    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update({
        105: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_1",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        106: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_2",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        107: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_3",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        108: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_4",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
    })
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class TuyaSingleSwitch_GP(TuyaSwitch):
    signature = {
        MODELS_INFO: [
            ("_TZE284_lnyz4a6v", "TS0601"),
            ("_TZE284_1tnysxwl", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster.cluster_id,
                    0xED00,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CustomMoesSwitchManufCluster_1G,
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


class TuyaDualSwitch_GP(TuyaSwitch):
    signature = {
        MODELS_INFO: [
            ("_TZE284_dmckrsxg", "TS0601"),
            ("_TZE284_a2teqi5u", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster.cluster_id,
                    0xED00,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CustomMoesSwitchManufCluster_2G,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOffNM],
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


class TuyaTripleSwitch_GP(TuyaSwitch):
    signature = {
        MODELS_INFO: [
            ("_TZE284_e4pf6l87", "TS0601"),
            ("_TZE284_xvywzhmi", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster.cluster_id,
                    0xED00,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CustomMoesSwitchManufCluster_3G,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOffNM],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOffNM],
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


class TuyaQuadrupleSwitch_GP(TuyaSwitch):
    signature = {
        MODELS_INFO: [
            ("_TZE284_y4jqpry8", "TS0601"),
            ("_TZE284_xibaabmu", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesSwitchManufCluster.cluster_id,
                    0xED00,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CustomMoesSwitchManufCluster_4G,
                    TuyaOnOffNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOffNM],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOffNM],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOffNM],
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
