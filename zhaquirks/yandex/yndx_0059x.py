"""Support for YNDX-0059x devices: curtain motor."""

from __future__ import annotations

from typing import Final

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import BaseAttributeDefs, BaseCommandDefs
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
from zhaquirks.yandex import YANDEX


class YandexWindowCovering(WindowCovering):
    """Yandex-specific window covering cluster implementation."""

    cluster_id: Final[t.uint16_t] = 0x0102
    name: Final = "Window Covering"
    ep_attribute: Final = "window_covering"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Window Covering Information
        window_covering_type: Final = ZCLAttributeDef(
            id=0x0000, type=WindowCoveringType, access="r", mandatory=True
        )
        config_status: Final = ZCLAttributeDef(
            id=0x0007, type=ConfigStatus, access="r", mandatory=True
        )
        # All subsequent attributes are mandatory if their control types are enabled
        current_position_lift_percentage: Final = ZCLAttributeDef(
            id=0x0008, type=t.uint8_t, access="rps"
        )
        # Window Covering Settings
        installed_open_limit_lift: Final = ZCLAttributeDef(
            id=0x0010, type=t.uint16_t, access="r"
        )
        installed_closed_limit_lift: Final = ZCLAttributeDef(
            id=0x0011, type=t.uint16_t, access="r"
        )
        velocity_lift: Final = ZCLAttributeDef(id=0x0014, type=t.uint16_t, access="rw")
        window_covering_mode: Final = ZCLAttributeDef(
            id=0x0017, type=WindowCoveringMode, access="rw", mandatory=True
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

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
        MODELS_INFO: [(YANDEX, "YNDX-00591")],
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
                    0x0B05,
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
