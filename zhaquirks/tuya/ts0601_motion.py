"""BlitzWolf IS-3/Tuya motion rechargeable occupancy sensor."""

import math
from typing import Dict, Optional, Tuple, Union

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogInput,
    AnalogOutput,
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    NoManufacturerCluster,
    TuyaLocalCluster,
    TuyaManufCluster,
    TuyaNewManufCluster,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaMCUCluster,
)

ZONE_TYPE = 0x0001


class TuyaMmwRadarSelfTest(t.enum8):
    """Mmw radar self test values."""

    TESTING = 0
    TEST_SUCCESS = 1
    TEST_FAILURE = 2
    OTHER = 3
    COMM_FAULT = 4
    RADAR_FAULT = 5


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


class TuyaAnalogInput(AnalogInput, TuyaLocalCluster):
    """Tuya local AnalogInput cluster."""


class TuyaIlluminanceMeasurement(IlluminanceMeasurement, TuyaLocalCluster):
    """Tuya local IlluminanceMeasurement cluster."""


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""


class TuyaRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster."""


class TuyaMmwRadarSensitivity(TuyaAttributesCluster, AnalogOutput):
    """AnalogOutput cluster for sensitivity."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(self.attributes_by_name["description"].id, "sensitivity")
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 1)
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 9)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)


class TuyaMmwRadarMinRange(TuyaAttributesCluster, AnalogOutput):
    """AnalogOutput cluster for min range."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(self.attributes_by_name["description"].id, "min_range")
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 0)
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 950)
        self._update_attribute(self.attributes_by_name["resolution"].id, 10)
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 118
        )  # 31: meters


class TuyaMmwRadarMaxRange(TuyaAttributesCluster, AnalogOutput):
    """AnalogOutput cluster for max range."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(self.attributes_by_name["description"].id, "max_range")
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 10)
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 950)
        self._update_attribute(self.attributes_by_name["resolution"].id, 10)
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 118
        )  # 31: meters


class TuyaMmwRadarDetectionDelay(TuyaAttributesCluster, AnalogOutput):
    """AnalogOutput cluster for detection delay."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.attributes_by_name["description"].id, "detection_delay"
        )
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 000)
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 20000)
        self._update_attribute(self.attributes_by_name["resolution"].id, 100)
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 159
        )  # 73: seconds


class TuyaMmwRadarFadingTime(TuyaAttributesCluster, AnalogOutput):
    """AnalogOutput cluster for fading time."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(self.attributes_by_name["description"].id, "fading_time")
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 2000)
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 200000)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1000)
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 159
        )  # 73: seconds


class TuyaMmwRadarTargetDistance(TuyaAttributesCluster, AnalogInput):
    """AnalogInput cluster for target distance."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.attributes_by_name["description"].id, "target_distance"
        )
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 118
        )  # 31: meters


class NeoBatteryLevel(t.enum8):
    """NEO battery level enum."""

    BATTERY_FULL = 0x00
    BATTERY_HIGH = 0x01
    BATTERY_MEDIUM = 0x02
    BATTERY_LOW = 0x03
    USB_POWER = 0x04


class NeoMotionManufCluster(TuyaNewManufCluster):
    """Neo manufacturer cluster."""

    attributes = TuyaNewManufCluster.attributes.copy()
    attributes.update(
        {
            0xEF0D: ("dp_113", t.enum8, True),  # ramdom attribute ID
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        101: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        104: DPToAttributeMapping(
            TuyaTemperatureMeasurement.ep_attribute,
            "measured_value",
            lambda x: x * 10,
        ),
        105: DPToAttributeMapping(
            TuyaRelativeHumidity.ep_attribute,
            "measured_value",
            lambda x: x * 100,
        ),
        113: DPToAttributeMapping(
            TuyaNewManufCluster.ep_attribute,
            "dp_113",
        ),
    }

    data_point_handlers = {
        101: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        113: "_dp_2_attr_update",
    }


class TuyaMmwRadarClusterBase(NoManufacturerCluster, TuyaMCUCluster):
    """Mmw radar cluster, base class."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            # ramdom attribute IDs
            0xEF01: ("occupancy", t.uint32_t, True),
            0xEF02: ("sensitivity", t.uint32_t, True),
            0xEF03: ("min_range", t.uint32_t, True),
            0xEF04: ("max_range", t.uint32_t, True),
            0xEF06: ("self_test", TuyaMmwRadarSelfTest, True),
            0xEF09: ("target_distance", t.uint32_t, True),
            0xEF65: ("detection_delay", t.uint32_t, True),
            0xEF66: ("fading_time", t.uint32_t, True),
            0xEF67: ("cli", t.CharacterString, True),
            0xEF68: ("illuminance", t.uint32_t, True),
        }
    )


