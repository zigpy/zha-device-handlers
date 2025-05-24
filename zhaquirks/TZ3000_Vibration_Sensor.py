import logging
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, PowerConfiguration, Identify
from zigpy.zcl.clusters.security import IasZone
from zhaquirks.tuya import TuyaManufCluster
import zigpy.types as t

_LOGGER = logging.getLogger(__name__)


class TuyaAxisCluster(TuyaManufCluster):
    """Custom cluster to decode accelerometer axis data from TS0601."""

    cluster_id = 0xEF00

    attributes = {
        0x0101: ("accel_x", t.int32s, True),
        0x0102: ("accel_y", t.int32s, True),
        0x0103: ("accel_z", t.int32s, True),
    }

    def handle_cluster_request(self, hdr, args, dst_addressing=None):
        """Handle incoming Tuya cluster requests."""
        _LOGGER.debug("handle_cluster_request: hdr=%s args=%s", hdr, args)

        if not args or not hasattr(args[0], "command_id"):
            _LOGGER.warning("Unexpected args: %s", args)
            return

        cmd_id = args[0].command_id
        raw_val = int.from_bytes(args[0].data[-1:], byteorder="big", signed=True)

        if cmd_id == 0x0265:
            self._update_attribute(0x0101, raw_val)
            _LOGGER.debug("Updated accel_x: %d", raw_val)
        elif cmd_id == 0x0266:
            self._update_attribute(0x0102, raw_val)
            _LOGGER.debug("Updated accel_y: %d", raw_val)
        elif cmd_id == 0x0267:
            self._update_attribute(0x0103, raw_val)
            _LOGGER.debug("Updated accel_z: %d", raw_val)
        else:
            _LOGGER.debug("Unhandled command_id: 0x%04x", cmd_id)


class TuyaVibrationSensor(CustomDevice):
    """Custom device representing Tuya vibration sensor _TZ3000_lqpt3mvr."""

    signature = {
        "model": "TS0601",
        "manufacturer": "_TZ3000_lqpt3mvr",
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": 0x0402,
                "input_clusters": [
                    0x0000,  # Basic
                    0x0001,  # PowerConfiguration
                    0x0003,  # Identify
                    0x0500,  # IasZone
                ],
                "output_clusters": [],
            },
        },
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": 0x0000,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    PowerConfiguration.cluster_id,
                    TuyaAxisCluster,
                ],
                "output_clusters": [],
            },
        },
    }
