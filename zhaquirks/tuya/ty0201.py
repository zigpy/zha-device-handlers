"""Tuya TY0201 temperature and humidity sensor."""

import logging

from zigpy.quirks.v2 import CustomDeviceV2
import zigpy.types as t
from zigpy.zcl import Cluster, foundation

from zhaquirks.tuya import BaseEnchantedDevice, TuyaPowerConfigurationCluster2AA
from zhaquirks.tuya.builder import TuyaQuirkBuilder

_LOGGER = logging.getLogger(__name__)


class TY0201Device(CustomDeviceV2, BaseEnchantedDevice):
    """TY0201 device with direction fix and enchantment."""

    def _find_zcl_cluster(
        self, hdr: foundation.ZCLHeader, packet: t.ZigbeePacket
    ) -> Cluster:
        """Find a cluster for the packet."""

        # TY0201 devices seem to be very lax with their ZCL header's `direction` field,
        # we should try "flipping" it if matching doesn't work normally.
        try:
            return super()._find_zcl_cluster_strict(hdr, packet)
        except KeyError:
            _LOGGER.debug(
                "Packet is coming in the wrong direction, swapping direction and trying again",
            )

            return super()._find_zcl_cluster_strict(
                hdr.replace(
                    frame_control=hdr.frame_control.replace(
                        direction=hdr.frame_control.direction.flip()
                    )
                ),
                packet,
            )


(
    TuyaQuirkBuilder("_TZ3000_bjawzodf", "TY0201")
    .applies_to("_TZ3000_zl1kmjqx", "TY0201")
    .applies_to("_TZ3000_zl1kmjqx", "")
    .replaces(TuyaPowerConfigurationCluster2AA)
    .device_class(TY0201Device)
    .skip_configuration()
    .add_to_registry()
)
