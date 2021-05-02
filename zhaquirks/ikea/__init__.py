"""Ikea module."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Scenes
from zigpy.zcl.clusters.lightlink import LightLink

_LOGGER = logging.getLogger(__name__)
IKEA = "IKEA of Sweden"
ROTATED = "device_rotated"


class LightLinkCluster(CustomCluster, LightLink):
    """Ikea LightLink cluster."""

    async def bind(self):
        """Bind LightLink cluster to coordinator."""
        application = self._endpoint.device.application
        try:
            coordinator = application.get_device(application.ieee)
        except KeyError:
            _LOGGER.warning("Aborting - unable to locate required coordinator device.")
            return
        group_list = await self.get_group_identifiers(0)
        try:
            group_record = group_list[2]
            group_id = group_record[0].group_id
        except IndexError:
            _LOGGER.warning(
                "unable to locate required group info - falling back to group 0x0000."
            )
            group_id = 0x0000
        status = await coordinator.add_to_group(
            group_id,
            name="Default Lightlink Group",
        )
        return [status]


class ScenesCluster(CustomCluster, Scenes):
    """Ikea Scenes cluster."""

    server_commands = Scenes.server_commands.copy()
    server_commands.update(
        {
            0x0007: foundation.ZCLCommandDef(
                "press",
                {"param1": t.int16s, "param2": t.int8s, "param3": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0008: foundation.ZCLCommandDef(
                "hold",
                {"param1": t.int16s, "param2": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0009: foundation.ZCLCommandDef(
                "release",
                {
                    "param1": t.int16s,
                },
                False,
                is_manufacturer_specific=True,
            ),
        }
    )
