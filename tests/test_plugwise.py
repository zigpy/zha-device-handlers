"""Tests for the Plugwise quirks."""

from unittest import mock

import pytest
from zigpy.zcl import Cluster, ClusterType, ReportingConfig
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

import zhaquirks
from zhaquirks.plugwise.emma import (
    EMMA_ZHA_SUPPORT_FW_VERSION,
    EmmaHumidityClusterClamped,
    EmmaPowerConfigCluster,
    EmmaPowerConfigClusterClamped,
    EmmaThermostatCluster,
    EmmaThermostatClusterClamped,
)

zhaquirks.setup()

EMMA_CLUSTER_IDS = {
    1: {
        PowerConfiguration.cluster_id: ClusterType.Server,
        Thermostat.cluster_id: ClusterType.Server,
        RelativeHumidity.cluster_id: ClusterType.Server,
        TemperatureMeasurement.cluster_id: ClusterType.Server,
    }
}

# ZHA's defaults for a climate device and a battery, which the firmware rejects
ZHA_CLIMATE_CONFIG = ReportingConfig(
    min_interval=30, max_interval=900, reportable_change=25
)
ZHA_BATTERY_CONFIG = ReportingConfig(
    min_interval=3600, max_interval=900, reportable_change=1
)


@pytest.fixture
def emma(zigpy_device_from_v2_quirk):
    """Return an Emma on firmware that enforces the reporting bounds."""
    return zigpy_device_from_v2_quirk(
        "Plugwise",
        "170-01",
        cluster_ids=EMMA_CLUSTER_IDS,
        firmware_version=EMMA_ZHA_SUPPORT_FW_VERSION,
    )


async def configured_reporting(cluster, config):
    """Return the reporting config `cluster` sends for `config`."""
    with mock.patch.object(
        Cluster, "configure_reporting_multiple", mock.AsyncMock(return_value={})
    ) as sent:
        await cluster.configure_reporting_multiple(config)
    return sent.mock_calls[0].args[0]


async def test_emma_thermostat_restricted_intervals(emma) -> None:
    """Test the restricted thermostat attributes are reported within the firmware bounds."""
    cluster = emma.endpoints[1].in_clusters[Thermostat.cluster_id]
    attr_def = Thermostat.AttributeDefs.occupied_heating_setpoint

    sent = await configured_reporting(cluster, {attr_def: ZHA_CLIMATE_CONFIG})

    assert sent[attr_def] == ReportingConfig(
        min_interval=1, max_interval=870, reportable_change=25
    )


async def test_emma_thermostat_local_temperature(emma) -> None:
    """Test the local temperature is narrowed on both the intervals and the change."""
    cluster = emma.endpoints[1].in_clusters[Thermostat.cluster_id]
    attr_def = Thermostat.AttributeDefs.local_temperature

    sent = await configured_reporting(cluster, {attr_def: ZHA_CLIMATE_CONFIG})

    assert sent[attr_def] == ReportingConfig(
        min_interval=1, max_interval=870, reportable_change=10
    )


async def test_emma_thermostat_other_attributes_untouched(emma) -> None:
    """Test an attribute the firmware does not restrict keeps ZHA's configuration."""
    cluster = emma.endpoints[1].in_clusters[Thermostat.cluster_id]
    attr_def = Thermostat.AttributeDefs.outdoor_temperature

    sent = await configured_reporting(cluster, {attr_def: ZHA_CLIMATE_CONFIG})

    assert sent[attr_def] == ZHA_CLIMATE_CONFIG


@pytest.mark.parametrize(
    ("cluster_id", "change"),
    [(RelativeHumidity.cluster_id, 25), (TemperatureMeasurement.cluster_id, 10)],
)
async def test_emma_measurement_intervals_pinned(emma, cluster_id, change) -> None:
    """Test the measurement clusters report on the only intervals the firmware accepts."""
    cluster = emma.endpoints[1].in_clusters[cluster_id]
    attr_def = cluster.AttributeDefs.measured_value

    sent = await configured_reporting(cluster, {attr_def: ZHA_CLIMATE_CONFIG})

    assert sent[attr_def] == ReportingConfig(
        min_interval=1, max_interval=870, reportable_change=change
    )


async def test_emma_battery_max_interval_floor(emma) -> None:
    """Test the battery attributes are reported no more often than the firmware allows."""
    cluster = emma.endpoints[1].in_clusters[PowerConfiguration.cluster_id]
    voltage = PowerConfiguration.AttributeDefs.battery_voltage
    percentage = PowerConfiguration.AttributeDefs.battery_percentage_remaining

    sent = await configured_reporting(
        cluster, {voltage: ZHA_BATTERY_CONFIG, percentage: ZHA_BATTERY_CONFIG}
    )

    assert sent[voltage].max_interval == 65534
    assert sent[percentage].max_interval == 43200


@pytest.mark.parametrize(
    ("firmware_version", "thermostat_cls", "power_cls"),
    [
        (
            EMMA_ZHA_SUPPORT_FW_VERSION,
            EmmaThermostatClusterClamped,
            EmmaPowerConfigClusterClamped,
        ),
        (
            EMMA_ZHA_SUPPORT_FW_VERSION - 1,
            EmmaThermostatCluster,
            EmmaPowerConfigCluster,
        ),
    ],
)
def test_emma_clamping_follows_firmware_version(
    zigpy_device_from_v2_quirk, firmware_version, thermostat_cls, power_cls
) -> None:
    """Test only firmware that enforces the reporting bounds gets the clamping clusters."""
    device = zigpy_device_from_v2_quirk(
        "Plugwise",
        "170-01",
        cluster_ids=EMMA_CLUSTER_IDS,
        firmware_version=firmware_version,
    )
    endpoint = device.endpoints[1]

    assert type(endpoint.in_clusters[Thermostat.cluster_id]) is thermostat_cls
    assert type(endpoint.in_clusters[PowerConfiguration.cluster_id]) is power_cls
    assert isinstance(
        endpoint.in_clusters[RelativeHumidity.cluster_id],
        EmmaHumidityClusterClamped,
    ) is (firmware_version >= EMMA_ZHA_SUPPORT_FW_VERSION)
