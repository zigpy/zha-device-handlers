"""Module to handle quirks of the Sinopé Technologies switches.

Supported devices, SP2600ZB, SP2610ZB, RM3250ZB, RM3500ZB,
VA4200WZ, VA4201WZ, VA4200ZB, VA4201ZB, VA4220ZB, VA4221ZB and MC3100ZB,
2nd gen VA4220ZB, VA4221ZB with flow meeter FS4220, FS4221.
"""

from typing import Final

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    DeviceTemperature,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import (
    FlowMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import Array

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import (
    SINOPE,
    SINOPE_MANUFACTURER_CLUSTER_ID,
    CustomDeviceTemperatureCluster,
)


class KeypadLock(t.enum8):
    """Keypad_lockout values."""

    Unlocked = 0x00
    Locked = 0x01
    Partial_lock = 0x02


class FlowAlarm(t.enum8):
    """Abnormal flow alarm."""

    Off = 0x00
    On = 0x01


class AlarmAction(t.enum8):
    """Flow alarm action."""

    Nothing = 0x00
    Notify = 0x01
    Close = 0x02
    Close_notify = 0x03
    No_flow = 0x04


class PowerSource(t.uint32_t):
    """Valve power source types."""

    Battery = 0x00000000
    ACUPS_01 = 0x00000001
    DC_power = 0x0001D4C0


class EmergencyPower(t.uint32_t):
    """Valve emergency power source types."""

    Battery = 0x00000000
    ACUPS_01 = 0x00000001
    Battery_ACUPS_01 = 0x0000003C


class AbnormalAction(t.bitmap16):
    """Action in case of abnormal flow detected."""

    Nothing = 0x0000
    Close_valve = 0x0001
    Close_notify = 0x0003


class ColdStatus(t.enum8):
    """Cold_load_pickup_status values."""

    Active = 0x00
    Off = 0x01


class FlowDuration(t.uint32_t):
    """Abnormal flow duration."""

    M_15 = 0x00000384
    M_30 = 0x00000708
    M_45 = 0x00000A8C
    M_60 = 0x00000E10
    M_75 = 0x00001194
    M_90 = 0x00001518
    H_3 = 0x00002A30
    H_6 = 0x00005460
    H_12 = 0x0000A8C0
    H_24 = 0x00015180


class InputDelay(t.uint16_t):
    """Delay for on/off input."""

    Off = 0x0000
    M_1 = 0x003C
    M_2 = 0x0078
    M_5 = 0x012C
    M_10 = 0x0258
    M_15 = 0x0384
    M_30 = 0x0708
    H_1 = 0x0E10
    H_2 = 0x1C20
    H_3 = 0x2A30


class EnergySource(t.enum8):
    """Power source."""

    Unknown = 0x0000
    DC_mains = 0x0001
    Battery = 0x0003
    DC_source = 0x0004
    ACUPS_01 = 0x0081
    ACUPS01 = 0x0082


class ValveStatus(t.bitmap8):
    """Valve_status."""

    Off = 0x00
    Off_armed = 0x01
    On = 0x02


class UnitOfMeasure(t.enum8):
    """Unit_of_measure."""

    KWh = 0x00
    Lh = 0x07


class SinopeManufacturerCluster(CustomCluster):
    """SinopeManufacturerCluster manufacturer cluster."""

    KeypadLock: Final = KeypadLock
    FlowAlarm: Final = FlowAlarm
    AlarmAction: Final = AlarmAction
    PowerSource: Final = PowerSource
    EmergencyPower: Final = EmergencyPower
    AbnormalAction: Final = AbnormalAction
    ColdStatus: Final = ColdStatus
    FlowDuration: Final = FlowDuration
    InputDelay: Final = InputDelay

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(foundation.BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        keypad_lockout: Final = foundation.ZCLAttributeDef(
            id=0x0002, type=KeypadLock, access="rw", is_manufacturer_specific=True
        )
        firmware_number: Final = foundation.ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        outdoor_temp: Final = foundation.ZCLAttributeDef(
            id=0x0010, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        unknown_attr_1: Final = foundation.ZCLAttributeDef(
            id=0x0013, type=t.enum8, access="rw", is_manufacturer_specific=True
        )
        connected_load: Final = foundation.ZCLAttributeDef(
            id=0x0060, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        current_load: Final = foundation.ZCLAttributeDef(
            id=0x0070, type=t.bitmap8, access="r", is_manufacturer_specific=True
        )
        dr_config_water_temp_min: Final = foundation.ZCLAttributeDef(
            id=0x0076, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        dr_config_water_temp_time: Final = foundation.ZCLAttributeDef(
            id=0x0077, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        dr_wt_time_on: Final = foundation.ZCLAttributeDef(
            id=0x0078, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        min_measured_temp: Final = foundation.ZCLAttributeDef(
            id=0x007C, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        max_measured_temp: Final = foundation.ZCLAttributeDef(
            id=0x007D, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        current_summation_delivered: Final = foundation.ZCLAttributeDef(
            id=0x0090, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        timer: Final = foundation.ZCLAttributeDef(
            id=0x00A0, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        timer_countdown: Final = foundation.ZCLAttributeDef(
            id=0x00A1, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        status: Final = foundation.ZCLAttributeDef(
            id=0x0200, type=t.bitmap32, access="rp", is_manufacturer_specific=True
        )
        alarm_flow_threshold: Final = foundation.ZCLAttributeDef(
            id=0x0230, type=FlowAlarm, access="rw", is_manufacturer_specific=True
        )
        alarm_options: Final = foundation.ZCLAttributeDef(
            id=0x0231, type=Array, access="r", is_manufacturer_specific=True
        )
        flow_meter_config: Final = foundation.ZCLAttributeDef(
            id=0x0240, type=AlarmAction, access="rw", is_manufacturer_specific=True
        )
        valve_countdown: Final = foundation.ZCLAttributeDef(
            id=0x0241, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )
        power_source: Final = foundation.ZCLAttributeDef(
            id=0x0250, type=PowerSource, access="rw", is_manufacturer_specific=True
        )
        emergency_power_source: Final = foundation.ZCLAttributeDef(
            id=0x0251, type=EmergencyPower, access="rw", is_manufacturer_specific=True
        )
        abnormal_flow_duration: Final = foundation.ZCLAttributeDef(
            id=0x0252, type=FlowDuration, access="rw", is_manufacturer_specific=True
        )
        abnormal_flow_action: Final = foundation.ZCLAttributeDef(
            id=0x0253, type=AbnormalAction, access="rw", is_manufacturer_specific=True
        )
        max_measured_value: Final = foundation.ZCLAttributeDef(
            id=0x0280, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        cold_load_pickup_status: Final = foundation.ZCLAttributeDef(
            id=0x0283, type=ColdStatus, access="r", is_manufacturer_specific=True
        )
        cold_load_pickup_remaining_time: Final = foundation.ZCLAttributeDef(
            id=0x0284, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        input_on_delay: Final = foundation.ZCLAttributeDef(
            id=0x02A0, type=InputDelay, access="rw", is_manufacturer_specific=True
        )
        input_off_delay: Final = foundation.ZCLAttributeDef(
            id=0x02A1, type=InputDelay, access="rw", is_manufacturer_specific=True
        )
        cluster_revision: Final = foundation.ZCL_CLUSTER_REVISION_ATTR


class SinopeTechnologiesBasicCluster(CustomCluster, Basic):
    """SinopetechnologiesBasicCluster custom cluster ."""

    EnergySource: Final = EnergySource

    class AttributeDefs(Basic.AttributeDefs):
        """Sinope Manufacturer Basic Cluster Attributes."""

        power_source: Final = foundation.ZCLAttributeDef(
            id=0x0007, type=EnergySource, access="r", is_manufacturer_specific=True
        )


class SinopeTechnologiesMeteringCluster(CustomCluster, Metering):
    """SinopeTechnologiesMeteringCluster custom cluster."""

    ValveStatus: Final = ValveStatus
    UnitOfMeasure: Final = UnitOfMeasure

    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {DIVISOR: 1000}

    class AttributeDefs(Metering.AttributeDefs):
        """Sinope Manufacturer Metering Cluster Attributes."""

        status: Final = foundation.ZCLAttributeDef(
            id=0x0200, type=ValveStatus, access="r", is_manufacturer_specific=True
        )
        unit_of_measure: Final = foundation.ZCLAttributeDef(
            id=0x0300, type=UnitOfMeasure, access="r", is_manufacturer_specific=True
        )


class SinopeTechnologiesFlowMeasurementCluster(CustomCluster, FlowMeasurement):
    """Custom flow measurement cluster that divides value by 10."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            value = value / 10
        super()._update_attribute(attrid, value)


class SinopeTechnologiesSwitch(CustomDevice):
    """SinopeTechnologiesSwitch custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=81, device_version=0,
        # input_clusters=[0, 3, 6, 1794, 2820, 65281]
        # output_clusters=[25]>
        MODELS_INFO: [
            (SINOPE, "SP2600ZB"),
            (SINOPE, "SP2610ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    SinopeTechnologiesMeteringCluster,
                    ElectricalMeasurement.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }


class SinopeTechnologiesLoadController(CustomDevice):
    """SinopeTechnologiesLoadController custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=2, device_version=0,
        # input_clusters=[0, 3, 4, 5, 6, 1794, 2820, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "RM3250ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesLoadController_V2(CustomDevice):
    """SinopeTechnologiesLoadController version 2 custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=2, device_version=0,
        # input_clusters=[0, 2, 3, 4, 5, 6, 1794, 2820, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "RM3250ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesValve(CustomDevice):
    """SinopeTechnologiesValve custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=3, device_version=0,
        # input_clusters=[0, 1, 3, 4, 5, 6, 8, 2821, 65281]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            (SINOPE, "VA4200WZ"),
            (SINOPE, "VA4201WZ"),
            (SINOPE, "VA4200ZB"),
            (SINOPE, "VA4201ZB"),
            (SINOPE, "VA4220ZB"),
            (SINOPE, "VA4221ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.LEVEL_CONTROLLABLE_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    SinopeTechnologiesBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesValveG2(CustomDevice):
    """SinopeTechnologiesValveG2 custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=3, device_version=0,
        # input_clusters=[0, 1, 3, 4, 5, 6, 8, 1026, 1280, 1794, 2821, 65281]
        # output_clusters=[3, 6, 25]>
        MODELS_INFO: [
            (SINOPE, "VA4220ZB"),
            (SINOPE, "VA4221ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.LEVEL_CONTROLLABLE_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    SinopeTechnologiesBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SinopeTechnologiesFlowMeasurementCluster,
                    IasZone.cluster_id,
                    SinopeTechnologiesMeteringCluster,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesMultiController(CustomDevice):
    """SinopeTechnologiesMultiController custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=2, device_version=0,
        # input_clusters=[0, 1, 3, 4, 5, 6, 15, 1026, 1029, 2821, 65281]
        # output_clusters=[25]>
        MODELS_INFO: [(SINOPE, "MC3100ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class SinopeTechnologiesCalypso(CustomDevice):
    """SinopeTechnologiesCalypso custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=260, device_version=0,
        # input_clusters=[0, 2, 3, 4, 5, 6, 1026, 1280, 1794, 2820, 2821, 65281]
        # output_clusters=[10, 25]>
        MODELS_INFO: [
            (SINOPE, "RM3500ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class SinopeTechnologiesSwitch_V2(CustomDevice):
    """SinopeTechnologiesSwitch version 2 custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=81, device_version=0,
        # input_clusters=[0, 3, 6, 1794, 2820, 4096, 65281]
        # output_clusters=[25, 4096]>
        MODELS_INFO: [
            (SINOPE, "SP2600ZB"),
            (SINOPE, "SP2610ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    SinopeTechnologiesMeteringCluster,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }
