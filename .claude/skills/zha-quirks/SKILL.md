---
name: zha-quirks
description: Reference for writing, changing or reviewing ZHA quirks in zha-device-handlers. Covers QuirkBuilder and TuyaQuirkBuilder methods, entity options (number multiplier, enums, buttons, custom entity classes), unique_id stability and migrating ZHA-native entities, custom clusters and manufacturer_code, firmware filters, legacy v1 quirks, test fixtures, and known pitfalls. Use when adding device support or touching anything under zhaquirks/ or tests/.
---

# Writing ZHA quirks

The always-loaded rules are in `AGENTS.md`; this skill holds the detailed reference. The source of truth for every signature and default is `zhaquirks/builder/builder.py`; read it when this skill and the code disagree.

Load the companion file for the task at hand:

- [entities.md](entities.md): entity methods (`.sensor()`, `.number()`, `.enum()`, buttons, …), number `multiplier` semantics, device automation triggers, hiding or changing default entities, custom entity classes
- [unique-ids.md](unique-ids.md): unique ID format, breaking changes, migrating ZHA-native entities to a quirk
- [clusters.md](clusters.md): custom clusters, `manufacturer_code`, `access`, enum types, `_CONSTANT_ATTRIBUTES`, accessing clusters, handling commands
- [tuya.md](tuya.md): `TuyaQuirkBuilder` and Tuya-specific rules
- [legacy-v1.md](legacy-v1.md): v1 `CustomDevice` quirks (only for changing existing ones)
- [testing.md](testing.md): fixtures, when tests are needed, end-to-end tests with diagnostics

## Zigbee Concepts

**Clusters**: Functionality groupings containing attributes and commands.
- **in_clusters** (Server clusters): Control the device, send attribute reports. E.g., `OnOff` on a light bulb.
- **out_clusters** (Client clusters): Send commands to other devices. E.g., `OnOff` on a remote control.

**Endpoints**: Groupings of clusters. Multi-gang switches have separate endpoints per switch.

## V2 quirks

Use `QuirkBuilder` from `zhaquirks.builder` for declarative quirk definition:

```python
from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("Manufacturer", "Model")
    .applies_to("AltManufacturer", "Model")  # Additional models
    .replaces(CustomClusterClass)             # Replace standard cluster
    .device_automation_triggers({...})        # Button/action mappings
    .switch(attribute_name=..., fallback_name=...)  # HA entity
    .add_to_registry()
)
```

### QuirkBuilder methods

**Device Matching:**
- `.applies_to(manufacturer, model)` - Add manufacturer/model pair to match (`also_applies_to` is an alias; use `applies_to`)
- `.filter(filter_function)` - Custom filter function `(device) -> bool`
- `.firmware_version_filter(min_version, max_version, allow_missing)` - Filter by firmware version

Firmware version filtering is useful when different firmware versions need different quirks:
```python
# Quirk for OLD firmware (before bug was fixed)
(
    QuirkBuilder("innr", "SP 240")
    .firmware_version_filter(max_version=0x191B3685, allow_missing=False)
    .replaces(OldFirmwareCluster)
    .add_to_registry()
)

# Quirk for NEW firmware (after bug was fixed)
(
    QuirkBuilder("innr", "SP 240")
    .firmware_version_filter(min_version=0x191B3685, allow_missing=True)
    .replaces(NewFirmwareCluster)
    .add_to_registry()
)
```
- `min_version`: Minimum firmware version (inclusive)
- `max_version`: Maximum firmware version (exclusive) - the version specified is NOT included
- `allow_missing`: If `True`, quirk applies when device has no firmware version

Note: In the example above, `0x191B3685` appears in both quirks because `max_version` is exclusive (old quirk applies to versions *before* this) while `min_version` is inclusive (new quirk applies to this version *and newer*).

**Cluster Modification:**
- `.adds(cluster, cluster_type=ClusterType.Server, endpoint_id=1, constant_attributes=None)` - Add a cluster the device doesn't have. `constant_attributes` forces attribute values like `_CONSTANT_ATTRIBUTES` on a custom cluster, keyed by `ZCLAttributeDef` (e.g. `{Metering.AttributeDefs.divisor: 100}`); the cluster must then be a `CustomCluster` subclass
- `.removes(cluster_id, cluster_type=ClusterType.Server, endpoint_id=1)` - Remove a cluster
- `.replaces(replacement_cluster_class, cluster_id=None, cluster_type=ClusterType.Server, endpoint_id=1)` - Replace an existing cluster with a custom implementation. `cluster_id` is only needed when the removed cluster's ID differs from the replacement's
- `.replace_cluster_occurrences(replacement_cluster_class, replace_server_instances=True, replace_client_instances=True)` - Replace across all endpoints

Use `.replaces()`, not `.adds()`, for a cluster the device already has: `.replaces()` carries the existing attribute cache over to the new cluster, `.adds()` doesn't. When you pass `cluster_type` or `endpoint_id`, pass them as keywords: their positions differ between methods.

`cluster_type` can be `ClusterType.Server` (in_clusters) or `ClusterType.Client` (out_clusters).

