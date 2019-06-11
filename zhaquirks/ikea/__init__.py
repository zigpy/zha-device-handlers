"""Ikea module."""
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.quirks import CustomCluster


class LightLinkCluster(CustomCluster, LightLink):
    """Ikea LightLink cluster."""

    async def bind(self):
        """Bind LightLink cluster to coordinator."""
        application = self._endpoint.device.application
        coordinator = application.get_device(application.ieee)
        group_list = await self.get_group_identifiers(0)
        group_record = group_list[2]
        group_id = group_record[0].group_id
        await coordinator.add_to_group(group_id)
