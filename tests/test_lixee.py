"""Tests for LiXee quirks."""

import json

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement, MeterIdentification
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zdo.types import NodeDescriptor

from tests.zha_helpers import DEVICES_DIR, join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.lixee import LIXEE
from zhaquirks.lixee.zlinky import (
    LinkyMode,
    ZLinkyTICManufacturerCluster,
    ZLinkyTICMetering,
)
from zhaquirks.tuya import TuyaManufCluster

zhaquirks.setup()

ZLINKY_DIAGNOSTICS = "lixee-zlinky-tic-0x00000001.json"

# Read attribute responses of a ZLinky (firmware v16, app_version 16) on a Linky in
# historical mode, Tempo contract
ZCL_TARIFF_OPTION = bytes.fromhex(
    "1c3710c101000000421042425228000000000000000000000000"
)
ZCL_TARIFF_PERIOD = bytes.fromhex("1c3710b301100000420448504a42")
ZCL_TOMORROW_COLOR = bytes.fromhex("1c3710b20101000042042d2d2d2d")
ZCL_LINKY_MODE = bytes.fromhex("1c3710b6010003002000")


@pytest.mark.parametrize(
    "in_clusters,out_clusters",
    [
        # firmware before v12.0
        ((), ()),
        # firmware v12.0 & v13.0
        ((PowerConfiguration.cluster_id,), ()),
        # firmware v14.0+
        (
            (
                PowerConfiguration.cluster_id,
                Time.cluster_id,
                TuyaManufCluster.cluster_id,
            ),
            (TuyaManufCluster.cluster_id,),
        ),
    ],
)
def test_zlinky_clusters(MockAppController, ieee_mock, in_clusters, out_clusters):
    """Test the clusters of all ZLinky_TIC firmware versions."""
    device = zigpy.device.Device(MockAppController, ieee_mock, t.NWK(0x1234))
    device.manufacturer = LIXEE
    device.model = "ZLinky_TIC"
    device.node_desc = NodeDescriptor(manufacturer_code=0x1037)
    ep = device.add_endpoint(1)
    ep.profile_id = zha.PROFILE_ID
    ep.device_type = zha.DeviceType.METER_INTERFACE
    for cluster_id in (
        Basic.cluster_id,
        Identify.cluster_id,
        Metering.cluster_id,
        MeterIdentification.cluster_id,
        ElectricalMeasurement.cluster_id,
        ZLinkyTICManufacturerCluster.cluster_id,
        *in_clusters,
    ):
        ep.add_input_cluster(cluster_id)
    ep.add_output_cluster(Ota.cluster_id)
    for cluster_id in out_clusters:
        ep.add_output_cluster(cluster_id)

    ep = DEVICE_REGISTRY.resolve(device).endpoints[1]

    assert isinstance(ep.smartenergy_metering, ZLinkyTICMetering)
    assert ep.smartenergy_metering.get(Metering.AttributeDefs.divisor.name) == 1000
    assert isinstance(ep.zlinky_manufacturer_specific, ZLinkyTICManufacturerCluster)
    assert PowerConfiguration.cluster_id in ep.in_clusters
    assert TuyaManufCluster.cluster_id not in ep.in_clusters
    assert TuyaManufCluster.cluster_id not in ep.out_clusters


async def test_zlinky_entities():
    """Test the ZLinky_TIC entities with a ZLinky v16 on a Linky in historical mode."""
    diagnostics = json.loads((DEVICES_DIR / ZLINKY_DIAGNOSTICS).read_text())
    ieee = diagnostics["ieee"]

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, ZLINKY_DIAGNOSTICS, DEVICE_REGISTRY
        )
        unique_ids = {entity.unique_id for entity in device.platform_entities.values()}

        # entities created before the migration to quirks v2 are kept
        for entities in diagnostics["zha_lib_entities"].values():
            for entity in entities:
                assert entity["unique_id"] in unique_ids

        cluster = device.device.endpoints[1].zlinky_manufacturer_specific
        for message in (
            ZCL_TARIFF_OPTION,
            ZCL_TARIFF_PERIOD,
            ZCL_TOMORROW_COLOR,
            ZCL_LINKY_MODE,
        ):
            _, rsp = cluster.deserialize(message)
            for record in rsp.status_records:
                cluster._update_attribute(record.attrid, record.value.value)

        attrs = ZLinkyTICManufacturerCluster.AttributeDefs
        for attribute, value in (
            (attrs.linky_tariff_period, "HPJB"),
            (attrs.hist_tomorrow_color, "----"),
            # sent padded with 12 NUL bytes
            (attrs.hist_tariff_option_or_std_supplier_price_schedule_name, "BBR("),
            (attrs.linky_mode, LinkyMode.Historical_single_phase.name),
        ):
            entity = device.get_platform_entity(
                Platform.SENSOR, unique_id=f"{ieee}-1-{attribute.name}"
            )
            assert entity.native_value == value
            # Home Assistant rejects text states for sensors expecting numbers
            assert entity.suggested_display_precision is None
            assert entity.state_class is None

        # tariff period and tomorrow color are only sent with reporting configured
        reported = {
            attr_id
            for call in cluster.configure_reporting_multiple.await_args_list
            for attr_id in call.args[0]
        }
        assert {cluster.find_attribute(attr_id).name for attr_id in reported} == {
            attrs.linky_tariff_period.name,
            attrs.hist_tomorrow_color.name,
        }
