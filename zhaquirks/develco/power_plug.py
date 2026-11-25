"""Develco smart plugs."""

from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.sensor import DeviceTemperature
from zigpy.zcl import ReportingConfig
from zigpy.zcl.clusters.general import DeviceTemperature as DeviceTemperatureCluster

from zhaquirks.builder import QuirkBuilder


class WholeDegreeDeviceTemperature(DeviceTemperature):
    """Device temperature in whole degrees."""

    _divisor = None  # Setting it to `1` would make the temperature a float
    _attr_suggested_display_precision = 0
    _attr_fallback_name = "Device temperature"
    # ZHA's reporting config assumes hundredths of a degree: its reportable change of
    # 50 would ask the device to report only on a change of 50 °C
    _server_cluster_config = {
        DeviceTemperatureCluster.cluster_id: ClusterConfig(
            bind=True,
            attributes={
                DeviceTemperatureCluster.AttributeDefs.current_temperature: AttrConfig(
                    read_on_startup=True,
                    reporting=ReportingConfig(
                        min_interval=30, max_interval=900, reportable_change=1
                    ),
                ),
            },
        ),
    }


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
