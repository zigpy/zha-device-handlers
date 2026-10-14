"""Tests for child devices defined by quirks v2."""

from types import SimpleNamespace

from frozendict import frozendict
import pytest
from zha.application import EntityPlatform
from zha.quirks import DeviceRegistry
from zha.zigbee.child_device import ChildDevice
import zigpy.types as t
from zigpy.typing import UNDEFINED
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.builder.discovery import _generic_kwargs
from zhaquirks.builder.metadata import ChildDeviceMetadata, QuirkDefinition
from zhaquirks.tuya.builder import TuyaQuirkBuilder


def _switch(builder: QuirkBuilder, endpoint_id: int, **kwargs) -> QuirkBuilder:
    """Add a config switch on an endpoint."""
    return builder.switch(
        OnOff.AttributeDefs.on_time.name,
        OnOff.cluster_id,
        endpoint_id=endpoint_id,
        translation_key="on_time",
        fallback_name="On time",
        **kwargs,
    )


def test_child_devices_default_none() -> None:
    """Test a quirk leaves child devices to ZHA by default."""
    entry = QuirkBuilder("manufacturer", "model").add_to_registry(DeviceRegistry())

    assert entry.zha_device_factory.quirk_definition.child_devices is None


def test_child_device() -> None:
    """Test defining child devices."""
    entry = (
        QuirkBuilder("manufacturer", "model")
        .child_device(
            "left",
            endpoint_id=1,
            translation_key="left",
            fallback_name="Left",
        )
        .child_device(
            "right",
            endpoint_ids=[2, 3],
            translation_key="gang",
            translation_placeholders={"name": "right"},
            fallback_name="Right",
        )
        .add_to_registry(DeviceRegistry())
    )

    assert entry.zha_device_factory.quirk_definition.child_devices == (
        ChildDeviceMetadata(
            id="left",
            endpoint_ids=frozenset({1}),
            translation_key="left",
            fallback_name="Left",
        ),
        ChildDeviceMetadata(
            id="right",
            endpoint_ids=frozenset({2, 3}),
            translation_key="gang",
            translation_placeholders=frozendict({"name": "right"}),
            fallback_name="Right",
        ),
    )


def test_child_device_without_endpoints() -> None:
    """Test a child device holding only explicitly assigned entities."""
    builder = QuirkBuilder("manufacturer", "model").child_device(
        "extra", fallback_name="Extra"
    )
    _switch(builder, 1, child_device_id="extra")
    entry = builder.add_to_registry(DeviceRegistry())

    definition = entry.zha_device_factory.quirk_definition
    assert definition.child_devices[0].endpoint_ids == frozenset()
    assert definition.entity_metadata[0].child_device_id == "extra"


def test_child_device_endpoint_arguments() -> None:
    """Test endpoint_id and endpoint_ids are mutually exclusive."""
    with pytest.raises(ValueError, match="either endpoint_id or endpoint_ids"):
        QuirkBuilder("manufacturer", "model").child_device(
            "a", endpoint_id=1, endpoint_ids=[2], fallback_name="A"
        )


def test_child_device_id_required() -> None:
    """Test a child device needs a non-empty id."""
    with pytest.raises(ValueError):
        QuirkBuilder("manufacturer", "model").child_device(
            "", endpoint_id=1, fallback_name="A"
        )


def test_disable_child_devices() -> None:
    """Test disabling child devices."""
    entry = (
        QuirkBuilder("manufacturer", "model")
        .disable_child_devices()
        .add_to_registry(DeviceRegistry())
    )

    assert entry.zha_device_factory.quirk_definition.child_devices == ()

    with pytest.raises(ValueError, match="already defines child devices"):
        QuirkBuilder("manufacturer", "model").child_device(
            "a", endpoint_id=1, fallback_name="A"
        ).disable_child_devices()

    with pytest.raises(ValueError, match="Child devices are disabled"):
        QuirkBuilder("manufacturer", "model").disable_child_devices().child_device(
            "a", endpoint_id=1, fallback_name="A"
        )


def test_child_device_duplicate_id() -> None:
    """Test child device ids must be unique."""
    builder = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_id=1, fallback_name="A")
        .child_device("a", endpoint_id=2, fallback_name="A")
    )

    with pytest.raises(ValueError, match="Duplicate child device ids"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_overlapping_endpoints() -> None:
    """Test an endpoint can only belong to one child device."""
    builder = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_ids=[1, 2], fallback_name="A")
        .child_device("b", endpoint_id=2, fallback_name="B")
    )

    with pytest.raises(ValueError, match="Endpoint 2 is assigned to both"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_unknown_reference() -> None:
    """Test entities can only refer to defined child devices."""
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, child_device_id="unknown")

    with pytest.raises(ValueError, match="undefined child devices"):
        builder.add_to_registry(DeviceRegistry())

    builder = QuirkBuilder("manufacturer", "model").change_entity_metadata(
        endpoint_id=1, new_child_device_id="unknown"
    )

    with pytest.raises(ValueError, match="undefined child devices"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_entities() -> None:
    """Test each child device and the main device can have a primary entity."""
    builder = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_id=1, fallback_name="A")
        .child_device("b", endpoint_id=2, fallback_name="B")
    )
    _switch(builder, 1, primary=True)
    _switch(builder, 2, primary=True)
    _switch(builder, 3, primary=True)

    # A second primary entity on the same child device is not allowed
    with pytest.raises(ValueError, match="Only one primary entity"):
        _switch(builder, 2, primary=True, unique_id_suffix="other")

    # Nor is one assigned to it explicitly
    with pytest.raises(ValueError, match="Only one primary entity"):
        _switch(builder, 3, primary=True, child_device_id="a")

    entry = builder.add_to_registry(DeviceRegistry())
    assert len(entry.zha_device_factory.quirk_definition.entity_metadata) == 3


