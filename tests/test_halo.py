"""Tests for Halo Smart Labs smoke & CO detector quirks."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
from zhaquirks.halolabs.halo import (
    HaloAlertState,
    HaloColorCluster,
    HaloControlCluster,
    HaloHushStatus,
    HaloSensorsCluster,
    HaloStatusCluster,
    HaloTestStatus,
    HaloWeatherCluster,
    WeatherAlertCode,
)

zhaquirks.setup()


# -- Helpers to build devices with all needed endpoints & clusters --

HALO_CLUSTER_IDS = {
    1: {IasZone.cluster_id: ClusterType.Server},
    2: {Color.cluster_id: ClusterType.Server},
    3: {IasZone.cluster_id: ClusterType.Server},
    4: {
        HaloStatusCluster.cluster_id: ClusterType.Server,
        HaloControlCluster.cluster_id: ClusterType.Server,
        HaloSensorsCluster.cluster_id: ClusterType.Server,
    },
}

HALO_PLUS_CLUSTER_IDS = {
    **HALO_CLUSTER_IDS,
    5: {HaloWeatherCluster.cluster_id: ClusterType.Server},
}


# -- Quirk registration tests --


def test_halo_quirk_registered(zigpy_device_from_v2_quirk):
    """Test that the Halo quirk is registered and applied."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo",
        cluster_ids=HALO_CLUSTER_IDS,
    )
    # The device should have the custom clusters on endpoint 4
    assert HaloStatusCluster.cluster_id in device.endpoints[4].in_clusters
    assert HaloControlCluster.cluster_id in device.endpoints[4].in_clusters
    assert HaloSensorsCluster.cluster_id in device.endpoints[4].in_clusters
    # Custom cluster types should be applied
    assert isinstance(
        device.endpoints[4].in_clusters[HaloStatusCluster.cluster_id],
        HaloStatusCluster,
    )
    assert isinstance(
        device.endpoints[4].in_clusters[HaloControlCluster.cluster_id],
        HaloControlCluster,
    )
    assert isinstance(
        device.endpoints[4].in_clusters[HaloSensorsCluster.cluster_id],
        HaloSensorsCluster,
    )


def test_halo_color_cluster_constant_attributes(zigpy_device_from_v2_quirk):
    """Test that HaloColorCluster sets correct constant attributes on EP2."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo",
        cluster_ids=HALO_CLUSTER_IDS,
    )
    color_cluster = device.endpoints[2].in_clusters[Color.cluster_id]
    assert isinstance(color_cluster, HaloColorCluster)
    # Verify constant attributes are set correctly
    expected_caps = (
        Color.ColorCapabilities.Hue_and_saturation
        | Color.ColorCapabilities.XY_attributes
    )
    assert (
        color_cluster._CONSTANT_ATTRIBUTES[Color.AttributeDefs.color_capabilities.id]
        == expected_caps
    )
    assert (
        color_cluster._CONSTANT_ATTRIBUTES[Color.AttributeDefs.color_temp_physical_min.id]
        == 153
    )
    assert (
        color_cluster._CONSTANT_ATTRIBUTES[Color.AttributeDefs.color_temp_physical_max.id]
        == 500
    )


def test_halo_plus_quirk_registered(zigpy_device_from_v2_quirk):
    """Test that the Halo+ quirk is registered and applied."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo+",
        cluster_ids=HALO_PLUS_CLUSTER_IDS,
    )
    # Should have all base Halo clusters on EP4
    assert isinstance(
        device.endpoints[4].in_clusters[HaloStatusCluster.cluster_id],
        HaloStatusCluster,
    )
    # And weather cluster on EP5
    assert HaloWeatherCluster.cluster_id in device.endpoints[5].in_clusters
    assert isinstance(
        device.endpoints[5].in_clusters[HaloWeatherCluster.cluster_id],
        HaloWeatherCluster,
    )


