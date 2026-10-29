"""Sonoff SNZB-06P - Zigbee presence sensor."""

from zha.application.platforms import ZclPlatformEntity
from zha.application.platforms.sensor import SonoffPresenceSenorIlluminationStatus
from zha.application.platforms.virtual import SonoffPresenceSensorInit
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster

SONOFF_CLUSTER_FC11_ID = 0xFC11
ATTR_SONOFF_ILLUMINATION_STATUS = 0x2001


class IlluminationStatus(t.enum8):
    """Last measured state of illumination enum."""

    Dark = 0x00
    Light = 0x01


class SonoffFC11Cluster(CustomCluster):
    """Sonoff manufacture specific cluster that provides illuminance."""

    cluster_id = SONOFF_CLUSTER_FC11_ID
    ep_attribute = "sonoff_manufacturer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        last_illumination_state = ZCLAttributeDef(
            id=ATTR_SONOFF_ILLUMINATION_STATUS,
            type=IlluminationStatus,
            manufacturer_code=None,
        )


class SonoffLastIlluminationStateSensor(SonoffPresenceSenorIlluminationStatus):
    """Last illumination state, also when a read marked it unsupported."""

    def _is_supported(self) -> bool:
        # The device only measures the illumination when it detects presence, and
        # answers reads of it with UNSUPPORTED_ATTRIBUTE otherwise
        if self._attribute_name not in self._cluster.attributes_by_name:
            return False

        return ZclPlatformEntity._is_supported(self)


class SonoffPresenceSensorInitWithoutRead(SonoffPresenceSensorInit):
    """ZHA's SNZB-06P cluster setup, without reading the last illumination state.

    The device answers that read with UNSUPPORTED_ATTRIBUTE unless presence was just
    detected, so the value is only taken from its reports.
    """

    _server_cluster_config = {}


(
    QuirkBuilder("SONOFF", "SNZB-06P")
    .removes(IasZone.cluster_id)
    .replaces(SonoffFC11Cluster)
    # The device reads the coordinator's KeepAlive server but does not advertise the
    # client side of the cluster. Unanswered reads make the device reboot itself
    # roughly every 8 minutes, resetting its settings.
    .adds(KeepAlive, cluster_type=ClusterType.Client, endpoint_id=1)
    .replaces_entity(
        SonoffPresenceSensorInit,
        SonoffPresenceSensorInitWithoutRead,
        endpoint_id=1,
        cluster_id=SonoffFC11Cluster.cluster_id,
    )
    .replaces_entity(
        SonoffPresenceSenorIlluminationStatus,
        SonoffLastIlluminationStateSensor,
        endpoint_id=1,
        cluster_id=SonoffFC11Cluster.cluster_id,
    )
    .add_to_registry()
)
