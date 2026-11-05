This file provides guidance to AI coding agents (and AI code review) working in this repository. Detailed references live in skills, listed at the end; load the matching skill before writing or reviewing quirk code.

## Overview

ZHA-Quirks provides device-specific handlers for ZHA (Zigbee Home Automation) in Home Assistant. Quirks handle devices that don't follow the Zigbee Cluster Library (ZCL) specification by defining custom attributes, clusters, and entity mappings.

## Commands

```bash
script/setup                            # uv sync + pre-commit install
uv sync                                 # after switching branches or pulling
uv run pytest tests/                    # all tests
uv run pytest tests/test_tuya.py -k name  # one file / one test
uv run pre-commit run --all-files       # ruff, ruff format, mypy, codespell
```

## Where things are

The quirks API lives in this repository, so read the source for exact signatures and defaults instead of guessing:

- `zhaquirks/builder/builder.py`: `QuirkBuilder` and its cluster/endpoint operations
- `zhaquirks/builder/metadata.py`: entity metadata, `EntityFilter`, `ReportingConfig`
- `zhaquirks/builder/discovery.py`: how quirk metadata becomes ZHA entities (unique IDs, which options are forwarded)
- `zhaquirks/tuya/builder/__init__.py`: `TuyaQuirkBuilder`; the root `tuya.md` explains Tuya datapoints
- `zhaquirks/clusters.py` (`CustomCluster`), `zhaquirks/__init__.py` (`LocalDataCluster`, `EventableCluster`), `zhaquirks/legacy/` (v1 `CustomDevice`), `zhaquirks/const.py`
- `tests/conftest.py` (fixtures), `tests/zha_helpers.py` (end-to-end helpers), `tests/data/devices/` (diagnostics files for those tests)
- zigpy provides ZCL clusters and types (`zigpy.zcl.clusters.*`, `zigpy.types`); the `zha` package provides the entity classes

Quirks are organized by manufacturer in `zhaquirks/<manufacturer>/`. Every such directory needs an `__init__.py`, or its quirks are never imported (and CI still passes). `__init__.py` holds code shared by several device files; a cluster used by one device stays in that device's file. Tuya devices go in `zhaquirks/tuya/` whatever the brand on the box.

## Before writing a quirk

1. **Check for existing support.** Search `zhaquirks/` for the manufacturer and model strings, and open PRs for the model. If a quirk already covers the device or a close variant, extend it with `.applies_to()` instead of adding a second quirk; never register the same manufacturer/model pair twice, unless the quirks are split by `.firmware_version_filter()`.
2. **New quirks use `QuirkBuilder`** (`TuyaQuirkBuilder` for Tuya devices). Only touch v1 `CustomDevice` quirks to change an existing one.
3. **Work from real device data**: the device's diagnostics, its signature, attribute reads, the manual. Zigbee2MQTT converters are useful evidence, not authority; copy a mapping only after reading the exact converter, including how it scales values (Z2M's `divideBy10` means the raw value is in tenths). Leave out datapoints or attributes you couldn't verify, and say so in the PR.
4. **Expose real device functionality only.** No invented attributes or virtual config entities that don't change a device setting, no stateless "event" sensors. `LocalDataCluster` is a last resort for values the device reports through another channel; never turn a cluster that talks to the device into one.
5. **Quirks work around device bugs, not ZHA bugs.** When ZHA or zigpy mishandles something for every device of a kind, fix it there instead of adding retries, debouncing or workarounds to a quirk.

## Rules for quirk code

