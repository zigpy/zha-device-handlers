"""Develco smart plugs."""

from zha.application.platforms.sensor import DeviceTemperature
from zigpy.zcl.clusters.general import DeviceTemperature as DeviceTemperatureCluster

from zhaquirks.builder import QuirkBuilder


class WholeDegreeDeviceTemperature(DeviceTemperature):
    """Device temperature in whole degrees: the device does not follow the spec."""

    _divisor = 1


(
    QuirkBuilder("frient A/S", "SPLZB-141")
    .applies_to("Develco Products A/S", "SPLZB-131")
    .replaces_entity(
        DeviceTemperature,
        WholeDegreeDeviceTemperature,
        endpoint_id=2,
        cluster_id=DeviceTemperatureCluster.cluster_id,
    )
    .add_to_registry()
)
