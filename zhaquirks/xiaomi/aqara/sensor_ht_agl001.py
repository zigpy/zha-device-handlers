"""Quirk for Aqara W100 Climate Sensor with 3 buttons."""

import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    MultistateInput,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from zhaquirks import CustomCluster
from zhaquirks.const import (
    ATTR_ID,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import XiaomiCustomDevice, XiaomiPowerConfiguration

_LOGGER = logging.getLogger(__name__)

# Attribute where button press values are reported
STATUS_TYPE_ATTR = 0x0055

# Buttons
PLUS_BUTTON = "plus"
CENTER_BUTTON = "center"
MINUS_BUTTON = "minus"


# Map reported values to action names
PRESS_TYPES = {
    0: COMMAND_HOLD,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    255: COMMAND_RELEASE,
}

# Optional label per endpoint
BUTTON_NAMES = {
    1: PLUS_BUTTON,
    2: CENTER_BUTTON,
    3: MINUS_BUTTON,
}


class MultistateInputCluster(CustomCluster, MultistateInput):
    """MultistateInput cluster that emits zha_event with button and press type."""

    def __init__(self, *args, **kwargs):
        """Initialize the MultistateInput cluster."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if attrid == STATUS_TYPE_ATTR:
            self._current_state = PRESS_TYPES.get(value, f"unknown_{value}")
            button = BUTTON_NAMES.get(
                self.endpoint.endpoint_id, f"ep{self.endpoint.endpoint_id}"
            )

            event_args = {
                PRESS_TYPE: self._current_state,
                VALUE: value,
                ATTR_ID: attrid,
                "button": button,
                "endpoint": self.endpoint.endpoint_id,
            }

            self.listener_event(ZHA_SEND_EVENT, self._current_state, event_args)
            _LOGGER.debug(
                "[W100] Button=%s, Action=%s, Value=%s", button, self._current_state, value
            )
            # Optionally update attr 0 for diagnostics
            super()._update_attribute(0, self._current_state)


class AqaraW100(XiaomiCustomDevice):
    """Aqara W100 Climate Sensor with buttons and ZHA event support."""

    signature = {
        MODELS_INFO: [("Aqara", "lumi.sensor_ht.agl001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0302,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    MultistateInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    0xFCC0,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0000,
                INPUT_CLUSTERS: [MultistateInput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0000,
                INPUT_CLUSTERS: [MultistateInput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0302,
                INPUT_CLUSTERS: [
                    Basic,
                    XiaomiPowerConfiguration,
                    Identify,
                    MultistateInputCluster,  # plus
                    TemperatureMeasurement,
                    RelativeHumidity,
                ],
                OUTPUT_CLUSTERS: [Ota],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0000,
                INPUT_CLUSTERS: [MultistateInputCluster],  # center
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0000,
                INPUT_CLUSTERS: [MultistateInputCluster],  # minus
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (PLUS_BUTTON, SHORT_PRESS): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 1},
        (PLUS_BUTTON, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE, ENDPOINT_ID: 1},
        (PLUS_BUTTON, LONG_PRESS): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 1},
        (PLUS_BUTTON, LONG_RELEASE): {COMMAND: COMMAND_RELEASE, ENDPOINT_ID: 1},
        (CENTER_BUTTON, SHORT_PRESS): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 2},
        (CENTER_BUTTON, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE, ENDPOINT_ID: 2},
        (CENTER_BUTTON, LONG_PRESS): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 2},
        (CENTER_BUTTON, LONG_RELEASE): {COMMAND: COMMAND_RELEASE, ENDPOINT_ID: 2},
        (MINUS_BUTTON, SHORT_PRESS): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 3},
        (MINUS_BUTTON, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE, ENDPOINT_ID: 3},
        (MINUS_BUTTON, LONG_PRESS): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 3},
        (MINUS_BUTTON, LONG_RELEASE): {COMMAND: COMMAND_RELEASE, ENDPOINT_ID: 3},
    }