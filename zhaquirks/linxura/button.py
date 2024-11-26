"""Linxura button device."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    DEVICE_TYPE,
    DOUBLE_PRESS,
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
from zhaquirks.linxura import LINXURA

PRESS_TYPES = {
    1: SHORT_PRESS,
    2: DOUBLE_PRESS,
    3: LONG_PRESS,
}


class LinxuraIASCluster(CustomCluster, IasZone):
    """IAS cluster used for Linxura button."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.zone_status.id and 0 < value < 24:
            if 0 < value < 6:
                button = BUTTON_1
                press_type = PRESS_TYPES[value // 2 + 1]
            elif 6 < value < 12:
                button = BUTTON_2
                press_type = PRESS_TYPES[value // 2 - 3 + 1]
            elif 12 < value < 18:
                button = BUTTON_3
                press_type = PRESS_TYPES[value // 2 - 6 + 1]
            elif 18 < value < 24:
                button = BUTTON_4
                press_type = PRESS_TYPES[value // 2 - 9 + 1]
            else:
                # discard invalid values: 0, 6, 12, 18
                return

            action = f"{button}_{press_type}"
            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


class LinxuraButton(CustomDevice):
    """Linxura button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 3, 1280]=>input_clusters=[0, 1280]
        # output_clusters=[3]>=>output_clusters=[]
        MODELS_INFO: [(LINXURA, "Smart Controller")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LinxuraIASCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }

    device_automation_triggers = {
        (press_type, button): {
            COMMAND: f"{button}_{press_type}",
            CLUSTER_ID: IasZone.cluster_id,
        }
        for press_type in (SHORT_PRESS, DOUBLE_PRESS, LONG_PRESS)
        for button in (BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4)
    }
