"""Xiaomi mija button device."""
import asyncio
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)

from zhaquirks import CustomCluster
from zhaquirks.const import (
    ARGS,
    BUTTON,
    CLICK_TYPE,
    COMMAND,
    COMMAND_CLICK,
    COMMAND_DOUBLE,
    COMMAND_FURIOUS,
    COMMAND_HOLD,
    COMMAND_QUAD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    COMMAND_TRIPLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
    TRIPLE_PRESS,
    UNKNOWN,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)

XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

CLICK_TYPE_MAP = {
    2: COMMAND_DOUBLE,
    3: COMMAND_TRIPLE,
    4: COMMAND_QUAD,
    128: COMMAND_FURIOUS,
}


class MijaButton(XiaomiQuickInitDevice):
    """Mija button device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 10
        super().__init__(*args, **kwargs)

    class MijaOnOff(CustomCluster, OnOff):
        """Mija on off cluster."""

        cluster_id = OnOff.cluster_id
        hold_duration: float = 1.0

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            self._loop = asyncio.get_running_loop()
            self._timer_handle = None
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            click_type = False

            # Handle Mija OnOff
            if attrid == 0:
                value = not value

                if value:
                    if self._timer_handle:
                        self._timer_handle.cancel()
                    self._timer_handle = self._loop.call_later(
                        self.hold_duration, self._hold_timeout
                    )
                else:
                    if self._timer_handle:
                        self._timer_handle.cancel()
                        self._timer_handle = None
                        click_type = COMMAND_SINGLE
                    else:
                        self.listener_event(ZHA_SEND_EVENT, COMMAND_RELEASE, [])

            # Handle Multi Clicks
            elif attrid == 32768:
                click_type = CLICK_TYPE_MAP.get(value, UNKNOWN)

            if click_type:
                self.listener_event(
                    ZHA_SEND_EVENT, COMMAND_CLICK, {CLICK_TYPE: click_type}
                )

            super()._update_attribute(attrid, value)

        def _hold_timeout(self):
            """Handle hold timeout."""

            self._timer_handle = None
            self.listener_event(ZHA_SEND_EVENT, COMMAND_HOLD, [])

    signature = {
        # Endpoints:
        #   1: profile=0x104, device_type=DeviceType.DIMMER_SWITCH
        #     Input Clusters:
        #       Basic (0)
        #       Identify (3)
        #       Ota (25)
        #       Manufacturer Specific (65535)
        #     Output Clusters:
        #       Basic (0)
        #       Identify (3)
        #       Groups (4)
        #       Scenes (5)
        #       On/Off (6)
        #       Level control (8)
        #       Ota (25)
        MODELS_INFO: [(LUMI, "lumi.sensor_switch")],
        NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    BasicCluster,
                    XiaomiPowerConfiguration,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    MijaOnOff,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, SHORT_PRESS): {
            COMMAND: COMMAND_CLICK,
            ARGS: {CLICK_TYPE: COMMAND_SINGLE},
        },
        (LONG_PRESS, BUTTON): {COMMAND: COMMAND_HOLD},
        (LONG_RELEASE, BUTTON): {COMMAND: COMMAND_RELEASE},
        (DOUBLE_PRESS, DOUBLE_PRESS): {
            COMMAND: COMMAND_CLICK,
            ARGS: {CLICK_TYPE: COMMAND_DOUBLE},
        },
        (TRIPLE_PRESS, TRIPLE_PRESS): {
            COMMAND: COMMAND_CLICK,
            ARGS: {CLICK_TYPE: COMMAND_TRIPLE},
        },
        (QUADRUPLE_PRESS, QUADRUPLE_PRESS): {
            COMMAND: COMMAND_CLICK,
            ARGS: {CLICK_TYPE: COMMAND_QUAD},
        },
        (QUINTUPLE_PRESS, QUINTUPLE_PRESS): {
            COMMAND: COMMAND_CLICK,
            ARGS: {CLICK_TYPE: COMMAND_FURIOUS},
        },
    }
