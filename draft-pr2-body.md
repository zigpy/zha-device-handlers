> [!IMPORTANT]
> This depends on #5395, which needs to be merged first. This branch is built on top of it, so the diff here currently includes its commits as well. I'll rebase this once #5395 is merged. Until then, the changes specific to this PR can be seen [here](https://github.com/TheJulianJES/zha-device-handlers/compare/tjj/dont-cache-constant-attributes...tjj/local-data-cluster-reads-no-recache).

## Proposed change

This stops `LocalDataCluster` reads from being fed back into the zigpy attribute cache.

zigpy stores every successful read result through `_update_attribute`, which caches it and emits an event that the appdb persists. That's correct for a device response, but a `LocalDataCluster` serves its reads from the attribute cache or `_DEFAULT_VALUES` itself, so this caused two problems:
- `_DEFAULT_VALUES` were cached and persisted as if the device had reported them. After that, they can't be told apart from real values, and they stick around even if the quirk's default changes.
- Clusters converting values in `_update_attribute` converted already converted values again on every read. For example, Xiaomi `LocalIlluminanceMeasurementCluster` re-applies its `log10` conversion, and Tuya MCU `TuyaPowerConfigurationCluster` doubles the battery percentage again.

`CustomCluster.read_attributes` now hands the attributes that aren't constants to a new `_read_non_constant_attributes` method, which reads them through zigpy as before. `LocalDataCluster` overrides it to build the read result itself:
- Cached values (with `allow_cache` / `only_cache`) are served through a zigpy cache-only read, which has no side effects.
- Everything else is still read through `read_attributes_raw`, so subclasses overriding it (XBee PWM) keep working, but the result is not passed through `_update_attribute`.
- Attributes without a value are still marked unsupported, like zigpy does.
- A successful read still drops a stale unsupported mark, like zigpy did before.

## Additional information

This also fixes the double conversion reported in #5287. That PR suppresses the `_update_attribute` echo by tracking the attribute IDs a read returned, whereas this doesn't route local reads through `_update_attribute` at all, which covers `_DEFAULT_VALUES` as well. If this approach is preferred, it would supersede #5287 (the two conflict). Thanks for the report and analysis there!

Behavior changes:
- Local reads no longer emit `AttributeReadEvent` / `AttributeUpdatedEvent`. ZHA reads entity state through `get()`, which still returns `_DEFAULT_VALUES`. I went through all 246 `LocalDataCluster` subclasses and couldn't find anything relying on these events or on the `_update_attribute` call during reads.
- `_update_attribute` overrides no longer run on reads. Apart from the conversion fixes above, this means `TuyaMotionWithReset` no longer restarts its reset timer when an active motion state is force-read (e.g. via `update_entity`), and `TuyaPM25ConcentrationIgnoreValues` no longer filters values it already filtered when they were reported.
- Unknown attributes now raise the `KeyError` in `CustomCluster.read_attributes` instead of in zigpy. It's the same exception, still raised before any request.

Not changed:
- Unsupported marks on local clusters are still persisted. Changing that would affect when entities are created for many quirks.
- Default values already persisted in existing databases are not cleaned up.
- ZHA diagnostics read through `get()`, so default values still show up there. Values that were converted twice may change when the ZHA device snapshots are regenerated.

## Checklist

- [ ] The changes are tested and work correctly
- [x] `pre-commit` checks pass / the code has been formatted using Black
- [x] Tests have been added to verify that the new code works
- [ ] Device diagnostics data has been attached
