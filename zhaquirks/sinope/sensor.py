"""Module to handle quirks of the Sinopé Technologies water leak sensor and level monitor.

It add manufacturer attributes for IasZone cluster for the water leak alarm.
Supported devices are WL4200, WL4200S and LM4110-ZB
"""

from typing import Final

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import SINOPE, SINOPE_MANUFACTURER_CLUSTER_ID


class LeakStatus(t.enum8):
    """Leak_status values."""

    Dry = 0x00
    Leak = 0x01


class SinopeManufacturerCluster(CustomCluster):
    """SinopeManufacturerCluster manufacturer cluster."""

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(foundation.BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        firmware_number: Final = foundation.ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        firmware_version: Final = foundation.ZCLAttributeDef(
            id=0x0004, type=t.CharacterString, access="r", is_manufacturer_specific=True
        )
        min_temperature_limit: Final = foundation.ZCLAttributeDef(
            id=0x0032, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        max_temperature_limit: Final = foundation.ZCLAttributeDef(
            id=0x0033, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        device_status: Final = foundation.ZCLAttributeDef(
            id=0x0034, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        battery_type: Final = foundation.ZCLAttributeDef(
            id=0x0036, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        status: Final = foundation.ZCLAttributeDef(
            id=0x0200, type=t.bitmap32, access="rp", is_manufacturer_specific=True
        )
        cluster_revision: Final = foundation.ZCL_CLUSTER_REVISION_ATTR


class SinopeTechnologiesIasZoneCluster(CustomCluster, IasZone):
    """SinopeTechnologiesIasZoneCluster custom cluster."""

    LeakStatus: Final = LeakStatus

    class AttributeDefs(IasZone.AttributeDefs):
        """Sinope Manufacturer IasZone Cluster Attributes."""

        leak_status: Final = foundation.ZCLAttributeDef(
            id=0x0030, type=LeakStatus, access="rw", is_manufacturer_specific=True
        )


class SinopeTechnologiesSensor(CustomDevice):
    """SinopeTechnologiesSensor custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0 input_clusters=[0, 1, 3, 1026, 1280, 2821, 65281]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            (SINOPE, "WL4200"),
            (SINOPE, "WL4200S"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
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
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SinopeTechnologiesIasZoneCluster,
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


class SinopeTechnologiesSensor2(CustomDevice):
    """SinopeTechnologiesSensor2 custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0 input_clusters=[0, 1, 3, 20, 1026, 1280, 2821, 65281]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            (SINOPE, "WL4200"),
            (SINOPE, "WL4200S"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
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
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SinopeTechnologiesIasZoneCluster,
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


class SinopeTechnologiesLevelMonitor(CustomDevice):
    """SinopeTechnologiesLevelMonitor custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=0
        # device_version=0 input_clusters=[0, 1, 3, 12, 32, 1026, 2821, 65281]
        # output_clusters=[25]>
        MODELS_INFO: [
            (SINOPE, "LM4110-ZB"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    AnalogInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    AnalogInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SinopeManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        }
    }
