"""Quirks v2 builder-mechanics tests migrated from zigpy."""

import logging
from typing import Any
from unittest.mock import AsyncMock, sentinel

from frozendict import frozendict
import pytest
from zha.quirks import DeviceRegistry
from zigpy.const import (
    SIG_ENDPOINTS,
    SIG_EP_INPUT,
    SIG_EP_PROFILE,
    SIG_EP_TYPE,
    SIG_MODELS_INFO,
)
from zigpy.device import Device
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    OnOff,
    PowerConfiguration,
)
from zigpy.zdo.types import LogicalType, NodeDescriptor

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.metadata import recursive_freeze
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import COMMAND, COMMAND_ON, SHORT_PRESS, TURN_ON
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.legacy import signature_matches


@pytest.fixture(name="device_mock")
def real_device(MockAppController) -> Device:
    """Device fixture with a single endpoint."""
    ieee = sentinel.ieee
    nwk = 0x2233
    device = Device(MockAppController, ieee, nwk)

    device.add_endpoint(1)
    device[1].profile_id = 255
    device[1].device_type = 255
    device.model = "model"
    device.manufacturer = "manufacturer"
    device[1].add_input_cluster(3)
    device[1].add_output_cluster(6)
    return device


def strict_eq(a: Any, b: Any) -> bool:
    """Recursively check equality and type matching."""
    if type(a) is not type(b):
        return False
    if a != b:
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(strict_eq(a[k], b[k]) for k in a)
    if isinstance(a, tuple | list):
        if len(a) != len(b):
            return False
        return all(
            strict_eq(a_item, b_item) for a_item, b_item in zip(a, b, strict=False)
        )
    return True


async def test_quirks_v2_model_manufacturer(device_mock):
    """Test the potential exceptions when model and manufacturer are set up incorrectly."""
    registry = DeviceRegistry()

    with pytest.raises(
        ValueError,
        match="At least one manufacturer and model must be specified for a v2 quirk.",
    ):
        (
            QuirkBuilder(registry=registry)
            .adds(Basic.cluster_id)
            .adds(OnOff.cluster_id)
            .enum(
                OnOff.AttributeDefs.start_up_on_off.name,
                OnOff.StartUpOnOff,
                OnOff.cluster_id,
                translation_key="start_up_on_off",
                fallback_name="Start up on/off",
            )
            .add_to_registry(registry)
        )

    with pytest.raises(
        ValueError,
        match="A manufacturer and/or model must be specified for a v2 quirk.",
    ):
        (
            QuirkBuilder(registry=registry)
            # Fails early, before we even add it to the registry
            .applies_to(manufacturer=None, model=None)  # type:ignore[call-overload]
        )


@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [
        ("manufacturer", "model"),  # has both
        ("manufacturer", None),  # missing model
        (None, "model"),  # missing manufacturer
    ],
)
async def test_quirks_v2_missing_model_manufacturer(
    MockAppController, manufacturer: str | None, model: str | None
):
    """Test that v2 quirks can match devices with missing model/manufacturer."""
    registry = DeviceRegistry()

    (
        QuirkBuilder(manufacturer, model)
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .add_to_registry(registry)
    )

    device = Device(MockAppController, sentinel.ieee, 0x2233)
    device.add_endpoint(1)
    device[1].profile_id = 255
    device[1].device_type = 255
    device[1].add_input_cluster(3)
    device[1].add_output_cluster(6)

    if manufacturer is not None:
        device.manufacturer = manufacturer

    if model is not None:
        device.model = model

    quirked = registry.resolve(device)
    assert isinstance(quirked, CustomZigpyDevice)

    entry = registry.match_entry(quirked)
    assert entry is not None

    registry.remove(entry)
    assert registry.match_entry(quirked) is None


async def test_quirks_v2_quirk_builder_cloning(device_mock):
    """Test the quirk builder clone functionality."""
    registry = DeviceRegistry()

    base = (
        QuirkBuilder(registry=registry)
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .enum(
            OnOff.AttributeDefs.start_up_on_off.name,
            OnOff.StartUpOnOff,
            OnOff.cluster_id,
            translation_key="start_up_on_off",
            fallback_name="Start up on/off",
        )
        .applies_to("foo", "bar")
    )

    cloned = base.clone()
    base.add_to_registry(registry)

    (
        cloned.adds(PowerConfiguration.cluster_id)
        .applies_to(device_mock.manufacturer, device_mock.model)
        .add_to_registry(registry)
    )

    quirked = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)
    assert (
        quirked.endpoints[1].in_clusters.get(PowerConfiguration.cluster_id) is not None
    )


