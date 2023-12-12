"""Device handler for Sonoff TRVZB"""
import logging
import typing

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

LOGGER = logging.getLogger(f"zhaquirks.{__name__}")

SONOFF_CLUSTER_ID: typing.Final = 0xFC11
SONOFF_CLUSTER_ID_FC57: typing.Final = 0xFC57
SONOFF_ATTR_CHILD_LOCK: typing.Final = 0x0000
SONOFF_ATTR_WINDOW_OPEN: typing.Final = 0x6000


class SonoffManufCluster(CustomCluster):
    """Sonoff manufacturer specific cluster."""

    name: str = "Sonoff Manufacturer Specific"
    cluster_id: t.uint16_t = SONOFF_CLUSTER_ID
    ep_attribute: str = "sonoff_manufacturer"

    class AttributeDefs(BaseAttributeDefs):
        child_lock: typing.Final = ZCLAttributeDef(
            id=SONOFF_ATTR_CHILD_LOCK,
            type=t.Bool,
            mandatory=True,
            is_manufacturer_specific=False,
        )
        open_window: typing.Final = ZCLAttributeDef(
            id=SONOFF_ATTR_WINDOW_OPEN,
            type=t.Bool,
            mandatory=True,
            is_manufacturer_specific=False,
        )

    @property
    def _is_manuf_specific(self) -> bool:
        """Pretend this is not manufacturer specific as the device will always
        return Status.UNSUPPORTED_ATTRIBUTE if the manufacturer id is set
        """
        return False


class SonoffTRVZB(CustomDevice):
    """Custom device representing Sonoff TRVZB."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=769, device_version=1,
        #   input_clusters=[0, 1, 3, 6, 32, 513, 64599, 64529], output_clusters=[10, 25])
        MODELS_INFO: [("SONOFF", "TRVZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    SONOFF_CLUSTER_ID_FC57,
                    SonoffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    SONOFF_CLUSTER_ID_FC57,
                    SonoffManufCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
