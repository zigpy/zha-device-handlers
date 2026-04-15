"""Tuya TS0601 screen switch quirks."""

from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaData, TuyaSwitch
from zhaquirks.tuya.mcu import DPToAttributeMapping, MoesSwitchManufCluster, TuyaOnOffNM


class RawBytes(TuyaData):
    """Raw bytes helper for Tuya string payloads."""

    def __init__(self, value: bytes):
        """Init raw byte payload."""
        self.raw = value

    def serialize(self) -> bytes:
        """Serialize raw bytes with Tuya string header."""
        length = len(self.raw)
        return b"\x00" + length.to_bytes(2, "big") + self.raw

    def __repr__(self) -> str:
        """Represent raw bytes."""
        return f"<RawBytes {self.raw!r}>"


def _name_dp_mapping(attribute_name: str) -> DPToAttributeMapping:
    """Create a DP mapping for screen name updates."""
    return DPToAttributeMapping(
        ep_attribute="tuya_mcu",
        attribute_name=attribute_name,
        converter=lambda value: value.decode("utf-8"),
        dp_converter=lambda value: RawBytes(value.encode("utf-8")),
        endpoint_id=1,
    )


class ScreenSwitchManufCluster1G(MoesSwitchManufCluster):
    """Custom Moes cluster with single-gang screen name support."""

    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update(
        {
            105: _name_dp_mapping("name_update_1"),
        }
    )
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class ScreenSwitchManufCluster2G(MoesSwitchManufCluster):
    """Custom Moes cluster with dual-gang screen name support."""

    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update(
        {
            105: _name_dp_mapping("name_update_1"),
            106: _name_dp_mapping("name_update_2"),
        }
    )
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class ScreenSwitchManufCluster3G(MoesSwitchManufCluster):
    """Custom Moes cluster with triple-gang screen name support."""

    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update(
        {
            105: _name_dp_mapping("name_update_1"),
            106: _name_dp_mapping("name_update_2"),
            107: _name_dp_mapping("name_update_3"),
        }
    )
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


class ScreenSwitchManufCluster4G(MoesSwitchManufCluster):
    """Custom Moes cluster with quadruple-gang screen name support."""

    dp_to_attribute = MoesSwitchManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update(
        {
            105: _name_dp_mapping("name_update_1"),
            106: _name_dp_mapping("name_update_2"),
            107: _name_dp_mapping("name_update_3"),
            108: _name_dp_mapping("name_update_4"),
        }
    )
    data_point_handlers = MoesSwitchManufCluster.data_point_handlers.copy()


def _signature(
    models_info: list[tuple[str, str]], input_clusters: list[int] | None = None
):
    """Build the base signature for screen switches."""
    if input_clusters is None:
        input_clusters = [
            Basic.cluster_id,
            Groups.cluster_id,
            Scenes.cluster_id,
            MoesSwitchManufCluster.cluster_id,
            0xED00,
        ]

    return {
        MODELS_INFO: models_info,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: input_clusters,
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


def _replacement(manufacturer_cluster: type[MoesSwitchManufCluster], channels: int):
    """Build the replacement definition for screen switches."""
    endpoints = {
        1: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
            INPUT_CLUSTERS: [
                Basic.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                manufacturer_cluster,
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

    for endpoint_id in range(2, channels + 1):
        endpoints[endpoint_id] = {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
            INPUT_CLUSTERS: [TuyaOnOffNM],
            OUTPUT_CLUSTERS: [],
        }

    return {ENDPOINTS: endpoints}


def _tze28c1000000_signature(models_info: list[tuple[str, str]]):
    """Signature variant for TZE28C1000000 devices."""
    return _signature(
        models_info,
        [
            Basic.cluster_id,
            0xE000,
            0xEB00,
            0xED00,
            Groups.cluster_id,
            Scenes.cluster_id,
            Identify.cluster_id,
            0xEF00,
        ],
    )


def _tze204_ef00_signature(models_info: list[tuple[str, str]]):
    """Signature variant for EF00-only TZE204 devices."""
    return _signature(
        models_info,
        [
            Groups.cluster_id,
            Scenes.cluster_id,
            0xEF00,
            Basic.cluster_id,
        ],
    )


class TuyaSingleScreenSwitchGP(TuyaSwitch):
    """Tuya single channel screen switch."""

    signature = _signature(
        [
            ("_TZE284_lnyz4a6v", "TS0601"),
            ("_TZE284_1tnysxwl", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster1G, 1)


class TuyaDualScreenSwitchGP(TuyaSwitch):
    """Tuya dual channel screen switch."""

    signature = _signature(
        [
            ("_TZE284_dmckrsxg", "TS0601"),
            ("_TZE284_a2teqi5u", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster2G, 2)


class TuyaDualScreenSwitchTZE28C1000000(TuyaSwitch):
    """Tuya dual channel screen switch with TZE28C1000000 signature."""

    signature = _tze28c1000000_signature(
        [
            ("_TZE28C1000000_a2teqi5u", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster2G, 2)


class TuyaDualScreenSwitchTZE204EF00(TuyaSwitch):
    """Tuya dual channel screen switch with EF00-only TZE204 signature."""

    signature = _tze204_ef00_signature(
        [
            ("_TZE204_3ctwoaip", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster2G, 2)


class TuyaTripleScreenSwitchGP(TuyaSwitch):
    """Tuya triple channel screen switch."""

    signature = _signature(
        [
            ("_TZE284_e4pf6l87", "TS0601"),
            ("_TZE284_xvywzhmi", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster3G, 3)


class TuyaQuadrupleScreenSwitchGP(TuyaSwitch):
    """Tuya quadruple channel screen switch."""

    signature = _signature(
        [
            ("_TZE284_y4jqpry8", "TS0601"),
            ("_TZE284_xibaabmu", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster4G, 4)


class TuyaQuadrupleScreenSwitchTZE28C1000000(TuyaSwitch):
    """Tuya quadruple channel screen switch with TZE28C1000000 signature."""

    signature = _tze28c1000000_signature(
        [
            ("_TZE28C1000000_xibaabmu", "TS0601"),
        ]
    )
    replacement = _replacement(ScreenSwitchManufCluster4G, 4)
