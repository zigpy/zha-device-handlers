"""General quirk v2 tests."""

import collections
import itertools

import zigpy.quirks
from zigpy.quirks.v2 import (
    EntityPlatform,
    EntityType,
    QuirksV2RegistryEntry,
    ZCLEnumMetadata,
)

import zhaquirks

zhaquirks.setup()

# zigpy registry v2 contains duplicates (due to being keyed by manufacturer and model),
# so to avoid duplicates but maintain insertion order, we use a dict instead of a set
ALL_QUIRK_V2_CLASSES: dict[QuirksV2RegistryEntry, None] = dict.fromkeys(
    itertools.chain.from_iterable(zigpy.quirks.DEVICE_REGISTRY.registry_v2.values())
)


def test_translation_key_and_fallback_name_match() -> None:
    """Ensure quirks v2 entities sharing the same translation key also share the same fallback name.

    This is needed as Home Assistant has a strings.json file that maps translation keys to names.
    This file is updated when bumping ZHA in HA. By default, the friendly name is the fallback name.
    """

    # translation_key -> {(quirk_location, fallback_name)}
    translation_key_map: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)

    # collect all translation keys and their quirk location and fallback names
    for quirk in ALL_QUIRK_V2_CLASSES:
        for entity_metadata in quirk.entity_metadata:
            if (translation_key := entity_metadata.translation_key) is None:
                continue
            quirk_location = f"{quirk.quirk_file}:{quirk.quirk_file_line}"
            translation_key_map[translation_key].add(
                (quirk_location, entity_metadata.fallback_name)
            )

    # check that if multiple entity metadata entries exist for the same translation key,
    # the fallback name is the same for all of them
    for translation_key, quirks in translation_key_map.items():
        if len(quirks) > 1:
            quirk_locations, fallback_names = zip(*quirks)
            # check that only one fallback name exists for the translation key
            # if not, we print the quirk locations to help identify the issue
            assert len(set(fallback_names)) == 1, (
                f"Translation key '{translation_key}' is shared by quirks with different fallback names: {quirk_locations}"
            )


def test_manufacturer_model_metadata_unique() -> None:
    """Ensure that each manufacturer-model pair is unique across all v2 quirks."""
    # quirk_locations are a list and not a set below,
    # as they are not guaranteed to be unique when set up incorrectly

    # (manufacturer, model) -> {quirk_location}
    man_model_quirk_map: dict[tuple[str, str], list[str]] = collections.defaultdict(
        list
    )

    for quirk in ALL_QUIRK_V2_CLASSES:
        for metadata in quirk.manufacturer_model_metadata:
            man_model_quirk_map[(metadata.manufacturer, metadata.model)].append(
                f"{quirk.quirk_file}:{quirk.quirk_file_line}"
            )

    # check that each manufacturer-model pair is unique
    for (manufacturer, model), quirk_locations in man_model_quirk_map.items():
        assert len(quirk_locations) == 1, (
            f"Manufacturer-model pair '{manufacturer}' '{model}' is shared by multiple quirks: {quirk_locations}"
        )


def test_enum_sensor_category() -> None:
    """Ensure enum metadata with sensor entity platform has valid entity category."""
    for quirk in ALL_QUIRK_V2_CLASSES:
        for entity_metadata in quirk.entity_metadata:
            if (
                isinstance(entity_metadata, ZCLEnumMetadata)
                and entity_metadata.entity_platform is EntityPlatform.SENSOR
            ):
                assert entity_metadata.entity_type in (
                    EntityType.STANDARD,
                    EntityType.DIAGNOSTIC,
                ), (
                    f"Enum sensor '{entity_metadata.translation_key}' in "
                    f"{quirk.quirk_file}:{quirk.quirk_file_line} "
                    f"has invalid entity type '{entity_metadata.entity_type}'"
                )