class TuyaMmwRadarClusterV1(TuyaMmwRadarClusterBase):
    """Mmw radar cluster, variant 1."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        2: DPToAttributeMapping(
            TuyaMmwRadarSensitivity.ep_attribute,
            "present_value",
        ),
        3: DPToAttributeMapping(
            TuyaMmwRadarMinRange.ep_attribute,
            "present_value",
            endpoint_id=2,
        ),
        4: DPToAttributeMapping(
            TuyaMmwRadarMaxRange.ep_attribute,
            "present_value",
            endpoint_id=3,
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "self_test",
        ),
        9: DPToAttributeMapping(
            TuyaMmwRadarTargetDistance.ep_attribute,
            "present_value",
            lambda x: x / 100,
        ),
        101: DPToAttributeMapping(
            TuyaMmwRadarDetectionDelay.ep_attribute,
            "present_value",
            converter=lambda x: x * 100,
            dp_converter=lambda x: x // 100,
            endpoint_id=4,
        ),
        102: DPToAttributeMapping(
            TuyaMmwRadarFadingTime.ep_attribute,
            "present_value",
            converter=lambda x: x * 100,
            dp_converter=lambda x: x // 100,
            endpoint_id=5,
        ),
        103: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "cli",
        ),
        104: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: int(math.log10(x) * 10000 + 1) if x > 0 else int(0),
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        9: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
    }


class TuyaMmwRadarClusterV2(TuyaMmwRadarClusterBase):
    """Mmw radar cluster, variant 2."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        2: DPToAttributeMapping(
            TuyaMmwRadarSensitivity.ep_attribute,
            "present_value",
        ),
        3: DPToAttributeMapping(
            TuyaMmwRadarMinRange.ep_attribute,
            "present_value",
            endpoint_id=2,
        ),
        4: DPToAttributeMapping(
            TuyaMmwRadarMaxRange.ep_attribute,
            "present_value",
            endpoint_id=3,
        ),
        9: DPToAttributeMapping(
            TuyaMmwRadarTargetDistance.ep_attribute,
            "present_value",
        ),
        101: DPToAttributeMapping(
            TuyaMmwRadarDetectionDelay.ep_attribute,
            "present_value",
            converter=lambda x: x * 100,
            dp_converter=lambda x: x // 100,
            endpoint_id=4,
        ),
        102: DPToAttributeMapping(
            TuyaMmwRadarFadingTime.ep_attribute,
            "present_value",
            converter=lambda x: x * 100,
            dp_converter=lambda x: x // 100,
            endpoint_id=5,
        ),
        104: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: int(math.log10(x) * 10000 + 1) if x > 0 else int(0),
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        9: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
    }


