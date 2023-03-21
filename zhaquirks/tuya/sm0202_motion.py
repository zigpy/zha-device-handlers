"""Device handler for Tuya LH-961ZB motion sensor."""
import asyncio
from typing import Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import _LOGGER
from zhaquirks.const import (
    CLUSTER_COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OFF,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATE,
)


class _Motion(CustomCluster, IasZone):
    """Self reset Motion cluster."""

    reset_s: int = 60

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._loop = asyncio.get_running_loop()
        self._timer_handle = None

    def _turn_off(self):
        self._timer_handle = None
        _LOGGER.debug("%s - Resetting motion sensor", self.endpoint.device.ieee)
        self.listener_event(CLUSTER_COMMAND, 253, ZONE_STATE, [OFF, 0, 0, 0])
        self._update_attribute(ZONE_STATE, OFF)


class MotionWithReset(_Motion):
    """Self reset Motion cluster."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple[IasZone.ZoneStatus],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None
    ):
        """Handle cluster request."""
        arg = args[0]
        if arg & IasZone.ZoneStatus.Alarm_1:
            """Handle the cluster command."""
            if self._timer_handle:
                self._timer_handle.cancel()
            self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)


class SM0202(CustomDevice):
    """Quirk for LH-961ZB motion sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    signature = {
        # "endpoint": 1
        # "profile_id": 260,
        # "device_type": "0x0402",
        # "in_clusters": ["0x0000","0x0001","0x0003", "0x0500", "0xeeff"],
        # "out_clusters": ["0x0019"]
        MODELS_INFO: [("_TYZB01_z2umiwvq", "SM0202")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    0xEEFF,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    MotionWithReset,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
