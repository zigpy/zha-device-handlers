# Unique IDs

HA uses `unique_id` to identify an entity across restarts. If a quirk change causes it to change, HA treats the result as a new entity — the old one is orphaned and anything referencing it breaks.

**For v2 quirk entities** the format is:

```
{device.ieee}-{endpoint_id}-{suffix}
```

Note there is **no cluster_id** between the endpoint and the suffix. This differs from the format used by ZHA-native entities (see below).

`{suffix}` resolves in this order:
1. Explicit `unique_id_suffix=` on the builder call
2. Otherwise `attribute_name` (attribute-based entities)
3. Otherwise `command_name` (for `.command_button()`)
4. Otherwise no suffix

Entities from `.adds_entity()` use the same format, with `{suffix}` from `unique_id_suffix=` or else the class's own suffix. Device-bound ones have no endpoint: `{device.ieee}-{suffix}`.

**Breaking-change implications:**
- Renaming `attribute_name` on a custom cluster used by an existing v2 quirk changes the default suffix and **breaks existing entities**. Avoid unless necessary.
- Moving an entity to a different `endpoint_id` also changes the unique_id and breaks existing entities.
- `translation_key` and `fallback_name` do **not** affect unique_id — renaming these is safe.
- If a rename is genuinely required, preserve the old suffix via `unique_id_suffix=` on each affected entity. Flag the breakage in the PR.
- When reviewing PRs that rename attributes in an existing v2 quirk (or move entities to different endpoints), call this out before it lands.

**ZHA-native entities (not created by a v2 quirk):**

Some entities are not created by a v2 quirk's entity declarations — they come from a class defined in the ZHA library itself. These entities go through ZHA's standard discovery path in `ZclPlatformEntity.__init__`, which uses a different format:

```
{device.ieee}-{endpoint_id}-{cluster_id}-{suffix}
```

The cluster_id appears as a decimal integer. `{suffix}` comes from a hardcoded `_unique_id_suffix` class attribute on the ZHA-native entity class (typically matching the entity's `_attribute_name`, e.g. `"power_outage_memory"`, `"invert_switch"`, `"child_lock"`).

Note: several primary platform-entity classes use a shorter legacy `{ieee}-{endpoint_id}` format (no cluster_id, no suffix) for backwards compatibility — `Light`, `Shade`, `DeviceTracker`, `Switch` (main OnOff on light/smart-plug/ballast/plug-in-unit device types), and `Cover`/`Thermostat`/`Siren` when the endpoint's device type matches the entity's primary type. Config switches, numbers and sensors on the same device normally use the standard cluster_id-included format above, except that config switches (`ConfigurableAttributeSwitch`) on ballast, plug-in-unit and smart-plug endpoints also leave out the cluster_id. Check the existing unique_id in a diagnostics file before choosing the suffix.

When migrating such an entity to a quirks v2 definition, the v2 entity must produce the same unique_id as the old one or HA will treat it as a new entity. Because v2 quirk unique_ids do **not** auto-include the cluster_id, the v2 `unique_id_suffix=` must reproduce whatever sits between the endpoint ID and the suffix in the existing ID (usually the cluster_id).

Example: for a ZHA-native entity on cluster_id `0xFCC0` (= `64704`) with attribute `child_lock`, the existing unique_id is `{ieee}-1-64704-child_lock`. To preserve that under v2, pass `unique_id_suffix="64704-child_lock"` on the corresponding `.switch(...)` call to get the same unique_id.

If you have access to a checkout of the ZHA library, you can find existing unique_ids in the device diagnostics dumps under `zha/tests/data/devices/`.

The code: `quirk_unique_id_base()` in `zhaquirks/builder/discovery.py` and `EntityMetadata.resolved_unique_id_suffix` in `zhaquirks/builder/metadata.py`.
