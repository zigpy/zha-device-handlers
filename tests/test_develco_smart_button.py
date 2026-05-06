"""Tests for Develco smart button."""

import itertools

import zigpy.quirks
from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff

import zhaquirks
from zhaquirks.develco.smart_button import ButtonState, CustomOnOff

zhaquirks.setup()


def _get_smart_button_quirk():
    """Return the registered smart button quirk entry."""
    for quirk in itertools.chain.from_iterable(
        zigpy.quirks.DEVICE_REGISTRY.registry_v2.values()
    ):
        manufacturer_models = {
            (metadata.manufacturer, metadata.model)
            for metadata in quirk.manufacturer_model_metadata
        }
        if ("frient A/S", "SBTZB-110") in manufacturer_models or (
            "Develco Products A/S",
            "SBTZB-110",
        ) in manufacturer_models:
            return quirk

    raise AssertionError("smart_button quirk not registered")


def test_sbtzb110_quirk_metadata():
    """Test the smart button quirk exposes the expected v2 entity metadata."""
    quirk = _get_smart_button_quirk()

    assert ("frient A/S", "SBTZB-110") in {
        (metadata.manufacturer, metadata.model)
        for metadata in quirk.manufacturer_model_metadata
    }
    assert ("Develco Products A/S", "SBTZB-110") in {
        (metadata.manufacturer, metadata.model)
        for metadata in quirk.manufacturer_model_metadata
    }

    entity_map = {
        entity_metadata.translation_key: entity_metadata
        for entity_metadata in quirk.entity_metadata
        if entity_metadata.translation_key is not None
    }

    assert entity_map["frient_button_press_action_delay"].fallback_name == (
        "Button press action delay"
    )
    assert entity_map["button_press_blink_led"].entity_type is EntityType.CONFIG
    assert entity_map["button_state"].entity_platform is EntityPlatform.SENSOR
    assert entity_map["button_state"].entity_type is EntityType.STANDARD
    assert entity_map["button_state"].fallback_name == "Button state"


def test_sbtzb110_button_state_enum():
    """Test the button state enum matches released and pressed values."""
    assert ButtonState.Released == 0
    assert ButtonState.Pressed == 1


def test_sbtzb110_custom_onoff_cluster_metadata():
    """Test the custom OnOff cluster keeps the expected manufacturer attributes."""
    assert CustomOnOff.cluster_id == OnOff.cluster_id
    assert (
        CustomOnOff.AttributeDefs.button_press_action_delay.manufacturer_code == 0x1015
    )
    assert CustomOnOff.AttributeDefs.button_press_blink_led.manufacturer_code == 0x1015
    assert BinaryInput.cluster_id == 0x000F
    assert ClusterType.Client.name == "Client"
