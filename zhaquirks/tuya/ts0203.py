"""Tuya Contact Sensor."""

from zigpy.quirks.v2 import ClusterType, add_to_registry_v2
from zigpy.zcl.clusters.general import Identify

from zhaquirks.tuya import TuyaPowerConfigurationCluster2AAA

(
    add_to_registry_v2("_TZ3000_6zvw8ham", "TS0203")
    .skip_configuration()
    .removes(Identify.cluster_id)
    .replaces(TuyaPowerConfigurationCluster2AAA)
    .removes(0x0003, cluster_type=ClusterType.Client)
    .removes(0x0004, cluster_type=ClusterType.Client)
    .removes(0x0005, cluster_type=ClusterType.Client)
    .removes(0x0006, cluster_type=ClusterType.Client)
    .removes(0x0008, cluster_type=ClusterType.Client)
    .removes(0x000a, cluster_type=ClusterType.Client)
    .removes(0x0019, cluster_type=ClusterType.Client)
    .removes(0x1000, cluster_type=ClusterType.Client)
)
