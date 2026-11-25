"""Tests for child devices defined by quirks v2."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from frozendict import frozendict
import pytest
from zha.application import EntityPlatform, Platform
from zha.application.platforms import ZclPlatformEntity
from zha.application.platforms.sensor import BaseSensor, Temperature
from zha.application.platforms.switch import ConfigurableAttributeSwitch, Switch
from zha.quirks import DeviceRegistry
from zha.zigbee.child_device import ChildDevice
import zigpy.types as t
from zigpy.typing import UNDEFINED
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
from zhaquirks.builder import ButtonEvent, ButtonEventType, EntityFilter, QuirkBuilder
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.builder.discovery import _generic_kwargs
from zhaquirks.builder.metadata import ChildDeviceMetadata, QuirkDefinition
from zhaquirks.const import COMMAND, COMMAND_ON
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

    builder = QuirkBuilder("manufacturer", "model").adds_entity(
        Switch,
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="added",
        child_device_id="unknown",
    )

    with pytest.raises(ValueError, match="undefined child devices"):
        builder.add_to_registry(DeviceRegistry())

    builder = QuirkBuilder("manufacturer", "model").replaces_entity(
        Switch, Switch, endpoint_id=1, cluster_id=OnOff.cluster_id, child_device_id="x"
    )

    with pytest.raises(ValueError, match="undefined child devices"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_entities() -> None:
    """Test each child device and the main device can have a primary entity."""
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, primary=True)
    _switch(builder, 2, primary=True)
    _switch(builder, 3, primary=True)

    # Child devices defined after the entities still count
    builder.child_device("a", endpoint_id=1, fallback_name="A")
    builder.child_device("b", endpoint_id=2, fallback_name="B")
    entry = builder.add_to_registry(DeviceRegistry())
    assert len(entry.zha_device_factory.quirk_definition.entity_metadata) == 3

    # A second primary entity on the same child device is not allowed
    _switch(builder, 2, primary=True, unique_id_suffix="other")
    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_explicit_assignment() -> None:
    """Test explicitly assigned primary entities count for their child device."""
    builder = QuirkBuilder("manufacturer", "model").child_device(
        "a", endpoint_id=1, fallback_name="A"
    )
    _switch(builder, 1, primary=True)
    _switch(builder, 3, primary=True, child_device_id="a")

    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_error_names_entities() -> None:
    """Test the primary entity error names the device and both entities."""
    builder = QuirkBuilder("manufacturer", "model").child_device(
        "a", endpoint_id=1, fallback_name="A"
    )
    _switch(builder, 1, primary=True)
    _switch(builder, 1, primary=True, unique_id_suffix="other")

    with pytest.raises(
        ValueError,
        match=(
            "child device 'a' has both the switch entity 'on_time' on endpoint 1"
            " and the switch entity 'other' on endpoint 1"
        ),
    ):
        builder.add_to_registry(DeviceRegistry())


def _two_primaries_moved(**change_kwargs) -> QuirkBuilder:
    """Return a quirk with a primary switch on endpoints 1 and 2 of child device `a`."""
    builder = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_ids=[1, 2], fallback_name="A")
        .child_device("b", fallback_name="B")
    )
    _switch(builder, 1, primary=True)
    _switch(builder, 2, primary=True)
    return builder.change_entity_metadata(**change_kwargs)


def test_child_device_primary_changed_child_device() -> None:
    """Test a quirk entity moved with `change_entity_metadata` counts where it moves."""
    _two_primaries_moved(
        endpoint_id=2, cluster_id=OnOff.cluster_id, new_child_device_id="b"
    ).add_to_registry(DeviceRegistry())

    # Moving it by its unique ID suffix works as well
    _two_primaries_moved(
        unique_id_suffix="2-on_time", new_child_device_id="b"
    ).add_to_registry(DeviceRegistry())

    # A change that matches neither entity leaves both on `a`
    with pytest.raises(ValueError, match="Only one primary entity"):
        _two_primaries_moved(
            endpoint_id=2,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            new_child_device_id="b",
        ).add_to_registry(DeviceRegistry())

    with pytest.raises(ValueError, match="Only one primary entity"):
        _two_primaries_moved(
            unique_id_suffix="3-on_time", new_child_device_id="b"
        ).add_to_registry(DeviceRegistry())

    # Moving both entities puts both primary entities on `b`
    with pytest.raises(ValueError, match="child device 'b'"):
        _two_primaries_moved(
            cluster_id=OnOff.cluster_id, new_child_device_id="b"
        ).add_to_registry(DeviceRegistry())


def test_child_device_primary_changed_primary() -> None:
    """Test a quirk entity demoted with `change_entity_metadata` isn't primary."""
    _two_primaries_moved(
        endpoint_id=2, cluster_id=OnOff.cluster_id, new_primary=False
    ).add_to_registry(DeviceRegistry())

    # A later change applies after an earlier one, as in ZHA
    with pytest.raises(ValueError, match="Only one primary entity"):
        _two_primaries_moved(
            endpoint_id=2, cluster_id=OnOff.cluster_id, new_primary=False
        ).change_entity_metadata(
            endpoint_id=2, cluster_id=OnOff.cluster_id, new_primary=True
        ).add_to_registry(DeviceRegistry())