async def test_quirks_v2_signature_match(device_mock):
    """Test the signature_matches filter."""
    registry = DeviceRegistry()

    signature_no_match = {
        SIG_MODELS_INFO: (("manufacturer", "model"),),
        SIG_ENDPOINTS: {
            1: {
                SIG_EP_PROFILE: 260,
                SIG_EP_TYPE: 255,
                SIG_EP_INPUT: [3],
            }
        },
    }

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .filter(signature_matches(signature_no_match))
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .enum(
            OnOff.AttributeDefs.start_up_on_off.name,
            OnOff.StartUpOnOff,
            OnOff.cluster_id,
            translation_key="start_up_on_off",
            fallback_name="Start up on/off",
        )
        .add_to_registry(registry)
    )

    quirked = registry.resolve(device_mock)
    assert not isinstance(quirked, CustomZigpyDevice)


async def test_quirks_v2_multiple_matches_not_raises(device_mock):
    """Test that registering an identical v2 quirk twice deduplicates, not raises.

    Identical quirk definitions compare equal (the `source` provenance is excluded
    from equality), so the registry keeps a single entry rather than accumulating
    duplicates.
    """
    registry = DeviceRegistry()

    def build():
        return (
            QuirkBuilder(device_mock.manufacturer, device_mock.model)
            .adds(Basic.cluster_id)
            .adds(OnOff.cluster_id)
            .enum(
                OnOff.AttributeDefs.start_up_on_off.name,
                OnOff.StartUpOnOff,
                OnOff.cluster_id,
                translation_key="start_up_on_off",
                fallback_name="Start up on/off",
            )
            .add_to_registry(registry)
        )

    entry1 = build()
    entry2 = build()

    assert entry1 == entry2
    assert list(registry) == [entry1]

    assert isinstance(registry.resolve(device_mock), CustomZigpyDevice)


async def test_quirks_v2_with_custom_device_class(device_mock):
    """Test adding a quirk with a custom device class to the registry."""
    registry = DeviceRegistry()

    class CustomTestDevice(CustomZigpyDevice):
        """Custom test device for testing quirks v2."""

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .device_class(CustomTestDevice)
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .enum(
            OnOff.AttributeDefs.start_up_on_off.name,
            OnOff.StartUpOnOff,
            OnOff.cluster_id,
            translation_key="start_up_on_off",
            fallback_name="Start up on/off",
        )
        .add_to_registry(registry)
    )

    assert isinstance(registry.resolve(device_mock), CustomTestDevice)


async def test_quirks_v2_with_custom_device_class_raises(device_mock):
    """Test that a zigpy device class that is not a `BaseCustomDevice` raises."""
    registry = DeviceRegistry()

    class CustomTestDevice:
        """Neither a ZHA `Device` nor a zigpy `BaseCustomDevice`."""

    with pytest.raises(
        TypeError,
        match="is not a subclass of BaseCustomDevice",
    ):
        (
            QuirkBuilder(device_mock.manufacturer, device_mock.model)
            .device_class(CustomTestDevice)
            .adds(Basic.cluster_id)
            .adds(OnOff.cluster_id)
            .enum(
                OnOff.AttributeDefs.start_up_on_off.name,
                OnOff.StartUpOnOff,
                OnOff.cluster_id,
            )
            .add_to_registry(registry)
        )


async def test_quirks_v2_with_node_descriptor(device_mock):
    """Test adding a quirk with an overridden node descriptor to the registry."""
    registry = DeviceRegistry()

    node_descriptor = NodeDescriptor(
        logical_type=LogicalType.Router,
        complex_descriptor_available=0,
        user_descriptor_available=0,
        reserved=0,
        aps_flags=0,
        frequency_band=NodeDescriptor.FrequencyBand.Freq2400MHz,
        mac_capability_flags=NodeDescriptor.MACCapabilityFlags.AllocateAddress,
        manufacturer_code=4174,
        maximum_buffer_size=82,
        maximum_incoming_transfer_size=82,
        server_mask=0,
        maximum_outgoing_transfer_size=82,
        descriptor_capability_field=NodeDescriptor.DescriptorCapability.NONE,
    )

    assert device_mock.node_desc != node_descriptor

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .node_descriptor(node_descriptor)
        .add_to_registry(registry)
    )

    quirked: CustomZigpyDevice = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)
    assert quirked.node_desc == node_descriptor


