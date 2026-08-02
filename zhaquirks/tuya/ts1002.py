"""Tuya TS1002 4-button scene switch."""

from __future__ import annotations

from typing import Any

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STOP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)
from zhaquirks.legacy import CustomDevice
from zhaquirks.tuya import (
    TuyaNoBindPowerConfigurationCluster,
    TuyaSmartRemoteOnOffCluster,
    TuyaZBExternalSwitchTypeCluster,
)

PRESS_TYPE = {
    0x00: SHORT_PRESS,
    0x01: DOUBLE_PRESS,
    0x02: LONG_PRESS,
}

# Zigbee2MQTT TS1002: different buttons may use different clusters.
BUTTON_FROM_STEP_MODE = {0: 3, 1: 4}
BUTTON_FROM_SCENE = {1: 1, 2: 2, 3: 3, 4: 4, 5: 1, 6: 2, 7: 3, 8: 4}


class TuyaTS1002NoBindMixin:
    """Skip Zigbee bind on remote output clusters (unsupported, blocks onboarding)."""

    async def bind(self):
        """Prevent bind."""
        return (foundation.Status.SUCCESS,)

    async def _configure_reporting(self, *args, **kwargs):
        """Prevent remote configure reporting."""
        return (foundation.ConfigureReportingResponse.deserialize(b"\x00")[0],)


class TuyaTS1002SceneCluster(TuyaTS1002NoBindMixin, CustomCluster, Scenes):
    """Map recall_scene to button endpoints."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle scene cluster commands and map them to button events."""
        if hdr.command_id in (0x00, 0x05) and args:
            scene_id = int(args[0])
            button_id = BUTTON_FROM_SCENE.get(scene_id)
            if button_id:
                self._dispatch_scene_button(button_id)
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def _dispatch_scene_button(self, button_id: int) -> None:
        device = self.endpoint.device
        target = device.endpoints.get(button_id)
        if target is None:
            return
        for cluster in target.in_clusters.values():
            if isinstance(cluster, TuyaSmartRemoteOnOffCluster):
                cluster.listener_event(ZHA_SEND_EVENT, SHORT_PRESS, [])
                return


class TuyaTS1002LevelCluster(TuyaTS1002NoBindMixin, CustomCluster, LevelControl):
    """Map step commands to buttons 3-4."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle level cluster commands and map them to button events."""
        if hdr.command_id == 0x02 and args:
            step_mode = int(getattr(args[0], "step_mode", args[0]))
            button_id = BUTTON_FROM_STEP_MODE.get(step_mode)
            if button_id:
                self._dispatch_level_button(button_id)
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def _dispatch_level_button(self, button_id: int) -> None:
        device = self.endpoint.device
        target = device.endpoints.get(button_id)
        if target is None:
            return
        for cluster in target.in_clusters.values():
            if isinstance(cluster, TuyaSmartRemoteOnOffCluster):
                cluster.listener_event(ZHA_SEND_EVENT, SHORT_PRESS, [])
                return


class TuyaTS1002ColorCluster(TuyaTS1002NoBindMixin, CustomCluster, Color):
    """Map step_color_temp to buttons 1-2."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle color cluster commands and map them to button events."""
        if hdr.command_id == 0x4C and args:
            step_mode = int(getattr(args[0], "step_mode", args[0]))
            button_id = 1 if step_mode in (1, 3) else 2 if step_mode in (0, 2) else None
            if button_id:
                self._dispatch_color_button(button_id)
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def _dispatch_color_button(self, button_id: int) -> None:
        device = self.endpoint.device
        target = device.endpoints.get(button_id)
        if target is None:
            return
        for cluster in target.in_clusters.values():
            if isinstance(cluster, TuyaSmartRemoteOnOffCluster):
                cluster.listener_event(ZHA_SEND_EVENT, SHORT_PRESS, [])
                return