def test_child_device_primary_unknown_change() -> None:
    """Test a change the builder can't match leaves the entity to ZHA's election."""
    # The function decides at discovery, so the builder can't reject the quirk
    _two_primaries_moved(
        function=lambda entity: entity.endpoint.id == 2, new_child_device_id="b"
    ).add_to_registry(DeviceRegistry())

    # A function filter that doesn't set the child device or primary is irrelevant
    with pytest.raises(ValueError, match="Only one primary entity"):
        _two_primaries_moved(
            function=lambda entity: True, new_fallback_name="Renamed"
        ).add_to_registry(DeviceRegistry())

    # A suffix filter can't be matched once an unknown change may set a unique ID
    _two_primaries_moved(
        function=lambda entity: entity.endpoint.id == 2, new_unique_id="ab:cd-2-other"
    ).change_entity_metadata(
        unique_id_suffix="other", new_child_device_id="b"
    ).add_to_registry(DeviceRegistry())


def test_child_device_primary_changed_primary_promotes() -> None:
    """Test a `new_primary=True` change that matches two quirk entities is rejected."""
    builder = QuirkBuilder("manufacturer", "model").child_device(
        "a", endpoint_id=1, fallback_name="A"
    )
    _switch(builder, 1, unique_id_suffix="first")
    _switch(builder, 1, unique_id_suffix="second")
    builder.change_entity_metadata(cluster_id=OnOff.cluster_id, new_primary=True)

    # ZHA would elect neither of them
    with pytest.raises(ValueError, match="child device 'a'"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_removed_entity() -> None:
    """Test a quirk entity that `removes_entity` removes doesn't count."""
    builder = QuirkBuilder("manufacturer", "model").disable_child_devices()
    _switch(builder, 1, unique_id_suffix="kept-control")
    _switch(builder, 1, unique_id_suffix="removed-control")
    builder.change_entity_metadata(unique_id_suffix="control", new_primary=True)
    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())

    builder.removes_entity(EntityFilter(unique_id_suffix="removed-control"))
    builder.add_to_registry(DeviceRegistry())

    # Removing every entity of the cluster removes the quirk's own ones too
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, primary=True)
    _switch(builder, 1, primary=True, unique_id_suffix="other")
    builder.prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
    builder.add_to_registry(DeviceRegistry())

    # An entity a filter may remove is left to ZHA as well
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, primary=True)
    _switch(builder, 1, primary=True, unique_id_suffix="other")
    builder.removes_entity(EntityFilter(function=lambda entity: True))
    builder.add_to_registry(DeviceRegistry())

    # A filter that doesn't match the entity leaves it counted
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, primary=True)
    _switch(builder, 1, primary=True, unique_id_suffix="other")
    builder.removes_entity(EntityFilter(endpoint_id=2))
    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_changed_unique_id() -> None:
    """Test suffix filters follow `new_unique_id` changes of the quirk's entities."""
    # A new unique ID on another endpoint leaves these entities' unique IDs alone
    with pytest.raises(ValueError, match="Only one primary entity"):
        _two_primaries_moved(
            endpoint_id=3, new_unique_id="other"
        ).change_entity_metadata(
            unique_id_suffix="3-on_time", new_child_device_id="b"
        ).add_to_registry(DeviceRegistry())

    # A suffix filter matches the new unique ID, not the old one
    _two_primaries_moved(
        endpoint_id=2, new_unique_id="ab:cd-2-custom"
    ).change_entity_metadata(
        unique_id_suffix="custom", new_child_device_id="b"
    ).add_to_registry(DeviceRegistry())

    with pytest.raises(ValueError, match="Only one primary entity"):
        _two_primaries_moved(
            endpoint_id=2, new_unique_id="ab:cd-2-custom"
        ).change_entity_metadata(
            unique_id_suffix="2-on_time", new_child_device_id="b"
        ).add_to_registry(DeviceRegistry())


