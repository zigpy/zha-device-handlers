"""Tests for the Danfoss Icon2 main controller quirk."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import AttributeUnsupportedEvent, ClusterType
from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

import zhaquirks
from zhaquirks.danfoss.icon2 import (
    CONTROLLER_ENDPOINT,
    DanfossIcon2DiagnosticCluster,
    DanfossIcon2ThermostatCluster,
    DanfossOutputStatus,
    DanfossSystemStatusWater,
)

zhaquirks.setup()

ZONE_CLUSTERS = {
    Basic.cluster_id: ClusterType.Server,
    Identify.cluster_id: ClusterType.Server,
    Thermostat.cluster_id: ClusterType.Server,
    UserInterface.cluster_id: ClusterType.Server,
    TemperatureMeasurement.cluster_id: ClusterType.Server,
    RelativeHumidity.cluster_id: ClusterType.Server,
    Diagnostic.cluster_id: ClusterType.Server,
}

CONTROLLER_CLUSTERS = {
    Basic.cluster_id: ClusterType.Server,
    Identify.cluster_id: ClusterType.Server,
    Diagnostic.cluster_id: ClusterType.Server,
}


def _icon2(zigpy_device_from_v2_quirk, model="0x0210", zones=(1, 2, 3, 4, 5)):
    """Create an Icon2 controller with the given zone endpoints."""
    cluster_ids = {zone: dict(ZONE_CLUSTERS) for zone in zones}
    cluster_ids[CONTROLLER_ENDPOINT] = dict(CONTROLLER_CLUSTERS)
    return zigpy_device_from_v2_quirk("Danfoss", model, cluster_ids=cluster_ids)


@pytest.mark.parametrize("model", ["0x0210", "0x0211"])
def test_icon2_clusters_replaced(zigpy_device_from_v2_quirk, model):
    """Every zone and the controller endpoint get the Danfoss clusters."""
    device = _icon2(zigpy_device_from_v2_quirk, model=model)

    for zone in range(1, 6):
        assert isinstance(
            device.endpoints[zone].thermostat, DanfossIcon2ThermostatCluster
        )
    assert isinstance(
        device.endpoints[CONTROLLER_ENDPOINT].diagnostic,
        DanfossIcon2DiagnosticCluster,
    )


def test_icon2_missing_zones_are_skipped(zigpy_device_from_v2_quirk):
    """A controller with fewer rooms only has those zone endpoints."""
    device = _icon2(zigpy_device_from_v2_quirk, zones=(1, 2))

    assert isinstance(device.endpoints[1].thermostat, DanfossIcon2ThermostatCluster)
    assert isinstance(device.endpoints[2].thermostat, DanfossIcon2ThermostatCluster)
    assert 3 not in device.endpoints


def test_icon2_all_fifteen_zones(zigpy_device_from_v2_quirk):
    """A fully configured controller has 15 zones."""
    device = _icon2(zigpy_device_from_v2_quirk, zones=range(1, 16))

    for zone in range(1, 16):
        assert isinstance(
            device.endpoints[zone].thermostat, DanfossIcon2ThermostatCluster
        )


def _entity_endpoints(device):
    """Return the endpoints with a zone heat binary sensor."""
    entry = DEVICE_REGISTRY.match_entry(device)
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    assert all(
        m.cluster_id == Thermostat.cluster_id and m.attribute_name == "output_status"
        for m in metadata
    )
    return [m.endpoint_id for m in metadata]


def test_icon2_entities(zigpy_device_from_v2_quirk):
    """A heat binary sensor is declared for every possible zone."""
    device = _icon2(zigpy_device_from_v2_quirk)

    assert _entity_endpoints(device) == list(range(1, 16))


def test_icon2_controller_endpoint_has_no_thermostat(zigpy_device_from_v2_quirk):
    """The controller endpoint keeps its clusters and gets no Thermostat."""
    device = _icon2(zigpy_device_from_v2_quirk)

    assert (
        Thermostat.cluster_id not in device.endpoints[CONTROLLER_ENDPOINT].in_clusters
    )


@pytest.mark.parametrize(
    "output_status, running_state",
    [
        (DanfossOutputStatus.Active, Thermostat.RunningState.Heat_State_On),
        (DanfossOutputStatus.Inactive, Thermostat.RunningState.Idle),
    ],
)
def test_icon2_running_state_from_output_status(
    zigpy_device_from_v2_quirk, output_status, running_state
):
    """The output status is mirrored into running_state."""
    device = _icon2(zigpy_device_from_v2_quirk)
    thermostat = device.endpoints[3].thermostat

    thermostat.update_attribute(
        DanfossIcon2ThermostatCluster.AttributeDefs.output_status.id, output_status
    )

    assert thermostat.get("output_status") == output_status
    assert thermostat.get("running_state") == running_state
    # Other zones are not affected
    assert device.endpoints[2].thermostat.get("running_state") is None


def test_icon2_running_state_kept_when_unsupported(zigpy_device_from_v2_quirk):
    """An unsupported read of running_state keeps the derived value."""
    device = _icon2(zigpy_device_from_v2_quirk)
    thermostat = device.endpoints[1].thermostat

    thermostat.update_attribute(
        DanfossIcon2ThermostatCluster.AttributeDefs.output_status.id,
        DanfossOutputStatus.Active,
    )
    thermostat._on_attribute_unsupported(
        AttributeUnsupportedEvent(
            device_ieee=str(device.ieee),
            endpoint_id=1,
            cluster_type=ClusterType.Server,
            cluster_id=Thermostat.cluster_id,
            attribute_name="running_state",
            attribute_id=Thermostat.AttributeDefs.running_state.id,
            manufacturer_code=None,
        )
    )

    assert thermostat.get("running_state") == Thermostat.RunningState.Heat_State_On


def test_icon2_manufacturer_specific_attributes():
    """The Danfoss attributes are manufacturer specific, standard ones are not."""
    zone_attrs = DanfossIcon2ThermostatCluster.AttributeDefs
    assert zone_attrs.output_status.is_manufacturer_specific
    assert zone_attrs.room_status_code.is_manufacturer_specific
    assert not zone_attrs.running_state.is_manufacturer_specific

    controller_attrs = DanfossIcon2DiagnosticCluster.AttributeDefs
    assert controller_attrs.heat_supply_request.is_manufacturer_specific


def test_icon2_running_state_cooling(zigpy_device_from_v2_quirk):
    """Active zones show cooling while the controller reports cool water flow."""
    device = _icon2(zigpy_device_from_v2_quirk)
    diagnostic = device.endpoints[CONTROLLER_ENDPOINT].diagnostic
    zone1 = device.endpoints[1].thermostat
    zone2 = device.endpoints[2].thermostat
    output_status = DanfossIcon2ThermostatCluster.AttributeDefs.output_status.id
    water = DanfossIcon2DiagnosticCluster.AttributeDefs.system_status_water.id

    diagnostic.update_attribute(water, DanfossSystemStatusWater.Cool_Water_Flow)
    zone1.update_attribute(output_status, DanfossOutputStatus.Active)
    zone2.update_attribute(output_status, DanfossOutputStatus.Inactive)
    assert zone1.get("running_state") == Thermostat.RunningState.Cool_State_On
    assert zone2.get("running_state") == Thermostat.RunningState.Idle

    # Switching to hot water updates the zones that are already active
    diagnostic.update_attribute(water, DanfossSystemStatusWater.Hot_Water_Flow)
    assert zone1.get("running_state") == Thermostat.RunningState.Heat_State_On
    assert zone2.get("running_state") == Thermostat.RunningState.Idle