class TuyaTS1002SceneOnOffCluster(TuyaTS1002NoBindMixin, TuyaSmartRemoteOnOffCluster):
    """Route TS1002 scene button presses to the matching endpoint."""

    class ServerCommandDefs(TuyaSmartRemoteOnOffCluster.ServerCommandDefs):
        """TS1002 sends press_type + 0x00 + button_id in 0xFD payload."""

        press_type = foundation.ZCLCommandDef(
            id=0xFD,
            schema={
                "press_type": t.uint8_t,
                "zero": t.uint8_t,
                "button": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )

    def _parse_button_press(self, args: list[Any] | Any) -> tuple[int, int | None]:
        """Extract press type and button id from a 0xFD command."""
        press_type = 0
        button_id: int | None = None

        if not args:
            return press_type, button_id

        if isinstance(args, (list, tuple)):
            first = args[0] if args else None
        else:
            first = args

        if first is None:
            return press_type, button_id

        if hasattr(first, "press_type"):
            press_type = int(first.press_type)
            if hasattr(first, "button"):
                button_id = int(first.button)
        elif isinstance(first, int):
            press_type = first
            if isinstance(args, (list, tuple)) and len(args) >= 3:
                button_id = int(args[2])

        return press_type, button_id

    def _dispatch_button_event(self, endpoint_id: int, press_type: int) -> None:
        """Send a button event on the target endpoint."""
        event = PRESS_TYPE.get(press_type, SHORT_PRESS)
        device = self.endpoint.device

        if endpoint_id == self.endpoint.endpoint_id:
            self.listener_event(ZHA_SEND_EVENT, event, [])
            return

        target = device.endpoints.get(endpoint_id)

        if target is not None:
            clusters = list(target.in_clusters.values()) + list(
                target.out_clusters.values()
            )
            for cluster in clusters:
                if (
                    isinstance(cluster, TuyaSmartRemoteOnOffCluster)
                    and cluster is not self
                ):
                    cluster.listener_event(ZHA_SEND_EVENT, event, [])
                    return

        self.listener_event(ZHA_SEND_EVENT, event, [])

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle Tuya scene button commands on endpoint 1."""
        if hdr.command_id != 0xFD:
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        if hdr.tsn == self.last_tsn:
            return
        self.last_tsn = hdr.tsn

        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        press_type, button_id = self._parse_button_press(args)
        if button_id is None:
            button_id = 1

        if 1 <= button_id <= 4:
            self._dispatch_button_event(button_id, press_type)
            return

        event = PRESS_TYPE.get(press_type, SHORT_PRESS)
        self.listener_event(ZHA_SEND_EVENT, event, [])


class TuyaSmartRemote1002(CustomDevice):
    """Tuya TS1002 4-button scene switch.

    Commercial example: Arlight SMART-ZB-801-22-1G-4SC-MULTI-IN (048042).
    https://arlight.ru/catalog/product/048042/
    """

    signature = {
        MODELS_INFO: [("_TZ3000_te34fjg4", "TS1002")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=261
            # device_version=0
            # input_clusters=[0, 1, 3, 4, 4096, 57345]
            # output_clusters=[3, 4, 5, 6, 8, 10, 25, 768, 4096]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaNoBindPowerConfigurationCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    TuyaTS1002SceneCluster,
                    TuyaTS1002SceneOnOffCluster,
                    TuyaTS1002LevelCluster,
                    Time.cluster_id,
                    Ota.cluster_id,
                    TuyaTS1002ColorCluster,
                    LightLink.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [TuyaSmartRemoteOnOffCluster],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [TuyaSmartRemoteOnOffCluster],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [TuyaSmartRemoteOnOffCluster],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: SHORT_PRESS},
        (DOUBLE_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: DOUBLE_PRESS},
        (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: LONG_PRESS},
        (SHORT_PRESS, BUTTON_3): {ENDPOINT_ID: 3, COMMAND: SHORT_PRESS},
        (DOUBLE_PRESS, BUTTON_3): {ENDPOINT_ID: 3, COMMAND: DOUBLE_PRESS},
        (LONG_PRESS, BUTTON_3): {ENDPOINT_ID: 3, COMMAND: LONG_PRESS},
        (SHORT_PRESS, BUTTON_4): {ENDPOINT_ID: 4, COMMAND: SHORT_PRESS},
        (DOUBLE_PRESS, BUTTON_4): {ENDPOINT_ID: 4, COMMAND: DOUBLE_PRESS},
        (LONG_PRESS, BUTTON_4): {ENDPOINT_ID: 4, COMMAND: LONG_PRESS},
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        (LONG_RELEASE, DIM_DOWN): {
            COMMAND: COMMAND_STOP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
        },
    }