async def test_quirks_v2_replace_occurrences(device_mock):
    """Test adding a quirk that replaces all occurrences of a cluster."""
    registry = DeviceRegistry()

    device_mock[1].add_output_cluster(Identify.cluster_id)

    device_mock.add_endpoint(2)
    device_mock[2].profile_id = 255
    device_mock[2].device_type = 255
    device_mock[2].add_input_cluster(Identify.cluster_id)

    device_mock.add_endpoint(3)
    device_mock[3].profile_id = 255
    device_mock[3].device_type = 255
    device_mock[3].add_output_cluster(Identify.cluster_id)

    class CustomIdentifyCluster(CustomCluster, Identify):
        """Custom identify cluster for testing quirks v2."""

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .replace_cluster_occurrences(CustomIdentifyCluster)
        .add_to_registry(registry)
    )

    quirked: CustomZigpyDevice = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)

    assert isinstance(
        quirked.endpoints[1].in_clusters[Identify.cluster_id], CustomIdentifyCluster
    )
    assert isinstance(
        quirked.endpoints[1].out_clusters[Identify.cluster_id], CustomIdentifyCluster
    )
    assert isinstance(
        quirked.endpoints[2].in_clusters[Identify.cluster_id], CustomIdentifyCluster
    )
    assert isinstance(
        quirked.endpoints[3].out_clusters[Identify.cluster_id], CustomIdentifyCluster
    )


async def test_quirks_v2_skip_configuration(device_mock):
    """Test adding a quirk that skips configuration to the registry."""
    registry = DeviceRegistry()

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .skip_configuration()
        .add_to_registry(registry)
    )

    quirked = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)

    # `skip_configuration` is consumed by ZHA, so it now lives on the quirk
    # definition rather than on the resolved zigpy device.
    entry = registry.match_entry(quirked)
    assert entry.zha_device_factory.quirk_definition.skip_configuration is True


async def test_quirks_v2_device_automation_triggers_on_zigpy_device(device_mock):
    """Test quirk-defined triggers are stamped onto the resolved zigpy device."""
    registry = DeviceRegistry()

    triggers = {(SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON}}

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .device_automation_triggers(triggers)
        .add_to_registry(registry)
    )

    quirked = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)

    # Consumers reading only the zigpy device (e.g. HA's early device trigger
    # cache) see the same triggers a v1 quirk exposes as a class attribute.
    assert quirked.device_automation_triggers == triggers


async def test_quirks_v2_no_device_automation_triggers(device_mock):
    """Test no trigger attribute is stamped when a quirk defines none."""
    registry = DeviceRegistry()

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .adds(OnOff.cluster_id)
        .add_to_registry(registry)
    )

    quirked = registry.resolve(device_mock)
    assert not hasattr(quirked, "device_automation_triggers")


async def test_quirks_v2_removes(device_mock):
    """Test adding a quirk that removes a cluster to the registry."""
    registry = DeviceRegistry()

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .removes(Identify.cluster_id)
        .add_to_registry(registry)
    )

    quirked_device: CustomZigpyDevice = registry.resolve(device_mock)
    assert isinstance(quirked_device, CustomZigpyDevice)

    assert quirked_device.endpoints[1].in_clusters.get(Identify.cluster_id) is None


