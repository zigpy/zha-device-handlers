"""Tests for Tuya no neutral switches."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ReportingConfig
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import Status

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.tuya import TuyaZBOnOffAttributeCluster
import zhaquirks.tuya.ts001x
from zhaquirks.tuya.ts001x import TuyaNoNeutralOnOffCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "quirk",
    (
        zhaquirks.tuya.ts001x.TuyaSingleNoNeutralSwitch,
        zhaquirks.tuya.ts001x.TuyaDoubleNoNeutralSwitch,
        zhaquirks.tuya.ts001x.TuyaTripleNoNeutralSwitch,
        zhaquirks.tuya.ts001x.TuyaSingleNoNeutralSwitch_2,
        zhaquirks.tuya.ts001x.TuyaDoubleNoNeutralSwitch_2,
        zhaquirks.tuya.ts001x.TuyaTripleNoNeutralSwitch_2,
    ),
)
async def test_no_neutral_switch_skips_reporting(zigpy_device_from_quirk, quirk):
    """Test that the no neutral switches never configure On/Off reporting."""
    device = zigpy_device_from_quirk(quirk)

    on_off_clusters = [
        endpoint.in_clusters[OnOff.cluster_id]
        for endpoint_id, endpoint in device.endpoints.items()
        if endpoint_id != 0 and OnOff.cluster_id in endpoint.in_clusters
    ]
    assert on_off_clusters

    for cluster in on_off_clusters:
        assert isinstance(cluster, TuyaNoNeutralOnOffCluster)
        assert isinstance(cluster, TuyaZBOnOffAttributeCluster)

        with mock.patch.object(
            cluster, "_configure_reporting", mock.AsyncMock()
        ) as configure_reporting:
            result = await cluster.configure_reporting_multiple(
                {
                    OnOff.AttributeDefs.on_off: ReportingConfig(
                        min_interval=0, max_interval=900, reportable_change=1
                    )
                }
            )

        configure_reporting.assert_not_awaited()
        assert result == {OnOff.AttributeDefs.on_off: Status.UNREPORTABLE_ATTRIBUTE}


async def test_no_neutral_switch_zha_configuration():
    """Test that ZHA still binds On/Off but sends no reporting configuration."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "tz3000-idhkkbqj-ts0012-0x00000041.json", DEVICE_REGISTRY
        )
        zigpy_device = device.device

        on_off_clusters = [
            zigpy_device.endpoints[endpoint_id].in_clusters[OnOff.cluster_id]
            for endpoint_id in (1, 2)
        ]

        for cluster in on_off_clusters:
            assert type(cluster) is TuyaNoNeutralOnOffCluster
            # the diagnostics helper mocks reporting on the instance, use the quirk's
            del cluster.configure_reporting_multiple
            cluster._configure_reporting = mock.AsyncMock()
            cluster.bind.reset_mock()

        await device.async_configure()

        for cluster in on_off_clusters:
            cluster.bind.assert_awaited_once()
            cluster._configure_reporting.assert_not_awaited()