- **Imports:** the quirks API comes from `zhaquirks.builder`, `zhaquirks.clusters` and `zhaquirks.legacy`. Never import from `zigpy.quirks` / `zigpy.quirks.v2` (deprecated shims).
- **No magic numbers** for IDs that have a definition: use `OnOff.cluster_id`, `Metering.AttributeDefs.divisor.id` / `.name`, `WindowCovering.ServerCommandDefs.go_to_lift_percentage.id`. A new attribute's ID goes inline in its `ZCLAttributeDef`, not in a module constant. Pass `attribute_name=Cluster.AttributeDefs.x.name` for an attribute that already has a definition, not a string literal, so typos fail at import (Tuya builder methods that create the attribute take a plain name).
- **Entity names:** every entity needs `fallback_name`, in English sentence case ("Soil moisture", not "Soil Moisture"; abbreviations like LED stay uppercase). `translation_key` is required when no `device_class` names the entity, and must map to the same `fallback_name` everywhere in the repo, unless the entity uses `translation_placeholders` (`test_translation_key_and_fallback_name_match`); reuse an existing key for the same meaning. Button names are actions ("Calibrate sensor").
- **Units:** use the `UnitOf*` constants from `zhaquirks.builder`, never strings like `"°C"`. Temperature offsets and hysteresis use `NumberDeviceClass.TEMPERATURE_DELTA`. Only use a unit the chosen device class allows.
- **Defaults:** don't pass arguments that equal their default. Default `entity_type`: `.sensor()` STANDARD, `.binary_sensor()` DIAGNOSTIC, everything else CONFIG. An entity the user can change is never DIAGNOSTIC. `.enum()` is a writable select; for a read-only attribute pass `entity_platform=EntityPlatform.SENSOR` and `entity_type=EntityType.DIAGNOSTIC` or `STANDARD` (an enum sensor can't be CONFIG).
- **Unique IDs:** a v2 quirk entity's unique ID is `{ieee}-{endpoint_id}-{unique_id_suffix or attribute_name}`. Renaming an attribute or moving an entity to another endpoint orphans existing users' entities. After a rename, keep the old ID with `unique_id_suffix=`; don't move entities between endpoints. Flag either in the PR. Details in the `zha-quirks` skill.
- **Vendor attributes:** set `manufacturer_code=` on manufacturer-specific attributes of standard clusters (attributes of a `0xFC00`+ cluster default to the device's manufacturer ID); new code uses `manufacturer_code`, not `is_manufacturer_specific`.
- **Reporting:** configure reporting with `reporting_config=ReportingConfig(...)`, not by overriding cluster configuration methods. `.skip_configuration()` only for devices that reject binding/reporting.
- **Firmware variants:** split behaviour by firmware with `.firmware_version_filter()` (min inclusive, max exclusive), not by guessing at runtime.
- **Comments:** one-line docstrings; no comments that restate the code or narrate the change; no unused enums or constants.
- **Don't** seed attribute values in a cluster `__init__` (wiped on every HA restart; local-only attributes on a `LocalDataCluster` can use `_DEFAULT_VALUES`), or subclass a ZCL cluster without `CustomCluster` first (`class Foo(CustomCluster, OnOff)`).

## Tests

- Purely declarative quirks need no tests: `QuirkBuilder` definitions, `.applies_to()` additions, triggers, `_CONSTANT_ATTRIBUTES`, existing custom clusters. `tests/test_quirks.py` and `tests/test_quirks_v2.py` validate every quirk, and once a device's diagnostics are in ZHA's test data, ZHA's snapshot tests cover the entities its quirk creates.
- Add tests for custom logic: overridden cluster methods (`handle_cluster_request`, `_update_attribute`, `write_attributes`), value parsing, command handling, non-trivial filters, custom entity classes.
- Don't add signature match tests (`assert_signature_matches_quirk`) or tests that only assert what the builder produced.
- Fixtures: `zigpy_device_from_v2_quirk(manufacturer, model)` for v2 quirks, `zigpy_device_from_quirk(QuirkClass)` for v1. Details in the `zha-quirks` skill.

## Pull requests and issues

AI tools are welcome, but the human contributor must understand and be able to explain every change, and answer review questions in their own words. Don't open issues or PRs autonomously. Follow the [Open Home Foundation AI policy](https://contributors.home-assistant.io/start/ai-policy/).

When writing a PR or issue on a user's behalf:

- **Diagnostics:** new device support and device bugs need the device's diagnostics file (HA device page → ⋮ → "Download diagnostics"). You can't generate it: ask the user to attach the unmodified `.json` file. Don't paste it inline, summarise it, edit it, offer to "attach it if needed", or write "N/A".
- **Templates:** keep every template heading, delete placeholder text you don't fill, and tick only checklist items that are true.
- **PR title:** a changelog line with a leading verb, no `Device:` prefix, no trailing period ("Add Sonoff SNZB-01M scene remote").
- **PR description:** describe the final diff, link the issue (`Fixes #N` only for a real fix), and list what wasn't tested on real hardware. Keep it short; no tool footers, session links or emoji.
- **Issues:** check the latest release, existing issues and PRs first. Keep what you observed apart from what you suspect; don't name ZHA/zigpy code you haven't read. Say whether custom quirks are loaded. Only post a custom quirk the user has actually run.
- Run `uv run pre-commit run --all-files` before pushing.

## Skills

Skills live in `.claude/skills/` (also reachable as `.agents/skills/`). Tools that don't load skills automatically can read the `SKILL.md` directly.

- `zha-quirks`: full `QuirkBuilder` / `TuyaQuirkBuilder` reference: entity options (number `multiplier`, enums, buttons, custom entity classes), unique ID rules and ZHA-native entity migration, custom clusters, legacy v1 quirks, testing fixtures, and known pitfalls.