async def test_quirks_v2_endpoints(device_mock):
    """Test adding a quirk that modifies endpoints to the registry."""
    registry = DeviceRegistry()

    device_mock[1].add_output_cluster(Identify.cluster_id)

    device_mock.add_endpoint(2)
    device_mock[2].profile_id = 255
    device_mock[2].device_type = 255
    device_mock[2].add_input_cluster(Identify.cluster_id)
    device_mock[2].add_output_cluster(OnOff.cluster_id)

    device_mock.add_endpoint(3)
    device_mock[3].profile_id = 255
    device_mock[3].device_type = 255
    device_mock[3].add_input_cluster(Identify.cluster_id)
    device_mock[3].add_output_cluster(OnOff.cluster_id)

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .adds_endpoint(1, profile_id=260, device_type=260)  # 1 not modified
        .removes_endpoint(2)
        .replaces_endpoint(3, profile_id=260, device_type=260)
        .adds_endpoint(4)
        .adds(OnOff.cluster_id, endpoint_id=4)
        .replaces_endpoint(5)
        .add_to_registry(registry)
    )

    quirked: CustomZigpyDevice = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)

    # verify endpoint 1 was not modified, as it already existed before
    assert 1 in quirked.endpoints
    assert quirked.endpoints[1].profile_id == 255
    assert quirked.endpoints[1].device_type == 255

    # verify endpoint 2 was removed
    assert 2 not in quirked.endpoints

    # verify endpoint 3 profile id and device type were replaced
    assert 3 in quirked.endpoints
    assert quirked.endpoints[3].profile_id == 260
    assert quirked.endpoints[3].device_type == 260

    # verify original clusters still exist on endpoint 3 where id and type were replaced
    assert quirked.endpoints[3].in_clusters.get(Identify.cluster_id) is not None
    assert quirked.endpoints[3].out_clusters.get(OnOff.cluster_id) is not None

    # verify endpoint 4 was added with default profile id and device type using adds
    assert 4 in quirked.endpoints
    assert quirked.endpoints[4].profile_id == 260
    assert quirked.endpoints[4].device_type == 255

    # verify cluster was added to endpoint 4
    assert quirked.endpoints[4].in_clusters.get(OnOff.cluster_id) is not None

    # verify endpoint 5 was added with default profile id and device type using replaces
    assert 5 in quirked.endpoints
    assert quirked.endpoints[5].profile_id == 260
    assert quirked.endpoints[5].device_type == 255


async def test_quirks_v2_processing_order(device_mock):
    """Test quirks v2 metadata processing order."""
    registry = DeviceRegistry()

    device_mock.add_endpoint(2)
    device_mock[2].add_input_cluster(Identify.cluster_id)
    device_mock[2].add_output_cluster(OnOff.cluster_id)

    device_mock.add_endpoint(3)
    device_mock[3].add_input_cluster(Identify.cluster_id)
    device_mock[3].add_output_cluster(OnOff.cluster_id)

    class TestCustomIdentifyCluster(CustomCluster, Identify):
        """Custom identify cluster for testing quirks v2."""

    # the order of operations in the quirk builder below barely matters,
    # but is laid out in a way that generally follows the expected execution order
    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .removes_endpoint(2)  # wipes device reported clusters from endpoint 2
        .adds_endpoint(2)  # adds a new "blank" endpoint 2 with no clusters
        .removes(Identify.cluster_id, endpoint_id=3)  # test removing cluster
        .adds(TestCustomIdentifyCluster, endpoint_id=3)  # then "replacing" it by adds
        .adds(LevelControl.cluster_id, endpoint_id=2)  # adds one custom cluster to ep 2
        .add_to_registry(registry)
    )

    quirked: CustomZigpyDevice = registry.resolve(device_mock)
    assert isinstance(quirked, CustomZigpyDevice)

    # verify endpoint 2 was removed and a new one added with device clusters removed
    assert 2 in quirked.endpoints
    assert quirked.endpoints[2].in_clusters.get(Identify.cluster_id) is None
    assert quirked.endpoints[2].out_clusters.get(OnOff.cluster_id) is None

    # verify endpoint 2 cluster added by quirk is present though
    assert quirked.endpoints[2].in_clusters.get(LevelControl.cluster_id) is not None

    # verify endpoint 3 cluster was replaced by alternatively using removes and adds
    # instead of just using replaces directly
    assert 3 in quirked.endpoints
    assert isinstance(
        quirked.endpoints[3].in_clusters[Identify.cluster_id], TestCustomIdentifyCluster
    )


async def test_quirks_v2_apply_custom_configuration(device_mock):
    """Test adding a quirk custom configuration to the registry."""
    registry = DeviceRegistry()

    class CustomOnOffCluster(CustomCluster, OnOff):
        """Custom on off cluster for testing quirks v2."""

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .adds(CustomOnOffCluster)
        .adds(CustomOnOffCluster, cluster_type=ClusterType.Client)
        .add_to_registry(registry)
    )

    quirked_device: CustomZigpyDevice = registry.resolve(device_mock)
    assert isinstance(quirked_device, CustomZigpyDevice)

    # pylint: disable=line-too-long
    quirked_cluster: CustomOnOffCluster = quirked_device.endpoints[1].in_clusters[
        CustomOnOffCluster.cluster_id
    ]
    assert isinstance(quirked_cluster, CustomOnOffCluster)
    # verify server cluster type was set when adding
    assert quirked_cluster.cluster_type == ClusterType.Server

    quirked_cluster.apply_custom_configuration = AsyncMock()

    quirked_client_cluster: CustomOnOffCluster = quirked_device.endpoints[
        1
    ].out_clusters[CustomOnOffCluster.cluster_id]
    assert isinstance(quirked_client_cluster, CustomOnOffCluster)
    # verify client cluster type was set when adding
    assert quirked_client_cluster.cluster_type == ClusterType.Client

    quirked_client_cluster.apply_custom_configuration = AsyncMock()

    await quirked_device.apply_custom_configuration()

    assert quirked_cluster.apply_custom_configuration.await_count == 1
    assert quirked_client_cluster.apply_custom_configuration.await_count == 1