def test_child_device_primary_empty_unique_id_suffix() -> None:
    """Test an empty unique ID suffix keeps its separator, as in ZHA."""
    builder = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_ids=[1, 2], fallback_name="A")
        .child_device("b", fallback_name="B")
    )
    _switch(builder, 1, primary=True)
    _switch(builder, 2, primary=True, unique_id_suffix="")

    # The unique ID ends with `-2-`, so a `2` suffix filter doesn't match it
    builder.change_entity_metadata(unique_id_suffix="2", new_child_device_id="b")
    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())


@pytest.mark.parametrize(
    ("entity_filter", "removed"),
    [
        (EntityFilter(entity_cls=Temperature), False),
        (EntityFilter(entity_cls=ConfigurableAttributeSwitch), True),
        (
            EntityFilter(entity_cls=ConfigurableAttributeSwitch, unique_id_suffix="x"),
            False,
        ),
        (EntityFilter(translation_key="other"), False),
        (EntityFilter(translation_key="on_time"), True),
        (EntityFilter(platform=EntityPlatform.SENSOR), False),
    ],
)
def test_child_device_primary_removed_entity_filters(
    entity_filter: EntityFilter, removed: bool
) -> None:
    """Test removal filters on entity class and translation key are decided."""
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1, primary=True)
    _switch(builder, 1, primary=True, unique_id_suffix="other")
    builder.removes_entity(entity_filter)

    if removed:
        builder.add_to_registry(DeviceRegistry())
    else:
        with pytest.raises(ValueError, match="Only one primary entity"):
            builder.add_to_registry(DeviceRegistry())


def test_child_device_primary_promoted_automatic_split() -> None:
    """Test a promotion is left to ZHA when ZHA may split the device on its own."""
    builder = QuirkBuilder("manufacturer", "model")
    _switch(builder, 1)
    _switch(builder, 2)
    builder.change_entity_metadata(cluster_id=OnOff.cluster_id, new_primary=True)

    # ZHA may put each one on a child device of its own
    builder.add_to_registry(DeviceRegistry())

    # Without child devices, both are on the main device
    builder.disable_child_devices()
    with pytest.raises(ValueError, match="the main device"):
        builder.add_to_registry(DeviceRegistry())


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


