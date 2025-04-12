"""Aqara Z1 Pro single rocker switch quirks."""

import logging
import sys
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
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
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    OnOffCluster,
    XiaomiCustomDevice,
)
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster

# Set up logging with a more visible format
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

# Add a console handler to ensure logs go to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
_LOGGER.addHandler(console_handler)

# Log at module level to verify the file is being loaded
_LOGGER.debug("AqaraZ1ProSingleRockerSwitch quirk module is being loaded! ZHA Profile ID: 0x%04x, Device Type: 0x%04x", zha.PROFILE_ID, zha.DeviceType.ON_OFF_SWITCH)

class AqaraZ1ProSliderCluster(CustomCluster):
    """Custom cluster for Aqara Z1 Pro slider events."""
    
    cluster_id = 0xfcc0
    
    # Attribute IDs
    ATTR_SLIDER_ACTION = 0x028C  # 652
    ATTR_SLIDE_TIME = 0x0231     # 561
    ATTR_SLIDE_SPEED = 0x0232    # 562
    ATTR_SLIDE_RELATIVE_DISPLACEMENT = 0x0233  # 563
    ATTR_SLIDE_TIME_DELTA = 0x0301  # 769
    
    # Action mapping
    ACTION_MAPPING = {
        1: "slider_single",
        2: "slider_double",
        3: "slider_hold",
        4: "slider_up",
        5: "slider_down",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attr_id = self.ATTR_SLIDER_ACTION
        _LOGGER.debug("AqaraZ1ProSliderCluster initialized for device %s", self._endpoint.device.ieee)
        
    async def _update_attribute(self, attrid, value):
        """Handle attribute updates."""
        _LOGGER.debug("AqaraZ1ProSliderCluster attribute update: attrid=0x%04x, value=%s", attrid, value)
        super()._update_attribute(attrid, value)
        
        # Store all attributes for the event
        if not hasattr(self, "_slider_attrs"):
            self._slider_attrs = {}
        
        # Update the attribute value
        self._slider_attrs[attrid] = value
        
        # If this is the slider action attribute, send the event
        if attrid == self.ATTR_SLIDER_ACTION:
            # Get the action name from the mapping
            action = self.ACTION_MAPPING.get(value, f"slider_unknown_{value}")
            _LOGGER.debug("AqaraZ1ProSliderCluster detected action: %s (value: %s)", action, value)
            
            # Prepare the event data
            event_data = {
                "device_ieee": str(self._endpoint.device.ieee),
                "endpoint_id": self._endpoint.endpoint_id,
                "cluster_id": self.cluster_id,
                "command": action,
                "args": {
                    "action": action,
                    "value": value,
                    "slide_time": self._slider_attrs.get(self.ATTR_SLIDE_TIME),
                    "slide_speed": self._slider_attrs.get(self.ATTR_SLIDE_SPEED),
                    "slide_relative_displacement": self._slider_attrs.get(self.ATTR_SLIDE_RELATIVE_DISPLACEMENT),
                    "slide_time_delta": self._slider_attrs.get(self.ATTR_SLIDE_TIME_DELTA),
                },
            }
            
            _LOGGER.debug("AqaraZ1ProSliderCluster sending event data: %s", event_data)
            
            # Send the event
            self.listener_event(
                "zha_send_event",
                action,
                event_data,
            )
            
            # Also send a generic slider event for easier automation
            self.listener_event(
                "zha_send_event",
                "slider_event",
                event_data,
            )
            _LOGGER.debug("AqaraZ1ProSliderCluster events sent successfully")


class AqaraZ1ProSingleRockerSwitch(XiaomiCustomDevice):
    """Aqara Z1 Pro Single Rocker Switch"""

    MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xfcc0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _LOGGER.debug("AqaraZ1ProSingleRockerSwitch device initialized with IEEE: %s", self.ieee)
    
    signature = {
        MODELS_INFO: [("Aqara", "lumi.switch.acn056")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    MeteringCluster.cluster_id,
                    ElectricalMeasurementCluster.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    AqaraZ1ProSliderCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }