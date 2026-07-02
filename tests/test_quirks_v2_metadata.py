"""Quirks v2 entity-metadata tests migrated from zigpy."""

import pytest
from zha.application import EntityPlatform, EntityType
from zha.application.platforms.sensor.device_class import (
    SensorDeviceClass,
    SensorStateClass,
)
from zha.quirks import DeviceRegistry
from zha.units import UnitOfTime
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.metadata import (
    BinarySensorMetadata,
    ChangedEntityMetadata,
    DeviceAlertLevel,
    DeviceAlertMetadata,
    ExposesFeatureMetadata,
    NumberMetadata,
    PreventDefaultEntityCreationMetadata,
    SwitchMetadata,
    WriteAttributeButtonMetadata,
    ZCLCommandButtonMetadata,
    ZCLEnumMetadata,
    ZCLSensorMetadata,
)


def test_quirks_v2_sensor():
    """Test adding a quirk that defines a sensor to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .sensor(
            OnOff.AttributeDefs.on_time.name,
            OnOff.cluster_id,
            translation_key="on_time",
            fallback_name="On time",
            suggested_display_precision=0,
        )
        .add_to_registry(registry)
    )

    (sensor_metadata,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(sensor_metadata, ZCLSensorMetadata)
    assert sensor_metadata.entity_type == EntityType.STANDARD
    assert sensor_metadata.entity_platform == EntityPlatform.SENSOR
    assert sensor_metadata.cluster_id == OnOff.cluster_id
    assert sensor_metadata.endpoint_id == 1
    assert sensor_metadata.cluster_type == ClusterType.Server
    assert sensor_metadata.attribute_name == OnOff.AttributeDefs.on_time.name
    assert sensor_metadata.divisor == 1
    assert sensor_metadata.multiplier == 1
    assert sensor_metadata.suggested_display_precision == 0


def test_quirks_v2_enum():
    """Test adding a quirk that defines an enum entity to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
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

    (enum_metadata,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(enum_metadata, ZCLEnumMetadata)
    assert enum_metadata.endpoint_id == 1
    assert enum_metadata.cluster_id == OnOff.cluster_id
    assert enum_metadata.cluster_type == ClusterType.Server
    assert enum_metadata.attribute_name == OnOff.AttributeDefs.start_up_on_off.name
    assert enum_metadata.enum == OnOff.StartUpOnOff
    assert enum_metadata.entity_type == EntityType.CONFIG


def test_quirks_v2_sensor_validation_failure_no_translation_key():
    """Test translation key and device class both not set causes exception."""
    registry = DeviceRegistry()

    with pytest.raises(ValueError, match="must have a translation_key or device_class"):
        (
            QuirkBuilder("manufacturer", "model")
            .adds(OnOff.cluster_id)
            .sensor(
                OnOff.AttributeDefs.on_time.name,
                OnOff.cluster_id,
                fallback_name="On time",
            )
            .add_to_registry(registry)
        )


def test_quirks_v2_switch():
    """Test adding a quirk that defines a switch to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .switch(
            OnOff.AttributeDefs.on_time.name,
            OnOff.cluster_id,
            force_inverted=True,
            invert_attribute_name=OnOff.AttributeDefs.off_wait_time.name,
            translation_key="on_time",
            fallback_name="On time",
        )
        .add_to_registry(registry)
    )

    (switch_metadata,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(switch_metadata, SwitchMetadata)
    assert switch_metadata.entity_type == EntityType.CONFIG
    assert switch_metadata.entity_platform == EntityPlatform.SWITCH
    assert switch_metadata.cluster_id == OnOff.cluster_id
    assert switch_metadata.endpoint_id == 1
    assert switch_metadata.cluster_type == ClusterType.Server
    assert switch_metadata.attribute_name == OnOff.AttributeDefs.on_time.name
    assert switch_metadata.force_inverted is True
    assert (
        switch_metadata.invert_attribute_name == OnOff.AttributeDefs.off_wait_time.name
    )


def test_quirks_v2_number():
    """Test adding a quirk that defines a number to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .number(
            OnOff.AttributeDefs.on_time.name,
            OnOff.cluster_id,
            min_value=0,
            max_value=100,
            step=1,
            unit=UnitOfTime.SECONDS,
            translation_key="on_time",
            fallback_name="On time",
        )
        .add_to_registry(registry)
    )

    (number_metadata,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(number_metadata, NumberMetadata)
    assert number_metadata.entity_type == EntityType.CONFIG
    assert number_metadata.entity_platform == EntityPlatform.NUMBER
    assert number_metadata.cluster_id == OnOff.cluster_id
    assert number_metadata.endpoint_id == 1
    assert number_metadata.cluster_type == ClusterType.Server
    assert number_metadata.attribute_name == OnOff.AttributeDefs.on_time.name
    assert number_metadata.min == 0
    assert number_metadata.max == 100
    assert number_metadata.step == 1
    assert number_metadata.unit == "s"
    assert number_metadata.mode is None
    assert number_metadata.multiplier is None


def test_quirks_v2_binary_sensor():
    """Test adding a quirk that defines a binary sensor to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .binary_sensor(
            OnOff.AttributeDefs.on_off.name,
            OnOff.cluster_id,
            translation_key="on_off",
            fallback_name="On/off",
        )
        .add_to_registry(registry)
    )

    (binary_sensor_metadata,) = (
        entry.zha_device_factory.quirk_definition.entity_metadata
    )
    assert isinstance(binary_sensor_metadata, BinarySensorMetadata)
    assert binary_sensor_metadata.entity_type == EntityType.DIAGNOSTIC
    assert binary_sensor_metadata.entity_platform == EntityPlatform.BINARY_SENSOR
    assert binary_sensor_metadata.cluster_id == OnOff.cluster_id
    assert binary_sensor_metadata.endpoint_id == 1
    assert binary_sensor_metadata.cluster_type == ClusterType.Server
    assert binary_sensor_metadata.attribute_name == OnOff.AttributeDefs.on_off.name


def test_quirks_v2_write_attribute_button():
    """Test adding a quirk that defines a write attr button to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .write_attr_button(
            OnOff.AttributeDefs.on_time.name,
            20,
            OnOff.cluster_id,
            translation_key="on_time",
            fallback_name="On time",
        )
        .add_to_registry(registry)
    )

    (write_attribute_button,) = (
        entry.zha_device_factory.quirk_definition.entity_metadata
    )
    assert isinstance(write_attribute_button, WriteAttributeButtonMetadata)
    assert write_attribute_button.entity_type == EntityType.CONFIG
    assert write_attribute_button.entity_platform == EntityPlatform.BUTTON
    assert write_attribute_button.cluster_id == OnOff.cluster_id
    assert write_attribute_button.endpoint_id == 1
    assert write_attribute_button.cluster_type == ClusterType.Server
    assert write_attribute_button.attribute_name == OnOff.AttributeDefs.on_time.name
    assert write_attribute_button.attribute_value == 20


