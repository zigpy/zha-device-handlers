"""LDS module."""
import logging

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.lightlink import LightLink

_LOGGER = logging.getLogger(__name__)
MANUFACTURER = "LDS"


class LightLinkCluster(CustomCluster, LightLink):
    """LDS LightLink cluster."""

    async def bind(self):
        """Bind LightLink cluster to coordinator."""
        application = self._endpoint.device.application
        try:
            coordinator = application.get_device(application.ieee)
        except KeyError:
            _LOGGER.warning("Aborting - unable to locate required coordinator device.")
            return
        group_list = await self.get_group_identifiers(0)
        group_record = group_list[2]
        group_id = group_record[0].group_id
        status = await coordinator.add_to_group(group_id)
        return [status]