@pytest.mark.parametrize("model", ["halo+", "haloWX", "SABDA1"])
def test_halo_plus_models(zigpy_device_from_v2_quirk, model):
    """Test that all Halo+ model variants are registered."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model=model,
        cluster_ids=HALO_PLUS_CLUSTER_IDS,
    )
    assert isinstance(
        device.endpoints[5].in_clusters[HaloWeatherCluster.cluster_id],
        HaloWeatherCluster,
    )


# -- IAS Zone zone_status attribute converter tests --


@pytest.mark.parametrize(
    "zone_status, expected_tamper, expected_battery_low, expected_test, expected_mains",
    [
        # All clear
        (0x0000, False, False, False, True),
        # Tamper only (bit 2)
        (0x0004, True, False, False, True),
        # Battery low only (bit 3)
        (0x0008, False, True, False, True),
        # Test mode only (bit 8)
        (0x0100, False, False, True, True),
        # AC mains fault (bit 7) — mains_power should be False
        (0x0080, False, False, False, False),
        # Multiple bits: smoke + tamper + battery + AC fault + test
        (0x019D, True, True, True, False),
    ],
)
def test_ias_zone_status_converters(
    zone_status,
    expected_tamper,
    expected_battery_low,
    expected_test,
    expected_mains,
):
    """Test IAS Zone zone_status bit extraction converters."""
    # Tamper (bit 2)
    assert bool(zone_status & IasZone.ZoneStatus.Tamper) == expected_tamper
    # Battery (bit 3)
    assert bool(zone_status & IasZone.ZoneStatus.Battery) == expected_battery_low
    # Test (bit 8)
    assert bool(zone_status & IasZone.ZoneStatus.Test) == expected_test
    # AC mains (bit 7), inverted for "mains connected"
    assert (not bool(zone_status & IasZone.ZoneStatus.AC_mains)) == expected_mains


# -- Halo status cluster attribute tests --


def test_halo_alert_state_enum():
    """Test HaloAlertState enum values match the device protocol."""
    assert int(HaloAlertState.Safe) == 0x00
    assert int(HaloAlertState.Low_battery) == 0x01
    assert int(HaloAlertState.End_of_life) == 0x02
    assert int(HaloAlertState.Pre_smoke) == 0x04
    assert int(HaloAlertState.Weather) == 0x05
    assert int(HaloAlertState.Carbon_monoxide) == 0x06
    assert int(HaloAlertState.Smoke) == 0x07
    assert int(HaloAlertState.Other) == 0x08
    assert int(HaloAlertState.Silenced) == 0x09
    assert int(HaloAlertState.Very_low_battery) == 0x0A
    assert int(HaloAlertState.Failed_battery) == 0x0B
    assert int(HaloAlertState.CO_test) == 0x0E
    assert int(HaloAlertState.Smoke_test) == 0x10
    assert int(HaloAlertState.Interconnect_CO) == 0x12
    assert int(HaloAlertState.Interconnect_smoke) == 0x13


def test_halo_status_cluster_attributes():
    """Test HaloStatusCluster attribute definitions."""
    assert HaloStatusCluster.cluster_id == 0xFD00
    assert HaloStatusCluster.AttributeDefs.device_status.id == 0x0000
    assert HaloStatusCluster.AttributeDefs.room.id == 0x0002


def test_halo_control_cluster_attributes():
    """Test HaloControlCluster attribute and command definitions."""
    assert HaloControlCluster.cluster_id == 0xFD01
    assert HaloControlCluster.AttributeDefs.test_status.id == 0x0000
    assert HaloControlCluster.AttributeDefs.hush_status.id == 0x0001
    assert HaloControlCluster.ServerCommandDefs.halo_test.id == 0x00
    assert HaloControlCluster.ServerCommandDefs.halo_hush.id == 0x01


def test_halo_sensors_cluster_attributes():
    """Test HaloSensorsCluster attribute definitions."""
    assert HaloSensorsCluster.cluster_id == 0xFD02
    assert HaloSensorsCluster.AttributeDefs.co_ppm.id == 0x0002


def test_halo_weather_cluster_attributes():
    """Test HaloWeatherCluster attribute and command definitions."""
    assert HaloWeatherCluster.cluster_id == 0xFD03
    assert HaloWeatherCluster.AttributeDefs.weather_alert_status.id == 0x0000
    assert HaloWeatherCluster.AttributeDefs.weather_mute.id == 0x0001
    assert HaloWeatherCluster.AttributeDefs.weather_location.id == 0x0002
    assert HaloWeatherCluster.AttributeDefs.weather_event1.id == 0x0003
    assert HaloWeatherCluster.AttributeDefs.weather_event2.id == 0x0004
    assert HaloWeatherCluster.AttributeDefs.weather_event3.id == 0x0005
    assert HaloWeatherCluster.AttributeDefs.weather_station.id == 0x0006
    assert HaloWeatherCluster.ServerCommandDefs.weather_scan.id == 0x00
    assert HaloWeatherCluster.ServerCommandDefs.weather_radio_play.id == 0x03


# -- Derived binary sensor converter tests --


@pytest.mark.parametrize(
    "alert_state, expected_weather_alert",
    [
        (HaloAlertState.Safe, False),
        (HaloAlertState.Weather, True),
        (HaloAlertState.Smoke, False),
        (HaloAlertState.Carbon_monoxide, False),
    ],
)
def test_weather_alert_converter(alert_state, expected_weather_alert):
    """Test that weather_alert binary sensor correctly derives from device_status."""
    assert (alert_state == HaloAlertState.Weather) == expected_weather_alert


@pytest.mark.parametrize(
    "test_status, expected_in_progress",
    [
        (HaloTestStatus.Success, False),
        (HaloTestStatus.Running, True),
        (HaloTestStatus.Fail_ion, False),
        (HaloTestStatus.Fail_other, False),
    ],
)
def test_test_in_progress_converter(test_status, expected_in_progress):
    """Test that test_in_progress correctly derives from test_status."""
    assert (test_status == HaloTestStatus.Running) == expected_in_progress


@pytest.mark.parametrize(
    "hush_status, expected_active",
    [
        (HaloHushStatus.Ready, False),
        (HaloHushStatus.Success, True),
        (HaloHushStatus.Timeout, False),
        (HaloHushStatus.Disabled, False),
    ],
)
def test_hush_active_converter(hush_status, expected_active):
    """Test that hush_active correctly derives from hush_status."""
    assert (hush_status == HaloHushStatus.Success) == expected_active


# -- Weather alert code enum tests --


def test_weather_alert_code_enum():
    """Test WeatherAlertCode enum covers key alert types."""
    assert int(WeatherAlertCode.NONE) == 0x00
    assert int(WeatherAlertCode.TOR) == 0x1B
    assert int(WeatherAlertCode.SVR) == 0x18
    assert int(WeatherAlertCode.HUW) == 0x13
    assert int(WeatherAlertCode.SSW) == 0x50


# -- Cluster update_attribute tests --


def test_halo_status_update_attribute(zigpy_device_from_v2_quirk):
    """Test that device_status attribute updates are properly handled."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo",
        cluster_ids=HALO_CLUSTER_IDS,
    )
    cluster = device.endpoints[4].in_clusters[HaloStatusCluster.cluster_id]

    # Simulate attribute report for device_status
    cluster.update_attribute(
        HaloStatusCluster.AttributeDefs.device_status.id,
        HaloAlertState.Smoke,
    )
    assert (
        cluster.get(HaloStatusCluster.AttributeDefs.device_status.id)
        == HaloAlertState.Smoke
    )


