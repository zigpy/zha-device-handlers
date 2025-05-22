"""AduroSmart Eria Adurolight_CSC device."""

import time

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color as ColorControl
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import CustomCluster, EventableCluster
from zhaquirks.aduro import ADUROLIGHT_CLUSTER_ID
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

BTN_CODE_MAP = {
    (0, 0): (BUTTON_1, SHORT_PRESS),
    (0, 1): (BUTTON_2, SHORT_PRESS),
    (0, 2): (BUTTON_3, SHORT_PRESS),
    (0, 3): (BUTTON_4, SHORT_PRESS),
    (1, 0): (BUTTON_1, LONG_PRESS),
    (1, 1): (BUTTON_2, LONG_PRESS),
    (1, 2): (BUTTON_3, LONG_PRESS),
    (1, 3): (BUTTON_4, LONG_PRESS),
}

ACTION_MAP = {
    (BUTTON_1, SHORT_PRESS): "button_1_short_press",
    (BUTTON_2, SHORT_PRESS): "button_2_short_press",
    (BUTTON_3, SHORT_PRESS): "button_3_short_press",
    (BUTTON_4, SHORT_PRESS): "button_4_short_press",
    (BUTTON_1, LONG_PRESS): "button_1_long_press",
    (BUTTON_2, LONG_PRESS): "button_2_long_press",
    (BUTTON_3, LONG_PRESS): "button_3_long_press",
    (BUTTON_4, LONG_PRESS): "button_4_long_press",
}

# DEBOUNCE settings (ADUROLIGHT_CSC buttons tend to send duplicate events)
_DEBOUNCE_INTERVAL = 1  # seconds
_last_event = {}


def _debounce_key(button, press_type):
    return (button, press_type)


class AdurolightFcccCluster(EventableCluster, CustomCluster):
    """Custom cluster for AduroSmart Eria FCCC manufacturer-specific events."""

    cluster_id = ADUROLIGHT_CLUSTER_ID
    manufacturer_specific = True

    def handle_cluster_request(
        self, hdr: foundation.ZCLHeader, args, dst_addressing=None
    ):
        """Handle incoming cluster requests and emit ZHA events with debounce logic."""
        cmd = hdr.command_id
        seq = getattr(hdr, "tsn", None)
        self.debug(f"[FCCC] seq={seq}, cmd={cmd}, args={args}")
        if cmd != 0 or len(args) < 2:
            return False
        btn_key = (args[0], args[1])
        if btn_key not in BTN_CODE_MAP:
            self.debug(f"[FCCC] Unknown button key: {btn_key}, args={args}")
            return False
        button, press_type = BTN_CODE_MAP[btn_key]
        action = ACTION_MAP.get((button, press_type), f"button_{button}_{press_type}")
        event_args = {
            "button": button,
            "press_type": press_type,
            "args": args,
            "params": {},
        }
        # --- Debounce logic: only emit if enough time has passed since last identical event ---
        key = _debounce_key(button, press_type)
        now = time.monotonic()
        last_time = _last_event.get(key, 0)
        if now - last_time < _DEBOUNCE_INTERVAL:
            self.debug(
                f"[FCCC] Debounced duplicate event: {action} (delta={now - last_time:.2f}s)"
            )
            return True  # don't emit again
        _last_event[key] = now
        # ---
        self.debug(f"[FCCC] Emitting event: {action}, {event_args}")
        self.listener_event(ZHA_SEND_EVENT, action, event_args)
        return True


class AdurolightCSCRemote(CustomDevice):
    """Device quirk for AduroSmart Eria ADUROLIGHT_CSC remote."""

    signature = {
        MODELS_INFO: [("AduroSmart Eria", "ADUROLIGHT_CSC")],
        ENDPOINTS: {
            #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2064
            #  device_version=0
            #  input_clusters=[0, 1, 3, 4, 5, 6, 8, 768, 4096, 64716]
            #  output_clusters=[0, 3, 4, 5, 6, 8, 768, 4096, 64716]>
            1: {
                PROFILE_ID: 0xC05E,
                DEVICE_TYPE: 0x0810,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    ColorControl.cluster_id,
                    LightLink.cluster_id,
                    ADUROLIGHT_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    ColorControl.cluster_id,
                    LightLink.cluster_id,
                    ADUROLIGHT_CLUSTER_ID,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=49246 device_type=1010
            #  device_version=0
            #  input_clusters=[4096]
            #  output_clusters=[4096]>
            2: {
                PROFILE_ID: 0xC05E,
                DEVICE_TYPE: 0x03F2,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0810,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    AdurolightFcccCluster,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    AdurolightFcccCluster,
                    LightLink.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x03F2,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_1_short_press",
        },
        (SHORT_PRESS, BUTTON_2): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_2_short_press",
        },
        (SHORT_PRESS, BUTTON_3): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_3_short_press",
        },
        (SHORT_PRESS, BUTTON_4): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_4_short_press",
        },
        (LONG_PRESS, BUTTON_1): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_1_long_press",
        },
        (LONG_PRESS, BUTTON_2): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_2_long_press",
        },
        (LONG_PRESS, BUTTON_3): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_3_long_press",
        },
        (LONG_PRESS, BUTTON_4): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: ADUROLIGHT_CLUSTER_ID,
            COMMAND: "button_4_long_press",
        },
    }