**Endpoint Modification:**
- `.adds_endpoint(endpoint_id, profile_id, device_type)`
- `.removes_endpoint(endpoint_id)`
- `.replaces_endpoint(endpoint_id, profile_id, device_type)` - Change endpoint's profile/device type

Example: Change device type so HA creates correct entity (ZHA profile used by default):
```python
.replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
```

**Other Methods:**
- `.friendly_name(model="...", manufacturer="...")` - Override the device name shown in HA (e.g. `model="Hue OmniGlow lightstrip", manufacturer="Philips"` instead of a model code)
- `.zigpy_device_class(cls)` - Replace the zigpy device with a `BaseCustomDevice` subclass (e.g., for special request handling)
- `.zha_device_class(cls)` - Use a `QuirkV2Device` subclass as the ZHA device
- `.skip_configuration()` - Skip attribute reporting configuration
- `.clone()` - Copy a builder so variants can share a base (see below)
- `.add_to_registry()` - **Required** - Registers the quirk. A builder without it registers nothing, silently

**Sharing a base between models with `.clone()`:** build the base without manufacturer/model and never register it; add `.applies_to()` on each clone:
```python
base_quirk = (
    QuirkBuilder()
    .replaces(VendorCluster)
    .device_automation_triggers({...})
)
base_quirk.clone().applies_to("Manufacturer", "ModelA").add_to_registry()
base_quirk.clone().applies_to("Manufacturer", "ModelB").add_to_registry()
```
If the models need nothing different, use one builder with several `.applies_to()` calls instead.

## Pitfalls

Each of these has shipped in a PR before; check the ones that apply.

- A new `zhaquirks/<vendor>/` directory without `__init__.py` is never imported: the quirk does nothing and CI still passes. Testing it as a custom quirk doesn't catch this, because a custom quirk file is loaded as a top-level module.
- A custom cluster that subclasses a ZCL cluster without `CustomCluster` (`class FooBasic(Basic)`) pollutes zigpy's global cluster registry. Use `class FooBasic(CustomCluster, Basic)`.
- `.prevent_default_entity_creation()` / `.removes_entity()` and `.change_entity_metadata()` match *every* entity on the device, including the quirk's own. A filter of only `endpoint_id` + `cluster_id` also removes (or changes) the entities the quirk adds on that cluster; narrow it with `unique_id_suffix=`, or with `EntityFilter(entity_cls=..., platform=...)` in `.removes_entity()`.
- `.adds_endpoint()` does nothing when the endpoint already exists; use `.replaces_endpoint()` to change its profile or device type.
- `.enum()` on a read-only attribute defaults to a select that issues failing writes; pass `entity_platform=EntityPlatform.SENSOR` with `entity_type=EntityType.DIAGNOSTIC` or `STANDARD`.
- An attribute typed as a `t.enum8` subclass is written as ZCL `enum8`. If the device expects `uint8`, it rejects the write; set `zcl_type=DataTypeId.uint8` on the `ZCLAttributeDef` and keep the enum for the option names.
- A `write_attributes` override that writes something else first must return the result of the user's write first: ZHA only checks `result[0]`, so `side_result + user_result` reports a failed write as success. Do the side write, then `return await super().write_attributes(...)`.
- A hand-written `TuyaMCUCluster` subclass that defines `dp_to_attribute` but not `data_point_handlers` never handles reports (`handle_get_data()` looks up `data_point_handlers` first). `TuyaQuirkBuilder` fills in both.
- Setting attribute values in a cluster's `__init__` doesn't survive an HA restart: the attribute cache is cleared and reloaded from the database after quirks are applied. Only local-only attributes on a `LocalDataCluster` can get defaults, through `_DEFAULT_VALUES`.
- `QuirkBuilder.sensor(suggested_display_precision=...)` is stored but not passed on to the ZHA entity; it has no effect.

## Key imports

Import the quirks API from `zhaquirks.builder`, `zhaquirks.clusters` and `zhaquirks.legacy`. The old `zigpy.quirks` / `zigpy.quirks.v2` paths are deprecated shims; don't use them.

```python
# Constants for signatures
from zhaquirks.const import (
    MODELS_INFO, ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS,
    PROFILE_ID, DEVICE_TYPE, SKIP_CONFIGURATION,
)

# Device automation triggers
from zhaquirks.const import (
    SHORT_PRESS, LONG_PRESS, DOUBLE_PRESS, TRIPLE_PRESS,
    COMMAND, COMMAND_ON, COMMAND_OFF, COMMAND_TOGGLE,
)

# Quirk building
from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder import EntityFilter, EntityPlatform, EntityType
from zhaquirks.builder import (  # Unit constants
    UnitOfTemperature, UnitOfTime, UnitOfEnergy, UnitOfPower,
)
from zhaquirks.builder import BinarySensorDeviceClass
from zhaquirks.builder import NumberDeviceClass
from zhaquirks.builder import SensorDeviceClass, SensorStateClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder

# Cluster types
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, OnOff, Groups, Scenes
from zigpy.zcl.clusters.measurement import TemperatureMeasurement, RelativeHumidity
import zigpy.types as t
```

