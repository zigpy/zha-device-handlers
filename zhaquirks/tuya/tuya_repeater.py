"""Tuya Zigbee repeater."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Groups, OnOff, Scenes
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.builder import QuirkBuilder

# MG-ZJQ100
(
    QuirkBuilder("_TZ3000_wn65ixz9", "TS0001")
    .applies_to("_TZ3000_n0lphcok", "TS0001")
    .applies_to("_TZ3000_trdx8uxs", "TS0001")
    .applies_to("_TZ3000_gdsvhfao", "TS0001")
    .removes(OnOff.cluster_id)
    .removes(Metering.cluster_id)
    .removes(ElectricalMeasurement.cluster_id)
    .removes(Groups.cluster_id)
    .removes(Scenes.cluster_id)
    .replaces_endpoint(1, device_type=zha.DeviceType.RANGE_EXTENDER)
    .add_to_registry()
)
