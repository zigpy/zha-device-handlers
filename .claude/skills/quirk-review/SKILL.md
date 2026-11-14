---
name: quirk-review
description: Checklist for reviewing a pull request to zha-device-handlers (ZHA quirks). Use when reviewing a PR or a diff that adds or changes a quirk, a custom cluster, the quirks builder, or tests. Lists what to check (duplicate support, unique ID breakage, entity naming, units, scaling, diagnostics, tests, known pitfalls) and what not to comment on.
---

# Reviewing a quirks PR

Read `AGENTS.md` (the rules contributors are held to) and the `zha-quirks` skill's Pitfalls section before reviewing. Read the linked issue and the PR description first, then every changed file in full: unique ID stability and naming depend on code outside the diff.

## What to check

1. **Description vs diff.** The title reads like a changelog line (leading verb, no `Device:` prefix, no trailing period). The description matches what the diff actually does now, not an earlier revision. Linked issues are the right ones.
2. **Duplicate support.** Search `zhaquirks/` for the manufacturer and model strings. Flag a quirk for a device that is already supported, a second registration of the same manufacturer/model pair (unless split by `.firmware_version_filter()`), or a new file where `.applies_to()` on an existing quirk would do. Tuya devices belong in `zhaquirks/tuya/`.
3. **Builder choice.** New quirks use `QuirkBuilder` / `TuyaQuirkBuilder`; a new v1 `CustomDevice` or a hand-written `TuyaMCUCluster` needs a reason the builder can't cover.
4. **Unique IDs.** On an existing v2 quirk, a renamed `attribute_name`, a changed `unique_id_suffix`, or an entity moved to another endpoint orphans users' entities. When a v2 entity is declared on a cluster ZHA already creates an entity for (standard clusters, or the vendor config entities in the `zha` package), both are created unless the default one is removed. Details: `zha-quirks` skill, `unique-ids.md`.
5. **Entities.** `fallback_name` in sentence case. A `translation_key` reused with a different `fallback_name` (without `translation_placeholders`) fails `test_translation_key_and_fallback_name_match`. `UnitOf*` constants instead of unit strings, and a unit valid for the device class. Writable entities aren't DIAGNOSTIC. Read-only enums use `entity_platform=EntityPlatform.SENSOR` with a STANDARD or DIAGNOSTIC `entity_type`. Arguments passed with their default value can go.
6. **Values.** Check `divisor`/`multiplier`/`scale` and DP mappings against the device's data or the exact Zigbee2MQTT converter; a number entity on a fractional attribute needs `step` and `multiplier` together. A measurement and its thresholds use the same scale.
7. **Real functionality only.** No invented attributes, virtual config entities, values seeded in a cluster `__init__`, or retries and workarounds for ZHA bugs.
8. **Code.** Imports from `zhaquirks.*`, not `zigpy.quirks*`. Existing IDs referenced through their definitions (`OnOff.cluster_id`, `Cluster.AttributeDefs.x.name`); Tuya builder methods that create an attribute take a plain name. `manufacturer_code` set on vendor attributes of standard clusters. A new vendor directory has `__init__.py`. Custom clusters inherit `CustomCluster` first. `.applies_to()` rather than its alias `.also_applies_to()` (a nit).
9. **Pitfalls.** Walk the `zha-quirks` skill's Pitfalls list against the diff.
10. **Tests.** Custom logic (overridden cluster methods, parsing, command handling, custom entity classes) has tests that exercise it. Declarative quirks don't need tests.
11. **Diagnostics.** A PR adding a new device has the device's diagnostics attached as a `.json` file, unmodified. A pasted signature or an offer to provide it later isn't enough.

## What not to comment on

- Formatting, import order, line length, line endings: pre-commit handles or ignores them.
- Missing tests for declarative quirks, signature tests, or tests that would only restate the builder call.
- Moving new attribute IDs into module constants, or adding `name` / `ep_attribute` to a custom cluster that doesn't need them.
- Anything you can't tie to a line of the diff or a concrete failure. Comment only where you are confident, and once per issue.

## Writing the review

Start with a one-sentence summary. Order findings by impact (broken unique IDs, wrong values, non-working quirk before naming and style), and give each a concrete fix. If the PR looks fine, say so briefly.