def test_halo_control_update_attribute(zigpy_device_from_v2_quirk):
    """Test that control cluster attribute updates are properly handled."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo",
        cluster_ids=HALO_CLUSTER_IDS,
    )
    cluster = device.endpoints[4].in_clusters[HaloControlCluster.cluster_id]

    # Test status
    cluster.update_attribute(
        HaloControlCluster.AttributeDefs.test_status.id,
        HaloTestStatus.Running,
    )
    assert (
        cluster.get(HaloControlCluster.AttributeDefs.test_status.id)
        == HaloTestStatus.Running
    )

    # Hush status
    cluster.update_attribute(
        HaloControlCluster.AttributeDefs.hush_status.id,
        HaloHushStatus.Success,
    )
    assert (
        cluster.get(HaloControlCluster.AttributeDefs.hush_status.id)
        == HaloHushStatus.Success
    )


def test_halo_sensors_update_attribute(zigpy_device_from_v2_quirk):
    """Test that CO PPM attribute updates are properly handled."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo",
        cluster_ids=HALO_CLUSTER_IDS,
    )
    cluster = device.endpoints[4].in_clusters[HaloSensorsCluster.cluster_id]

    cluster.update_attribute(
        HaloSensorsCluster.AttributeDefs.co_ppm.id,
        42,
    )
    assert cluster.get(HaloSensorsCluster.AttributeDefs.co_ppm.id) == 42


def test_halo_weather_update_attribute(zigpy_device_from_v2_quirk):
    """Test that weather cluster attribute updates are properly handled."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="Halo Smart Labs",
        model="halo+",
        cluster_ids=HALO_PLUS_CLUSTER_IDS,
    )
    cluster = device.endpoints[5].in_clusters[HaloWeatherCluster.cluster_id]

    # Weather alert status
    cluster.update_attribute(
        HaloWeatherCluster.AttributeDefs.weather_alert_status.id,
        WeatherAlertCode.TOR,
    )
    assert (
        cluster.get(HaloWeatherCluster.AttributeDefs.weather_alert_status.id)
        == WeatherAlertCode.TOR
    )

    # Weather station
    cluster.update_attribute(
        HaloWeatherCluster.AttributeDefs.weather_station.id,
        3,
    )
    assert cluster.get(HaloWeatherCluster.AttributeDefs.weather_station.id) == 3
