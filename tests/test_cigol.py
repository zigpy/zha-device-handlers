"""Tests for Cigol Electronics quirks."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.application.helpers import CoordinatorConfiguration, ZHAConfiguration, ZHAData
from zha.zigbee.device import Device as ZHADevice, ZHAEvent
from zigpy.profiles import zha
from zigpy.zcl import AttributeUpdatedEvent, ClusterType
from zigpy.zcl.clusters.general import MultistateInput, OnOff
from zigpy.zcl.foundation import Status

import zhaquirks
from zhaquirks.builder.metadata import ZCLSensorMetadata
from zhaquirks.cigol.connect import (
    CIGOL_CONNECT_QUIRK,
    INPUT_ENDPOINT_NAMES,
    INPUT_REPORTING_CHANGE,
    INPUT_REPORTING_MAX_INTERVAL,
    INPUT_REPORTING_MIN_INTERVAL,
    MANUFACTURER,
    MODEL,
    OUTPUT_ENDPOINT_NAMES,
    PORT_A_INPUT_ENDPOINT_NAMES,
    PORT_A_OUTPUT_ENDPOINT_NAMES,
    PORT_B_INPUT_ENDPOINT_NAMES,
    PORT_B_OUTPUT_ENDPOINT_NAMES,
    PRESS_TYPES,
    CigolConnectDevice,
    CigolMultistateInputCluster,
    present_value_to_action,
)
from zhaquirks.const import LONG_RELEASE, SHORT_PRESS

zhaquirks.setup()


def make_cluster_ids(input_endpoints, output_endpoints):
    """Build endpoint cluster metadata for a mocked Connect device."""
    return {
        **{
            endpoint: {MultistateInput.cluster_id: ClusterType.Server}
            for endpoint in input_endpoints
        },
        **{
            endpoint: {OnOff.cluster_id: ClusterType.Server}
            for endpoint in output_endpoints
        },
    }


@pytest.fixture
def connect_device(zigpy_device_from_v2_quirk):
    """Return a Connect device matching the supplied ZHA diagnostics."""
    return zigpy_device_from_v2_quirk(
        MANUFACTURER,
        MODEL,
        endpoint_ids=[],
        cluster_ids=make_cluster_ids(
            PORT_A_INPUT_ENDPOINT_NAMES, PORT_B_OUTPUT_ENDPOINT_NAMES
        ),
    )


def test_connect_dynamic_endpoint_handling(zigpy_device_from_v2_quirk):
    """The quirk only changes endpoints that the interviewed device exposes."""
    device = zigpy_device_from_v2_quirk(
        MANUFACTURER,
        MODEL,
        endpoint_ids=[],
        cluster_ids=make_cluster_ids((1, 11), (51,)),
    )

    assert isinstance(device, CigolConnectDevice)
    assert {endpoint.endpoint_id for endpoint in device.non_zdo_endpoints} == {
        1,
        11,
        51,
    }
    assert isinstance(device.endpoints[1].multistate_input, CigolMultistateInputCluster)
    assert isinstance(
        device.endpoints[11].multistate_input, CigolMultistateInputCluster
    )
    assert device.endpoints[51].profile_id == zha.PROFILE_ID
    assert device.endpoints[51].device_type == zha.DeviceType.ON_OFF_OUTPUT


def test_connect_automation_triggers(connect_device):
    """All known input endpoints expose four automation trigger types."""
    triggers = connect_device.device_automation_triggers

    assert len(triggers) == len(PORT_A_INPUT_ENDPOINT_NAMES) * len(PRESS_TYPES)
    assert triggers[(SHORT_PRESS, "input_a_1")] == {
        "command": "single",
        "endpoint_id": 1,
    }
    assert triggers[(LONG_RELEASE, "input_a_18")] == {
        "command": "release",
        "endpoint_id": 18,
    }


@pytest.mark.parametrize(
    ("value", "command"),
    (
        (0, "release"),
        (1, "single"),
        (2, "double"),
        (4, "hold"),
    ),
)
def test_connect_input_events(connect_device, value, command):
    """Present-value reports are converted into named ZHA events."""
    cluster = connect_device.endpoints[1].multistate_input
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    attr_listener = mock.Mock()
    cluster.on_event(AttributeUpdatedEvent.event_type, attr_listener)
    cluster.update_attribute(MultistateInput.AttributeDefs.present_value.id, value)

    listener.zha_send_event.assert_called_once_with(command, {"value": value})
    assert attr_listener.call_count == 1


@pytest.mark.parametrize("value", (3, 99))
def test_connect_unknown_input_value_is_ignored(connect_device, value):
    """Unknown input values update the cache without generating a button event."""
    cluster = connect_device.endpoints[1].multistate_input
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(MultistateInput.AttributeDefs.present_value.id, value)

    listener.zha_send_event.assert_not_called()


@pytest.mark.parametrize(
    ("value", "state"),
    ((0, "release"), (1, "single"), (2, "double"), (4, "hold"), (3, "unknown_3")),
)
def test_connect_action_sensor_converter(value, state):
    """The visible action sensors use readable states."""
    assert present_value_to_action(value) == state


def test_connect_input_sensor_metadata():
    """Every known input creates a visible action sensor."""
    sensor_metadata = (
        CIGOL_CONNECT_QUIRK.zha_device_factory.quirk_definition.entity_metadata
    )

    assert len(sensor_metadata) == len(INPUT_ENDPOINT_NAMES)
    for metadata in sensor_metadata:
        assert isinstance(metadata, ZCLSensorMetadata)
        assert metadata.cluster_id == MultistateInput.cluster_id
        assert metadata.attribute_name == (
            MultistateInput.AttributeDefs.present_value.name
        )
        assert metadata.reporting_config is None


@pytest.mark.asyncio
async def test_connect_explicit_input_binding_and_reporting(connect_device):
    """The custom cluster explicitly binds and configures present-value reporting."""
    cluster = connect_device.endpoints[1].multistate_input
    cluster.bind = mock.AsyncMock(return_value=(Status.SUCCESS,))
    cluster.configure_reporting = mock.AsyncMock(
        return_value={MultistateInput.AttributeDefs.present_value: Status.SUCCESS}
    )

    await cluster.apply_custom_configuration()

    cluster.bind.assert_awaited_once_with()
    cluster.configure_reporting.assert_awaited_once_with(
        MultistateInput.AttributeDefs.present_value,
        INPUT_REPORTING_MIN_INTERVAL,
        INPUT_REPORTING_MAX_INTERVAL,
        INPUT_REPORTING_CHANGE,
    )


def test_connect_zha_discovers_action_sensors_and_triggers(connect_device):
    """The ZHA layer discovers sensors/triggers and forwards input reports."""
    for endpoint in connect_device.non_zdo_endpoints:
        endpoint.profile_id = zha.PROFILE_ID

    gateway = mock.Mock()
    gateway.config = ZHAData(
        config=ZHAConfiguration(
            coordinator_configuration=CoordinatorConfiguration(path="/dev/null")
        )
    )

    zha_device = ZHADevice.new(connect_device, gateway)
    zha_device._discover_new_entities()

    action_sensors = [
        entity
        for entity in zha_device._discovered_entities
        if entity.PLATFORM is Platform.SENSOR
        and entity.cluster.cluster_id == MultistateInput.cluster_id
    ]

    assert len(action_sensors) == len(PORT_A_INPUT_ENDPOINT_NAMES)
    assert len(zha_device.device_automation_triggers) == (
        len(PORT_A_INPUT_ENDPOINT_NAMES) * len(PRESS_TYPES) + 1
    )

    event_listener = mock.Mock()
    zha_device.on_event(ZHAEvent.event_type, event_listener)
    connect_device.endpoints[1].multistate_input.update_attribute(
        MultistateInput.AttributeDefs.present_value.id, 1
    )

    event_listener.assert_called_once()
    event = event_listener.call_args.args[0]
    assert event.data["endpoint_id"] == 1
    assert event.data["cluster_id"] == MultistateInput.cluster_id
    assert event.data["command"] == "single"
    assert event.data["args"] == {"value": 1}


def test_connect_port_b_outputs_are_switch_outputs(connect_device):
    """The eight Port B outputs are classified as on/off outputs."""
    for endpoint in range(51, 59):
        assert connect_device.endpoints[endpoint].device_type == (
            zha.DeviceType.ON_OFF_OUTPUT
        )
        assert OUTPUT_ENDPOINT_NAMES[endpoint] == f"Output B.{endpoint - 50}"


@pytest.mark.parametrize(
    ("input_endpoints", "output_endpoints"),
    (
        pytest.param(
            PORT_A_INPUT_ENDPOINT_NAMES,
            PORT_B_OUTPUT_ENDPOINT_NAMES,
            id="a-input-b-output",
        ),
        pytest.param(
            PORT_B_INPUT_ENDPOINT_NAMES,
            PORT_A_OUTPUT_ENDPOINT_NAMES,
            id="a-output-b-input",
        ),
        pytest.param(
            INPUT_ENDPOINT_NAMES,
            {},
            id="a-input-b-input",
        ),
        pytest.param(
            {},
            OUTPUT_ENDPOINT_NAMES,
            id="a-output-b-output",
        ),
    ),
)
def test_connect_all_port_combinations(
    zigpy_device_from_v2_quirk, input_endpoints, output_endpoints
):
    """All four advertised port combinations select the correct quirk profile."""
    device = zigpy_device_from_v2_quirk(
        MANUFACTURER,
        MODEL,
        endpoint_ids=[],
        cluster_ids=make_cluster_ids(input_endpoints, output_endpoints),
    )

    assert isinstance(device, CigolConnectDevice)

    for endpoint in input_endpoints:
        assert isinstance(
            device.endpoints[endpoint].multistate_input,
            CigolMultistateInputCluster,
        )

    for endpoint in output_endpoints:
        assert device.endpoints[endpoint].device_type == zha.DeviceType.ON_OFF_OUTPUT

    triggers = getattr(device, "device_automation_triggers", {})
    assert len(triggers) == len(input_endpoints) * len(PRESS_TYPES)
    assert {trigger["endpoint_id"] for trigger in triggers.values()} == set(
        input_endpoints
    )

    entry = device._quirk_registry_entry
    definition = entry.zha_device_factory.quirk_definition
    assert len(definition.entity_metadata) == len(INPUT_ENDPOINT_NAMES)
    assert len(definition.changed_entity_metadata) == len(OUTPUT_ENDPOINT_NAMES)

    for endpoint in device.non_zdo_endpoints:
        endpoint.profile_id = zha.PROFILE_ID

    gateway = mock.Mock()
    gateway.config = ZHAData(
        config=ZHAConfiguration(
            coordinator_configuration=CoordinatorConfiguration(path="/dev/null")
        )
    )
    zha_device = ZHADevice.new(device, gateway)
    zha_device._discover_new_entities()

    action_sensors = [
        entity
        for entity in zha_device._discovered_entities
        if entity.PLATFORM is Platform.SENSOR
        and entity.cluster.cluster_id == MultistateInput.cluster_id
    ]
    assert len(action_sensors) == len(input_endpoints)
    assert len(zha_device.device_automation_triggers) == (
        len(input_endpoints) * len(PRESS_TYPES) + 1
    )


def test_connect_reversed_profile_endpoint_names():
    """The hardware-verified reversed profile uses the correct endpoint ranges."""
    assert {
        endpoint: f"Output A.{endpoint - 20}" for endpoint in range(21, 29)
    } == PORT_A_OUTPUT_ENDPOINT_NAMES
    assert {
        **{endpoint: f"input_b_{endpoint - 30}" for endpoint in range(31, 39)},
        **{endpoint: f"input_b_{endpoint - 30}" for endpoint in range(41, 49)},
    } == PORT_B_INPUT_ENDPOINT_NAMES


def test_connect_reversed_profile_entity_names(zigpy_device_from_v2_quirk):
    """ZHA exposes all reversed-profile inputs and named Port A outputs."""
    device = zigpy_device_from_v2_quirk(
        MANUFACTURER,
        MODEL,
        endpoint_ids=[],
        cluster_ids=make_cluster_ids(
            PORT_B_INPUT_ENDPOINT_NAMES,
            PORT_A_OUTPUT_ENDPOINT_NAMES,
        ),
    )

    for endpoint in device.non_zdo_endpoints:
        endpoint.profile_id = zha.PROFILE_ID

    gateway = mock.Mock()
    gateway.config = ZHAData(
        config=ZHAConfiguration(
            coordinator_configuration=CoordinatorConfiguration(path="/dev/null")
        )
    )
    zha_device = ZHADevice.new(device, gateway)
    zha_device._discover_new_entities()

    action_sensors = {
        entity.endpoint.id: entity.fallback_name
        for entity in zha_device._discovered_entities
        if entity.PLATFORM is Platform.SENSOR
        and entity.cluster.cluster_id == MultistateInput.cluster_id
    }
    switches = {
        entity.endpoint.id: entity.fallback_name
        for entity in zha_device._discovered_entities
        if entity.PLATFORM is Platform.SWITCH
        and entity.cluster.cluster_id == OnOff.cluster_id
    }

    assert action_sensors == {
        **{endpoint: f"Input B.{endpoint - 30} action" for endpoint in range(31, 39)},
        **{endpoint: f"Input B.{endpoint - 30} action" for endpoint in range(41, 49)},
    }
    assert switches == {
        endpoint: f"Output A.{endpoint - 20}" for endpoint in range(21, 29)
    }
