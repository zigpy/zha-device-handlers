"""zunzunbee button device."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    CLUSTER_ID,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.zunzunbee import ZUNZUNBEE

BUTTON_7 = "button_7"
BUTTON_8 = "button_8"

PRESS_TYPES = {
    1: SHORT_PRESS,
    2: LONG_PRESS,
}


class ZunZunBeeIASCluster(CustomCluster, IasZone):
    """IAS cluster used for ZunZunBee button."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        press = (value & 1) + 1
        value = value & 0x01FE
        if attrid == self.AttributeDefs.zone_status.id:
            if value == 2:
                button = BUTTON_1
                press_type = PRESS_TYPES[press]
            elif value == 4:
                button = BUTTON_2
                press_type = PRESS_TYPES[press]
            elif value == 8:
                button = BUTTON_3
                press_type = PRESS_TYPES[press]
            elif value == 16:
                button = BUTTON_4
                press_type = PRESS_TYPES[press]
            elif value == 32:
                button = BUTTON_5
                press_type = PRESS_TYPES[press]
            elif value == 64:
                button = BUTTON_6
                press_type = PRESS_TYPES[press]
            elif value == 128:
                button = BUTTON_7
                press_type = PRESS_TYPES[press]
            elif value == 256:
                button = BUTTON_8
                press_type = PRESS_TYPES[press]
            else:
                # discard invalid values: 0, 6, 12, 18
                return

            action = f"{button}_{press_type}"
            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


class ZunZunBeeButton(CustomDevice):
    """zunzunbee button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        # output_clusters=[3, 25]>
        MODELS_INFO: [(ZUNZUNBEE, "SSWZ8T")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0104,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    ZunZunBeeIASCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }

    device_automation_triggers = {
        (press_type, button): {
            COMMAND: f"{button}_{press_type}",
            CLUSTER_ID: IasZone.cluster_id,
        }
        for press_type in (SHORT_PRESS, LONG_PRESS)
        for button in (
            BUTTON_1,
            BUTTON_2,
            BUTTON_3,
            BUTTON_4,
            BUTTON_5,
            BUTTON_6,
            BUTTON_7,
            BUTTON_8,
        )
    }
