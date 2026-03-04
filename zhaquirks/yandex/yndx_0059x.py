"""Support for YNDX-0059x devices: curtain motor."""

from __future__ import annotations

from typing import Final

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.closures import (
    ConfigStatus,
    WindowCovering,
    WindowCoveringMode,
    WindowCoveringType,
)
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.foundation import Direction, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.yandex import (
    YANDEX,
    YANDEX_ATTRIBUTE_MAX_POSITION,
    YANDEX_ATTRIBUTE_MIN_POSITION,
    YANDEX_ATTRIBUTE_UNK_F000,
    YANDEX_ATTRIBUTE_UNK_FFFD,
    YANDEX_ATTRIBUTE_VELOCITY_LIFT,
    YANDEX_MANUFACTURER_CODE_2,
)


class YandexWindowCovering(CustomCluster, WindowCovering):
    """Yandex-flavor window covering cluster."""

    manufacturer_id_override = YANDEX_MANUFACTURER_CODE_2

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Attribute definitions."""

        window_covering_type: Final = ZCLAttributeDef(
            id=0x0000, type=WindowCoveringType, access="r", mandatory=True
        )
        config_status: Final = ZCLAttributeDef(
            id=0x0007, type=ConfigStatus, access="r", mandatory=True
        )
        current_position_lift_percentage: Final = ZCLAttributeDef(
            id=0x0008, type=t.uint8_t, access="rps"
        )
        velocity_lift: Final = YANDEX_ATTRIBUTE_VELOCITY_LIFT
        window_covering_mode: Final = ZCLAttributeDef(
            id=0x0017, type=WindowCoveringMode, access="rw", mandatory=True
        )
        min_position: Final = YANDEX_ATTRIBUTE_MIN_POSITION
        max_position: Final = YANDEX_ATTRIBUTE_MAX_POSITION
        unknown_f000: Final = YANDEX_ATTRIBUTE_UNK_F000
        unknown_fffd: Final = YANDEX_ATTRIBUTE_UNK_FFFD

    class ServerCommandDefs(WindowCovering.ServerCommandDefs):
        """Server command definitions."""

        down_close: Final = ZCLCommandDef(
            id=0x00, schema={}, direction=Direction.Client_to_Server
        )
        up_open: Final = ZCLCommandDef(
            id=0x01, schema={}, direction=Direction.Client_to_Server
        )
        stop: Final = ZCLCommandDef(
            id=0x02, schema={}, direction=Direction.Client_to_Server
        )
        go_to_lift_percentage: Final = ZCLCommandDef(
            id=0x05,
            schema={"percentage_lift_value": t.uint8_t},
            direction=Direction.Client_to_Server,
        )


class YandexCurtainMotor(CustomDevice):
    """Yandex curtain motor."""

    signature = {
        MODELS_INFO: [(YANDEX, "YNDX-00591"), (YANDEX, "YNDX-00592")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=514
            # device_version=0
            # input_clusters=[0, 3, 4, 5, 258, 2821]
            # output_clusters=[3, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
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

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    YandexWindowCovering,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