def test_button_event_child_device_kwargs() -> None:
    """Test a button event entity can be assigned to a child device explicitly."""
    entity_metadata = (
        QuirkBuilder("manufacturer", "model")
        .child_device("a", endpoint_id=2, fallback_name="A")
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_ON},
                )
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
            child_device_id="a",
        )
        .add_to_registry(DeviceRegistry())
        .zha_device_factory.quirk_definition.entity_metadata
    )

    assert _generic_kwargs(entity_metadata[0])["child_device_id"] == "a"


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
    # The entity filter only matches endpoint-bound (ZCL) entities by endpoint
    entity = MagicMock(spec=ZclPlatformEntity)
    entity.PLATFORM = EntityPlatform.SWITCH
    entity.unique_id = "ab:cd:ef:12:34:56:78:90-1-6"
    entity.endpoint = SimpleNamespace(id=1)
    entity._attr_child_device_id = "unchanged"

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

    builder.add_to_registry(DeviceRegistry())

    # Both stay on the main device in ZHA, so a second primary one is rejected
    builder.sensor(
        PowerConfiguration.AttributeDefs.battery_voltage.name,
        PowerConfiguration.cluster_id,
        endpoint_id=2,
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
        primary=True,
    )
    with pytest.raises(ValueError, match="Only one primary entity"):
        builder.add_to_registry(DeviceRegistry())


def test_child_device_id_type() -> None:
    """Test child device ids must be strings."""
    with pytest.raises(TypeError):
        _switch(QuirkBuilder("manufacturer", "model"), 1, child_device_id=1)

    with pytest.raises(TypeError):
        QuirkBuilder("manufacturer", "model").child_device(
            b"left", endpoint_id=1, fallback_name="Left"
        )


def test_added_entity_child_device_id_type() -> None:
    """Test `adds_entity` and `replaces_entity` only take string child device ids."""
    with pytest.raises(TypeError):
        QuirkBuilder("manufacturer", "model").adds_entity(
            Switch,
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            unique_id_suffix="added",
            child_device_id=["a"],
        )

    with pytest.raises(TypeError):
        QuirkBuilder("manufacturer", "model").replaces_entity(
            Switch,
            Switch,
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            child_device_id=1,
        )


class DeviceValueSensor(BaseSensor):
    """Sensor bound to the device, with a fixed value."""

    _unique_id_suffix = "device_value"

    @property
    def native_value(self) -> int:
        """Return the value."""
        return 5


class PartTemperature(Temperature):
    """Temperature sensor subclass replacing the default one."""


async def test_added_entities_child_device() -> None:
    """Test added and replacing entities can be assigned to child devices."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("CentraLite", "3405-L")
        .child_device("part", fallback_name="Part")
        .adds_entity(
            DeviceValueSensor, fallback_name="Device value", child_device_id="part"
        )
        .replaces_entity(
            Temperature,
            PartTemperature,
            endpoint_id=1,
            cluster_id=TemperatureMeasurement.cluster_id,
            child_device_id="part",
        )
        .add_to_registry(registry)
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "centralite-3405-l-0x10025310.json", registry
        )
        added = device.get_platform_entity(
            Platform.SENSOR, unique_id="00:0d:6f:00:05:65:83:f2-device_value"
        )
        (replacing,) = (
            entity
            for entity in device.platform_entities.values()
            if type(entity) is PartTemperature
        )

        assert set(device.child_devices) == {"part"}
        assert added.child_device is device.child_devices["part"]
        assert replacing.child_device is device.child_devices["part"]


def test_clone_child_devices() -> None:
    """Test cloning a quirk copies its child devices."""
    template = QuirkBuilder("manufacturer", "model").child_device(
        "left", endpoint_id=1, fallback_name="Left"
    )

    clone = template.clone().applies_to("manufacturer", "model2")
    clone.child_device("right", endpoint_id=2, fallback_name="Right")

    assert [child_device.id for child_device in template.child_devices] == ["left"]
    assert [child_device.id for child_device in clone.child_devices] == [
        "left",
        "right",
    ]

    disabled = QuirkBuilder("manufacturer", "model").disable_child_devices().clone()
    assert disabled.child_devices == []