def test_quirks_v2_command_button():
    """Test adding a quirk that defines a command button to the registry."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .command_button(
            OnOff.ServerCommandDefs.on_with_timed_off.name,
            OnOff.cluster_id,
            command_kwargs={"on_off_control": OnOff.OnOffControl.Accept_Only_When_On},
            translation_key="on_with_timed_off",
            fallback_name="On with timed off",
        )
        .command_button(
            OnOff.ServerCommandDefs.on_with_timed_off.name,
            OnOff.cluster_id,
            translation_key="on_with_timed_off",
            fallback_name="On with timed off",
        )
        .add_to_registry(registry)
    )

    button, second_button = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(button, ZCLCommandButtonMetadata)
    assert button.entity_type == EntityType.CONFIG
    assert button.entity_platform == EntityPlatform.BUTTON
    assert button.cluster_id == OnOff.cluster_id
    assert button.endpoint_id == 1
    assert button.cluster_type == ClusterType.Server
    assert button.command_name == OnOff.ServerCommandDefs.on_with_timed_off.name
    assert len(button.kwargs) == 1
    assert button.kwargs["on_off_control"] == OnOff.OnOffControl.Accept_Only_When_On

    # coverage for overridden eq method
    assert button != second_button
    assert button != entry

    assert second_button.kwargs == {}
    assert second_button.args == ()


def test_quirks_v2_friendly_name():
    """Test adding a quirk that defines a friendly name."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .friendly_name(model="Real Model Name", manufacturer="Real Manufacturer")
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

    friendly_name = entry.zha_device_factory.quirk_definition.friendly_name
    assert friendly_name is not None
    assert friendly_name.model == "Real Model Name"
    assert friendly_name.manufacturer == "Real Manufacturer"