async def test_quirks_v2_also_applies_to(device_mock):
    """Test adding the same quirk for multiple manufacturers and models."""
    registry = DeviceRegistry()

    class CustomTestDevice(CustomZigpyDevice):
        """Custom test device for testing quirks v2."""

    (
        QuirkBuilder(device_mock.manufacturer, device_mock.model)
        .also_applies_to("manufacturer2", "model2")
        .also_applies_to("manufacturer3", "model3")
        .device_class(CustomTestDevice)
        .adds(Basic.cluster_id)
        .adds(OnOff.cluster_id)
        .enum(
            OnOff.AttributeDefs.start_up_on_off.name,
            OnOff.StartUpOnOff,
            OnOff.cluster_id,
            translation_key="start_up_on_off",
            fallback_name="Start up on/off",
        )
        .add_to_registry(registry)
    )

    assert isinstance(registry.resolve(device_mock), CustomTestDevice)

    device_mock.manufacturer = "manufacturer2"
    device_mock.model = "model2"
    assert isinstance(registry.resolve(device_mock), CustomTestDevice)

    device_mock.manufacturer = "manufacturer3"
    device_mock.model = "model3"
    assert isinstance(registry.resolve(device_mock), CustomTestDevice)


@pytest.mark.parametrize(
    ("obj", "expected"),
    [
        ({}, frozendict()),
        ([], ()),
        ({"a": 1, "b": 2}, frozendict({"a": 1, "b": 2})),
        ([1, 2, 3], (1, 2, 3)),
        (
            {"outer": {"inner": "value"}},
            frozendict({"outer": frozendict({"inner": "value"})}),
        ),
        ({"key": [1, 2, 3]}, frozendict({"key": (1, 2, 3)})),
        ([{"a": 1}, {"b": 2}], (frozendict({"a": 1}), frozendict({"b": 2}))),
        ([[1, 2], [3, 4]], ((1, 2), (3, 4))),
        (
            {"a": [1, {"b": 2}], "c": {"d": [3, 4]}},
            frozendict(
                {"a": (1, frozendict({"b": 2})), "c": frozendict({"d": (3, 4)})}
            ),
        ),
        (42, 42),
        ("string", "string"),
        (None, None),
        (True, True),
        (3.14, 3.14),
        (frozendict({"a": 1}), frozendict({"a": 1})),
        ((1, 2, 3), (1, 2, 3)),
        ((1, [2], {3: 4}), (1, (2,), frozendict({3: 4}))),
        (
            {"triggers": {("key1", "key2"): {"param": 0}}},
            frozendict(
                {"triggers": frozendict({("key1", "key2"): frozendict({"param": 0})})}
            ),
        ),
    ],
)
def test_recursive_freeze(obj, expected):
    """Test recursive_freeze converts mutable collections to immutable ones."""
    result = recursive_freeze(obj)
    assert strict_eq(result, expected)
    hash(result)


def test_quirk_v2_loading_failure(
    device_mock: Device, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that v2 quirks can fail to load without crashing."""

    registry = DeviceRegistry()

    class BadCustomDevice(CustomZigpyDevice):
        """Custom device with bad quirk definition."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("This device failed to initialize")

    (
        QuirkBuilder(registry=registry)
        .applies_to(
            manufacturer=device_mock.manufacturer,
            model=device_mock.model,
        )
        .device_class(BadCustomDevice)
        .add_to_registry(registry)
    )

    with caplog.at_level(logging.ERROR):
        quirked = registry.resolve(device_mock)

    assert quirked is device_mock
    assert "Failed to load quirk for" in caplog.text