class TuyaMmwRadarClusterV3(TuyaMmwRadarClusterBase):
    """Tuya MMW radar cluster, variant 3."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        103: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "cli",
        ),
        104: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "measured_value",
            converter=lambda x: int(math.log10(x) * 10000 + 1) if x > 0 else int(0),
        ),
        105: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        106: DPToAttributeMapping(
            TuyaMmwRadarSensitivity.ep_attribute,
            "present_value",
        ),
        107: DPToAttributeMapping(
            TuyaMmwRadarMaxRange.ep_attribute,
            "present_value",
            endpoint_id=3,
        ),
        108: DPToAttributeMapping(
            TuyaMmwRadarMinRange.ep_attribute,
            "present_value",
            endpoint_id=2,
        ),
        109: DPToAttributeMapping(
            TuyaMmwRadarTargetDistance.ep_attribute,
            "present_value",
        ),
        110: DPToAttributeMapping(
            TuyaMmwRadarFadingTime.ep_attribute,
            "present_value",
            converter=lambda x: x * 100,
            dp_converter=lambda x: x // 100,
            endpoint_id=5,
        ),
        111: DPToAttributeMapping(
            TuyaMmwRadarDetectionDelay.ep_attribute,
            "present_value",
            converter=lambda x: x * 100,
            dp_converter=lambda x: x // 100,
            endpoint_id=4,
        ),
    }

    data_point_handlers = {
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        106: "_dp_2_attr_update",
        107: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
        110: "_dp_2_attr_update",
        111: "_dp_2_attr_update",
    }


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Tuya Motion Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Motion_Sensor}
    reset_s = 15


class TuyaManufacturerClusterMotion(TuyaManufCluster):
    """Manufacturer Specific Cluster of the Motion device."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple[TuyaManufCluster.Command],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""
        tuya_cmd = args[0]
        self.debug("handle_cluster_request--> hdr: %s, args: %s", hdr, args)
        if hdr.command_id == 0x0001 and tuya_cmd.command_id == 1027:
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)


class TuyaMotion(CustomDevice):
    """BW-IS3 occupancy sensor."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_i5j6ifxj", "5j6ifxj"), ("_TYST11_7hfcudw5", "hfcudw5")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    MotionCluster,
                    TuyaManufacturerClusterMotion,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }


class NeoMotion(CustomDevice):
    """NAS-PD07 occupancy sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_7hfcudw5", "TS0601"),
            ("_TZE200_ppuj1vem", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoMotionManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoMotionManufCluster,
                    TuyaOccupancySensing,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaMmwRadarOccupancyVariant1GPP(CustomDevice):
    """Millimeter wave occupancy sensor."""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[4, 5, 61184, 0], output_clusters=[25, 10])
        MODELS_INFO: [
            ("_TZE200_ar0slwnd", "TS0601"),
            ("_TZE200_sfiy5tfs", "TS0601"),
            ("_TZE200_mrf6vtua", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
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
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMmwRadarClusterV1,
                    TuyaOccupancySensing,
                    TuyaAnalogInput,
                    TuyaIlluminanceMeasurement,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaMmwRadarOccupancyVariant1(CustomDevice):
    """Millimeter wave occupancy sensor."""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10]
        MODELS_INFO: [
            ("_TZE200_ar0slwnd", "TS0601"),
            ("_TZE200_sfiy5tfs", "TS0601"),
            ("_TZE200_mrf6vtua", "TS0601"),
            ("_TZE200_ztc6ggyl", "TS0601"),
            ("_TZE204_ztc6ggyl", "TS0601"),
            ("_TZE200_wukb7rhc", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMmwRadarClusterV1,
                    TuyaIlluminanceMeasurement,
                    TuyaOccupancySensing,
                    TuyaMmwRadarTargetDistance,
                    TuyaMmwRadarSensitivity,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        }
    }


class TuyaMmwRadarOccupancyVariant2(CustomDevice):
    """Mini/Ceiling Human Breathe Sensor"""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[4, 5, 61184, 0], output_clusters=[25, 10]
        MODELS_INFO: [
            ("_TZE204_qasjif9e", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242, profile=41440, device_type=97, device_version=0, input_clusters=[], output_clusters=[33]
                # input_clusters=[]
                # output_clusters=[33]
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
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMmwRadarClusterV2,
                    TuyaIlluminanceMeasurement,
                    TuyaOccupancySensing,
                    TuyaMmwRadarTargetDistance,
                    TuyaMmwRadarSensitivity,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarMinRange,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarMaxRange,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarDetectionDelay,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarFadingTime,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaMmwRadarOccupancyVariant3(CustomDevice):
    """Mini/Ceiling Human Breathe Sensor"""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10])
        MODELS_INFO: [
            ("_TZE204_sxm7l9xa", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
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
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMmwRadarClusterV3,
                    TuyaIlluminanceMeasurement,
                    TuyaOccupancySensing,
                    TuyaMmwRadarTargetDistance,
                    TuyaMmwRadarSensitivity,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarMinRange,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarMaxRange,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarDetectionDelay,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    TuyaMmwRadarFadingTime,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