def test_quirks_v2_no_friendly_name():
    """Test that a quirk without a friendly name has none set."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
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

    assert entry.zha_device_factory.quirk_definition.friendly_name is None


def test_quirks_v2_device_alerts():
    """Test adding a quirk that defines device alerts."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .device_alert(level="warning", message="This device has routing problems.")
        .device_alert(
            level="error", message="This device irreparably crashes the mesh."
        )
        .add_to_registry(registry)
    )

    assert entry.zha_device_factory.quirk_definition.device_alerts == (
        DeviceAlertMetadata(
            level=DeviceAlertLevel.WARNING,
            message="This device has routing problems.",
        ),
        DeviceAlertMetadata(
            level=DeviceAlertLevel.ERROR,
            message="This device irreparably crashes the mesh.",
        ),
    )


def test_quirks_v2_disable_entity_creation():
    """Test preventing default entity creation."""
    registry = DeviceRegistry()

    def filter_func(entity) -> bool:
        return True

    entry = (
        QuirkBuilder("manufacturer", "model")
        .prevent_default_entity_creation(endpoint_id=1, unique_id_suffix="something")
        .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
        .prevent_default_entity_creation(
            endpoint_id=1, cluster_id=OnOff.cluster_id, cluster_type=ClusterType.Client
        )
        .prevent_default_entity_creation(function=filter_func)
        .add_to_registry(registry)
    )

    assert entry.zha_device_factory.quirk_definition.disabled_default_entities == (
        PreventDefaultEntityCreationMetadata(
            endpoint_id=1,
            cluster_id=None,
            cluster_type=None,
            unique_id_suffix="something",
            function=None,
        ),
        PreventDefaultEntityCreationMetadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Server,  # by default
            unique_id_suffix=None,
            function=None,
        ),
        PreventDefaultEntityCreationMetadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix=None,
            function=None,
        ),
        PreventDefaultEntityCreationMetadata(
            endpoint_id=None,
            cluster_id=None,
            cluster_type=None,
            unique_id_suffix=None,
            function=filter_func,
        ),
    )


def test_quirks_v2_primary_entity():
    """Test that only a single primary entity is allowed."""
    registry = DeviceRegistry()

    builder = (
        QuirkBuilder("manufacturer", "model")
        .adds(OnOff.cluster_id)
        .switch(
            OnOff.AttributeDefs.on_time.name,
            OnOff.cluster_id,
            force_inverted=True,
            invert_attribute_name=OnOff.AttributeDefs.off_wait_time.name,
            translation_key="on_time",
            fallback_name="On time",
            primary=True,
        )
    )

    with pytest.raises(ValueError):
        # Having a second primary entity is not allowed
        builder.sensor(
            OnOff.AttributeDefs.on_time.name,
            OnOff.cluster_id,
            translation_key="on_time",
            fallback_name="On time",
            primary=True,
        )

    entry = builder.add_to_registry(registry)

    entity_metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    assert len(entity_metadata) == 1
    assert entity_metadata[0].primary is True


