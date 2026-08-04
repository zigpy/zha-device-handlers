"""Tests for Nous quirks."""

from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR, SE_POLL_SUMMATION, TUYA_PLUG_ONOFF
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks

zhaquirks.setup()


def _a4z_device(zigpy_device_from_v2_quirk):
    """Create a Nous A4Z, which reports metering on both of its endpoints."""
    endpoint = {
        OnOff.cluster_id: ClusterType.Server,
        Metering.cluster_id: ClusterType.Server,
        ElectricalMeasurement.cluster_id: ClusterType.Server,
    }
    return zigpy_device_from_v2_quirk(
        manufacturer="_TZ3000_uwkja6z1",
        model="TS011F",
        cluster_ids={1: dict(endpoint), 2: dict(endpoint)},
    )


def _exposed_features(device):
    """Return the feature strings the applied quirk exposes to ZHA."""
    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    quirk_definition = entry.zha_device_factory.quirk_definition
    return {f.feature for f in quirk_definition.exposes_features}


def test_nous_a4z_measurement_scaling(zigpy_device_from_v2_quirk):
    """Test the multipliers and divisors the socket never reports are served."""
    device = _a4z_device(zigpy_device_from_v2_quirk)

    metering = device.endpoints[1].smartenergy_metering
    assert metering.get(Metering.AttributeDefs.multiplier.id) == 1
    assert metering.get(Metering.AttributeDefs.divisor.id) == 100

    electrical = device.endpoints[1].electrical_measurement
    assert (
        electrical.get(ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id)
        == 1
    )
    assert (
        electrical.get(ElectricalMeasurement.AttributeDefs.ac_current_divisor.id)
        == 1000
    )


def test_nous_a4z_duplicate_measurement_removed(zigpy_device_from_v2_quirk):
    """Test endpoint 2's duplicate measurement is dropped but its relay kept."""
    device = _a4z_device(zigpy_device_from_v2_quirk)

    assert Metering.cluster_id not in device.endpoints[2].in_clusters
    assert ElectricalMeasurement.cluster_id not in device.endpoints[2].in_clusters
    assert OnOff.cluster_id in device.endpoints[2].in_clusters


def test_nous_a4z_tuya_onoff_attributes(zigpy_device_from_v2_quirk):
    """Test the Tuya OnOff extras are exposed, on endpoint 1 only."""
    device = _a4z_device(zigpy_device_from_v2_quirk)

    on_off = device.endpoints[1].on_off
    for attribute_name in ("power_on_state", "backlight_mode", "child_lock"):
        assert attribute_name in on_off.attributes_by_name

    # One socket-wide register mirrored on both endpoints, so endpoint 2 keeps a
    # plain OnOff cluster rather than exposing a second set of the same settings.
    assert "power_on_state" not in device.endpoints[2].on_off.attributes_by_name

    assert TUYA_PLUG_ONOFF in _exposed_features(device)


def test_nous_a4z_summation_is_polled(zigpy_device_from_v2_quirk):
    """Test the summation poll survives the friendly name renaming the model.

    ZHA only creates its Metering poller for a model allowlist that TS011F is on,
    and this socket does not report summation on its own, so renaming the model
    via friendly_name has to be paired with asking for the poll explicitly.
    """
    device = _a4z_device(zigpy_device_from_v2_quirk)

    assert SE_POLL_SUMMATION in _exposed_features(device)