def test_child_device_primary_entities_defined_later() -> None:
    """Test primary entities are validated against child devices defined later."""
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, primary=True)
    _switch(builder, 2, primary=True, child_device_id="a")

    # Defining the child device for endpoint 1 later puts both primary entities on it
    builder.child_device("a", endpoint_id=1, fallback_name="A")

    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())


def test_entity_child_device_kwargs() -> None:
    """Test the child device of an exposed entity is passed to ZHA when set."""
    builder = QuirkBuilder("manufacturer", "model").child_device(
        "a", endpoint_id=2, fallback_name="A"
    )
    _switch(builder, 1)
    _switch(builder, 2, child_device_id=None, unique_id_suffix="main")
    _switch(builder, 3, child_device_id="a", unique_id_suffix="child")
    entity_metadata = builder.add_to_registry(
        DeviceRegistry()
    ).zha_device_factory.quirk_definition.entity_metadata

    assert entity_metadata[0].child_device_id is UNDEFINED
    assert "child_device_id" not in _generic_kwargs(entity_metadata[0])
    assert _generic_kwargs(entity_metadata[1])["child_device_id"] is None
    assert _generic_kwargs(entity_metadata[2])["child_device_id"] == "a"


def test_quirk_v2_device_child_devices() -> None:
    """Test the quirk's child devices are exposed to ZHA."""
    definition = QuirkDefinition(
        child_devices=(
            ChildDeviceMetadata(
                id="a",
                endpoint_ids=frozenset({1}),
                translation_key="gang",
                translation_placeholders={"name": "a"},
                fallback_name="A",
            ),
            ChildDeviceMetadata(id="b", fallback_name="B"),
        )
    )
    device = SimpleNamespace(_quirk_definition=definition)

    assert QuirkV2Device._quirk_child_devices(device) == [
        ChildDevice(
            id="a",
            endpoint_ids=frozenset({1}),
            translation_key="gang",
            translation_placeholders={"name": "a"},
            fallback_name="A",
        ),
        ChildDevice(id="b", fallback_name="B"),
    ]

    device = SimpleNamespace(_quirk_definition=QuirkDefinition())
    assert QuirkV2Device._quirk_child_devices(device) is None

    device = SimpleNamespace(_quirk_definition=QuirkDefinition(child_devices=()))
    assert QuirkV2Device._quirk_child_devices(device) == []


@pytest.mark.parametrize(
    ("new_child_device_id", "expected"),
    [(UNDEFINED, "unchanged"), (None, None), ("a", "a")],
)
def test_change_entity_child_device(new_child_device_id, expected) -> None:
    """Test changing the child device of a default entity."""
    entry = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", fallback_name="A")
        .change_entity_metadata(endpoint_id=1, new_child_device_id=new_child_device_id)
        .add_to_registry(DeviceRegistry())
    )
    definition = entry.zha_device_factory.quirk_definition
    entity = SimpleNamespace(
        PLATFORM=EntityPlatform.SWITCH,
        unique_id="ab:cd:ef:12:34:56:78:90-1-6",
        endpoint=SimpleNamespace(id=1),
        _attr_child_device_id="unchanged",
    )

    QuirkV2Device._apply_entity_metadata_changes(
        SimpleNamespace(_quirk_definition=definition), entity
    )
    assert entity._attr_child_device_id == expected


def test_tuya_entity_child_device() -> None:
    """Test Tuya data point entities can be assigned to a child device."""
    entry = (
        TuyaQuirkBuilder("_TZE200_abcdefgh", "TS0601", registry=DeviceRegistry())
        .child_device("l2", fallback_name="L2")
        .tuya_switch(
            dp_id=7,
            attribute_name="child_lock_2",
            translation_key="child_lock",
            fallback_name="Child lock",
            child_device_id="l2",
        )
        .tuya_sensor(
            dp_id=8,
            attribute_name="power_2",
            type=t.uint16_t,
            translation_key="power",
            fallback_name="Power",
            child_device_id="l2",
        )
        .add_to_registry()
    )

    assert [
        entity.child_device_id
        for entity in entry.zha_device_factory.quirk_definition.entity_metadata
    ] == ["l2", "l2"]


def test_child_device_primary_device_level_entities() -> None:
    """Test primary entities of device-level clusters count for the main device."""
    builder = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_id=1, fallback_name="A")
        .child_device("b", endpoint_id=2, fallback_name="B")
    )

    for endpoint_id in (1, 2):
        builder.sensor(
            PowerConfiguration.AttributeDefs.battery_voltage.name,
            PowerConfiguration.cluster_id,
            endpoint_id=endpoint_id,
            translation_key="battery_voltage",
            fallback_name="Battery voltage",
            unique_id_suffix=f"battery_voltage_{endpoint_id}",
            primary=endpoint_id == 1 or None,
        )

    # Both stay on the main device in ZHA, so a second primary one is rejected
    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.sensor(
            PowerConfiguration.AttributeDefs.battery_voltage.name,
            PowerConfiguration.cluster_id,
            endpoint_id=2,
            translation_key="battery_voltage",
            fallback_name="Battery voltage",
            primary=True,
        )


def test_child_device_id_type() -> None:
    """Test child device ids must be strings."""
    with pytest.raises(TypeError):
        _switch(QuirkBuilder("manufacturer", "model"), 1, child_device_id=1)

    with pytest.raises(TypeError):
        QuirkBuilder("manufacturer", "model").child_device(
            b"left", endpoint_id=1, fallback_name="Left"
        )