def test_quirks_v2_change_entity_metadata():
    """Test changing entity metadata functionality."""
    registry = DeviceRegistry()

    def filter_func(entity) -> bool:
        return True

    entry = (
        QuirkBuilder("manufacturer", "model")
        .change_entity_metadata(
            endpoint_id=1,
            unique_id_suffix="something",
            new_primary=True,
        )
        .change_entity_metadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            new_translation_key="custom_key",
            new_translation_placeholders={"index": "subkey"},
        )
        .change_entity_metadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            new_device_class=SensorDeviceClass.POWER,
            new_state_class=SensorStateClass.MEASUREMENT,
            new_entity_category=EntityType.CONFIG,
            new_entity_registry_enabled_default=False,
        )
        .change_entity_metadata(
            function=filter_func,
            new_unique_id="custom_unique_id",
            new_fallback_name="Custom Fallback Name",
        )
        .add_to_registry(registry)
    )

    assert entry.zha_device_factory.quirk_definition.changed_entity_metadata == (
        ChangedEntityMetadata(
            endpoint_id=1,
            cluster_id=None,
            cluster_type=None,
            unique_id_suffix="something",
            function=None,
            new_primary=True,
            new_unique_id=None,
            new_translation_key=None,
            new_translation_placeholders=None,
            new_device_class=None,
            new_state_class=None,
            new_entity_category=None,
            new_entity_registry_enabled_default=None,
            new_fallback_name=None,
        ),
        ChangedEntityMetadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Server,  # by default
            unique_id_suffix=None,
            function=None,
            new_primary=None,
            new_unique_id=None,
            new_translation_key="custom_key",
            new_translation_placeholders={"index": "subkey"},
            new_device_class=None,
            new_state_class=None,
            new_entity_category=None,
            new_entity_registry_enabled_default=None,
            new_fallback_name=None,
        ),
        ChangedEntityMetadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix=None,
            function=None,
            new_primary=None,
            new_unique_id=None,
            new_translation_key=None,
            new_translation_placeholders=None,
            new_device_class=SensorDeviceClass.POWER,
            new_state_class=SensorStateClass.MEASUREMENT,
            new_entity_category=EntityType.CONFIG,
            new_entity_registry_enabled_default=False,
            new_fallback_name=None,
        ),
        ChangedEntityMetadata(
            endpoint_id=None,
            cluster_id=None,
            cluster_type=None,
            unique_id_suffix=None,
            function=filter_func,
            new_primary=None,
            new_unique_id="custom_unique_id",
            new_translation_key=None,
            new_translation_placeholders=None,
            new_device_class=None,
            new_state_class=None,
            new_entity_category=None,
            new_entity_registry_enabled_default=None,
            new_fallback_name="Custom Fallback Name",
        ),
    )


def test_quirks_v2_exposes_feature():
    """Test exposes feature functionality."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .exposes_feature("some_feature")
        .exposes_feature("another_feature", config={"option": True})
        .add_to_registry(registry)
    )

    assert entry.zha_device_factory.quirk_definition.exposes_features == (
        ExposesFeatureMetadata(feature="some_feature"),
        ExposesFeatureMetadata(feature="another_feature", config={"option": True}),
    )


def test_quirks_v2_firmware_version_filter():
    """Test that firmware_version_filter populates the device match."""
    registry = DeviceRegistry()

    entry = (
        QuirkBuilder("manufacturer", "model")
        .firmware_version_filter(min_version=10, max_version=50, allow_missing=False)
        .adds(OnOff.cluster_id)
        .add_to_registry(registry)
    )

    match = entry.device_match
    assert match.firmware_version_min == 10
    assert match.firmware_version_max == 50
    assert match.firmware_version_allow_missing is False
