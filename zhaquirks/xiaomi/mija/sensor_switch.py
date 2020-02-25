"""Xiaomi mija button device."""
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

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ... import CustomCluster
from ...const import (
    ARGS,
    CLICK_TYPE,
    COMMAND,
    COMMAND_CLICK,
    COMMAND_DOUBLE,
    COMMAND_FURIOUS,
    COMMAND_QUAD,
    COMMAND_SINGLE,
    COMMAND_TRIPLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
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

XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

CLICK_TYPE_MAP = {
    2: COMMAND_DOUBLE,
    3: COMMAND_TRIPLE,
    4: COMMAND_QUAD,
    128: COMMAND_FURIOUS,
}


class MijaButton(XiaomiCustomDevice):
    """Mija button device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 10
        super().__init__(*args, **kwargs)

    class MijaOnOff(CustomCluster, OnOff):
        """Mija on off cluster."""

        cluster_id = OnOff.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            click_type = False

            # Handle Mija OnOff
            if attrid == 0:
                value = not value
                click_type = COMMAND_SINGLE if value is True else False

            # Handle Multi Clicks
            elif attrid == 32768:
                click_type = CLICK_TYPE_MAP.get(value, UNKNOWN)

            if click_type:
                self.listener_event(
                    ZHA_SEND_EVENT, COMMAND_CLICK, {CLICK_TYPE: click_type}
                )

            super()._update_attribute(attrid, value)

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
                    PowerConfigurationCluster,
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
