"""General quirk v2 tests."""

import collections
import itertools

import zigpy.quirks
from zigpy.quirks.v2 import QuirksV2RegistryEntry

import zhaquirks

zhaquirks.setup()


ALL_QUIRK_V2_CLASSES: list[QuirksV2RegistryEntry] = itertools.chain.from_iterable(
    zigpy.quirks._DEVICE_REGISTRY._registry_v2.values()
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
            assert (
                len(set(fallback_names)) == 1
            ), f"Translation key '{translation_key}' is shared by quirks with different fallback names: {quirk_locations}"
