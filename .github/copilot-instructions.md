This file provides guidance to AI coding agents when working with code in this repository.

## Overview

ZHA-Quirks provides device-specific handlers for ZHA (Zigbee Home Automation) in Home Assistant. Quirks handle devices that don't follow standard ZCL (Zigbee Cluster Library) specifications by defining custom attributes, clusters, and entity mappings.

## Commands

```bash
# Setup development environment (includes uv sync and pre-commit install)
script/setup

# Sync dependencies after switching branches or pulling updates
uv sync

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_tuya.py

# Run a specific test function
pytest tests/test_tuya.py::test_function_name -v

# Run pre-commit checks (ruff, mypy, codespell)
pre-commit run --all-files

# Lint and format
ruff check zhaquirks/
ruff format zhaquirks/

# Type checking
mypy zhaquirks/
```

## Zigbee Concepts

**Clusters**: Functionality groupings containing attributes and commands.
- **in_clusters** (Server clusters): Control the device, send attribute reports. E.g., `OnOff` on a light bulb.
- **out_clusters** (Client clusters): Send commands to other devices. E.g., `OnOff` on a remote control.

**Endpoints**: Groupings of clusters. Multi-gang switches have separate endpoints per switch.

## Quirk Architecture

### V2 Quirks (Preferred for New Quirks)

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

#### QuirkBuilder Methods Reference

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

**Entity Creation (Home Assistant):**
All entity methods require `fallback_name`. Common parameters:
- `attribute_name`: ZCL attribute to expose
- `cluster_id`: Cluster containing the attribute
- `endpoint_id`: Endpoint (default 1)
- `translation_key`: For HA translations (required if no device_class)
- `fallback_name`: English name in sentence case (always required)
- `entity_type`: `EntityType.STANDARD`, `CONFIG`, or `DIAGNOSTIC`
- `initially_disabled`: Start disabled in HA
- `device_class`: HA device class for the entity
- `reporting_config`: Configure ZCL attribute reporting
- `unique_id_suffix`: Suffix appended to the entity's unique_id. Defaults to `attribute_name` (or `command_name` for command-based entities). Required when creating multiple entities from the same attribute/command on the same endpoint, since otherwise the default suffixes collide. See **Entity unique_id format** below before changing this on existing quirks.

**Parameter order convention:** `attribute_name`, `cluster_id`, `endpoint_id` first; `translation_key` and `fallback_name` always last (in that order). Use keyword arguments for clarity.

`reporting_config` sets up automatic attribute reporting from the device:
```python
from zhaquirks.builder import ReportingConfig

.sensor(
    attribute_name=VOCIndex.AttributeDefs.measured_value.name,
    cluster_id=VOCIndex.cluster_id,
    reporting_config=ReportingConfig(
        min_interval=60,      # Minimum seconds between reports
        max_interval=120,     # Maximum seconds between reports
        reportable_change=1,  # Minimum change to trigger report
    ),
    ...
)
```

**Entity Methods:** (`VendorCluster` stands for your `CustomCluster` subclass. Arguments marked "Optional" can be left out; the values shown are examples, not always the defaults, so check `builder.py` and leave out any argument that equals its default)
```python
# Switch (on/off control)
.switch(
    attribute_name=VendorCluster.AttributeDefs.led_enable.name,
    cluster_id=VendorCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server; use ClusterType.Client for out_clusters
    force_inverted=False,             # Optional: invert on/off
    off_value=0,                      # Optional: value written when turning off (default 0)
    on_value=1,                       # Optional: value written when turning on (default 1)
    translation_key="led_enable",
    fallback_name="LED enable",
)

# Sensor (read-only value)
.sensor(
    attribute_name=VendorCluster.AttributeDefs.temperature.name,
    cluster_id=VendorCluster.cluster_id,
    cluster_type=ClusterType.Server,          # Optional: default Server
    divisor=100,                              # Optional: divide raw value (default 1)
    multiplier=1,                             # Optional: multiply raw value (default 1)
    device_class=SensorDeviceClass.TEMPERATURE,  # Optional: HA device class
    state_class=SensorStateClass.MEASUREMENT,    # Optional: HA state class
    unit=UnitOfTemperature.CELSIUS,           # Optional: use unit constants, not strings
    translation_key="temperature",
    fallback_name="Temperature",
)

# Binary Sensor (on/off state)
.binary_sensor(
    attribute_name=VendorCluster.AttributeDefs.occupancy.name,
    cluster_id=VendorCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    device_class=BinarySensorDeviceClass.OCCUPANCY,  # Optional: HA device class
    translation_key="occupancy",
    fallback_name="Occupancy",
)

# Binary Sensor with attribute_converter (extract bit from zone_status)
.binary_sensor(
    attribute_name=IasZone.AttributeDefs.zone_status.name,
    cluster_id=IasZone.cluster_id,
    endpoint_id=44,
    device_class=BinarySensorDeviceClass.TAMPER,
    attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
    unique_id_suffix="tamper",  # Required when multiple entities use same attribute
    fallback_name="Tamper",
)

# Number (adjustable value)
.number(
    attribute_name=VendorCluster.AttributeDefs.off_to_on_delay.name,
    cluster_id=VendorCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    min_value=0,                      # Optional: minimum allowed value
    max_value=65535,                  # Optional: maximum allowed value
    step=1,                           # Optional: step increment
    unit=UnitOfTime.SECONDS,          # Optional: unit constant
    mode="box",                       # Optional: "box" for text input, "slider" for slider
    multiplier=1,                     # Optional: scale between HA value and raw attribute (default 1)
    device_class=NumberDeviceClass.DURATION,  # Optional: HA device class
    translation_key="turn_on_delay",
    fallback_name="Turn on delay",
)
```

**Number `multiplier` semantics:** Defined on the entity by ZHA. HA Core is a pure pass-through — it does no scaling itself. The conversion is:
- Display: `native_value = raw_attr_value * multiplier`
- Write: `raw_attr_value = round(ha_value / multiplier)`

If the underlying attribute is an integer representing a fractional unit (e.g., the ZCL `local_temperature_calibration` attribute is `int8s` storing tenths of a degree), pair fractional `step` with the matching `multiplier` so HA values are scaled correctly. The attribute's raw type comes from the cluster's `AttributeDefs` — for `.number()` (unlike `.tuya_number()`) you don't pass a `type`. Without a `multiplier` (default `1`), fractional input is rounded to a whole raw value on write and raw values are displayed unscaled.

```python
# ZCL Thermostat local_temperature_calibration: int8s, tenths of a degree.
# HA range -2.5..2.5 °C ↔ raw attribute value -25..25
.number(
    attribute_name=Thermostat.AttributeDefs.local_temperature_calibration.name,
    cluster_id=Thermostat.cluster_id,
    min_value=-2.5,
    max_value=2.5,
    step=0.1,
    multiplier=0.1,   # required: pairs with step=0.1
    unit=UnitOfTemperature.CELSIUS,
    device_class=NumberDeviceClass.TEMPERATURE_DELTA,
    translation_key="local_temperature_calibration",
    fallback_name="Local temperature calibration",
)
```

`min_value`/`max_value` are HA-side values (after the multiplier), not raw attribute values. Confirm the device's raw value range and pick HA-side limits accordingly.

```python

# Enum as SELECT (dropdown, default) - user can change value
.enum(
    attribute_name=VendorCluster.AttributeDefs.mode.name,
    enum_class=ModeEnum,
    cluster_id=VendorCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    translation_key="mode",
    fallback_name="Mode",
)

# Enum as SENSOR (read-only display)
.enum(
    attribute_name=VendorCluster.AttributeDefs.operating_mode.name,
    enum_class=OperatingModeEnum,
    cluster_id=VendorCluster.cluster_id,
    entity_platform=EntityPlatform.SENSOR,  # Optional: makes it read-only (default SELECT)
    entity_type=EntityType.DIAGNOSTIC,      # Required with SENSOR: an enum sensor can't be CONFIG
    translation_key="operating_mode",
    fallback_name="Operating mode",
)

# Button (write attribute on press)
.write_attr_button(
    attribute_name=VendorCluster.AttributeDefs.reset.name,
    attribute_value=1,
    cluster_id=VendorCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    translation_key="reset",
    fallback_name="Reset",
)

# Button (execute ZCL command on press)
.command_button(
    command_name=Basic.ServerCommandDefs.reset_fact_default.name,
    cluster_id=Basic.cluster_id,
    command_args=(),                  # Optional: positional args for command
    command_kwargs={},                # Optional: keyword args for command
    cluster_type=ClusterType.Server,  # Optional: default Server
    translation_key="factory_reset",
    fallback_name="Factory reset",
)
```

**Entity unique_id format:**

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

**Device Automation Triggers:**
```python
# Maps device events to HA automation triggers
# Format: {(action, subtype): {COMMAND: command_name, ...}}
.device_automation_triggers({
    (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
    (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
    (LONG_PRESS, DIM_UP): {COMMAND: COMMAND_STEP, CLUSTER_ID: 8, ENDPOINT_ID: 1},
})
```
The trigger tuple `(action, subtype)` appears in the HA UI. The dict value must uniquely match the `zha_event` fired by the device.

When a custom cluster fires the event itself, use a `COMMAND_*` constant as the command (`COMMAND_SINGLE`, `COMMAND_DOUBLE`, `COMMAND_HOLD`, …) and keep press-type constants (`SHORT_PRESS`, …) for the trigger tuple:
```python
self.listener_event(ZHA_SEND_EVENT, COMMAND_SINGLE, {})
# ...
.device_automation_triggers({(SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 1}})
```

**Other Methods:**
- `.friendly_name(model="...", manufacturer="...")` - Override device name displayed in HA
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

```python
# Example: Show user-friendly name instead of model code
.friendly_name(
    model="Hue OmniGlow lightstrip",
    manufacturer="Philips",
)
```

**Preventing Default Entity Creation:**
Hide entities that ZHA would create by default. Without `cluster_type`, `cluster_id` matches server and client clusters.
```python
# Hide all entities from a cluster
.prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)

# Hide entities matching a condition
.prevent_default_entity_creation(
    endpoint_id=1,
    cluster_id=OnOff.cluster_id,
    function=lambda entity: entity.device_class == "opening",
)
```

**Changing Default Entity Metadata:**
Modify properties of entities ZHA creates by default:
```python
# Make an entity the primary entity for the device
.change_entity_metadata(
    endpoint_id=35,
    cluster_id=IasZone.cluster_id,
    new_primary=True,
)

# Change entity category and primary status
.change_entity_metadata(
    endpoint_id=35,
    cluster_id=IasWd.cluster_id,
    new_primary=False,
    new_entity_category=EntityType.DIAGNOSTIC,
)
```
Available `new_*` parameters: `new_primary`, `new_unique_id`, `new_translation_key`, `new_translation_placeholders`, `new_device_class`, `new_state_class`, `new_entity_category`, `new_entity_registry_enabled_default`, `new_fallback_name`. Here `cluster_type` defaults to `ClusterType.Server` when `cluster_id` is set.

**Custom Entity Classes:**
Use the builder entity methods when an entity maps to one attribute. When it needs logic they can't express, subclass an appropriate entity type:

- New entity: `.adds_entity(cls, endpoint_id=..., cluster_id=..., **kwargs)`. `kwargs` go to `cls.__init__`. Device-bound entities (`PlatformEntity`, not `ZclPlatformEntity`) take no endpoint or cluster. The entity is only created if `cls.is_supported()` passes; `force_create=True` skips the check. Pass `unique_id_suffix` unless `cls` sets one: without a suffix, a ZCL entity gets `{ieee}-{endpoint_id}`, which default lights, switches and covers also use.
- Changing a default ZHA entity: `.replaces_entity(zha_cls, cls, endpoint_id=..., cluster_id=...)`, or `filter=EntityFilter(...)` instead of the endpoint and cluster. It must match exactly one entity of exactly `zha_cls`. `cls` must be the same kind (ZCL or device-bound) and keep the unique ID.

Example: a switch per relay bit of a mask attribute:
```python
from zha.application.helpers import write_attributes_safe

class DetachRelaySwitch(ConfigurableAttributeSwitch):
    _attribute_name = SonoffCluster.AttributeDefs.detach_relay_mask.name
    _server_cluster_config = {
        SonoffCluster.cluster_id: ClusterConfig(
            attributes={
                SonoffCluster.AttributeDefs.detach_relay_mask: AttrConfig(
                    read_on_startup=True
                ),
            },
        ),
    }

    def __init__(self, *args, relay: SonoffDetachedRelayMask, **kwargs) -> None:
        self._relay = relay
        super().__init__(*args, **kwargs)

    @property
    def is_on(self) -> bool:
        return bool(self._cluster.get(self._attribute_name) & self._relay)

    async def async_turn_on_off(self, state: bool) -> None:
        mask = self._cluster.get(self._attribute_name)
        mask = (mask | self._relay) if state else (mask & ~self._relay)
        await write_attributes_safe(self._cluster, {self._attribute_name: mask})
        self.maybe_emit_state_changed_event()


(
    QuirkBuilder("SONOFF", "ZBM5-1C-80/86")
    .replaces(SonoffCluster)
    .adds_entity(
        DetachRelaySwitch,
        endpoint_id=1,
        cluster_id=SonoffCluster.cluster_id,
        relay=SonoffDetachedRelayMask.Relay1,
        unique_id_suffix="relay_1_detached",
        translation_key="detach_relay_id",
        translation_placeholders={"id": "1"},
        fallback_name="Detach relay 1",
    )
    .add_to_registry()
)
```

Removing entities: `.removes_entity(EntityFilter(...))` with any of `entity_cls` (exact type), `platform`, `endpoint_id`, `cluster_id`, `cluster_type`, `unique_id_suffix`, `translation_key`, `device_class`, `function`.

### Tuya Devices (TuyaQuirkBuilder)

Tuya devices use datapoints (DPs) instead of ZCL attributes. Use `TuyaQuirkBuilder`:

```python
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_xxx", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .tuya_switch(dp_id=5, attribute_name="valve", translation_key="valve", fallback_name="Valve")
    .skip_configuration()
    .add_to_registry()
)
```

See `tuya.md` for detailed Tuya quirk documentation including finding DPs and all available methods.

### V1 Quirks (Legacy)

V1 quirks inherit from `CustomDevice` with explicit `signature` and `replacement` dicts. The signature must match the device exactly; the replacement defines what ZHA should use instead:

```python
from zhaquirks.legacy import CustomDevice
from zhaquirks.const import MODELS_INFO, ENDPOINTS, INPUT_CLUSTERS, ...

class MyDevice(CustomDevice):
    signature = {
        MODELS_INFO: [("Manufacturer", "Model")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [Basic.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id, CustomOnOffCluster],
            }
        },
    }
```

### Custom Clusters

**Extending a ZCL cluster** - Add manufacturer-specific attributes to a standard cluster:

```python
from zhaquirks.clusters import CustomCluster
from zigpy.zcl.clusters.general import OnOff

class CustomOnOffCluster(CustomCluster, OnOff):
    """Custom OnOff with manufacturer-specific attributes."""

    class AttributeDefs(OnOff.AttributeDefs):
        custom_attr: Final = ZCLAttributeDef(
            id=0x8000, type=t.Bool, manufacturer_code=0x117C
        )
```

**Fully custom cluster** - For manufacturer-specific clusters not based on ZCL:

```python
from zhaquirks.clusters import CustomCluster
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

class VOCIndex(CustomCluster):
    """Custom cluster with no ZCL base."""

    cluster_id: t.uint16_t = 0xFC7E       # Manufacturer-specific cluster ID
    name: str = "IKEA VOC Index"
    ep_attribute: str = "voc_index"        # Attribute name on endpoint

    class AttributeDefs(BaseAttributeDefs):  # Note: BaseAttributeDefs, not a ZCL cluster
        measured_value: Final = ZCLAttributeDef(
            id=0x0000, type=t.Single, access="rp", manufacturer_code=0x117C
        )
```

**`manufacturer_code`**: Specifies the manufacturer code to send with read/write requests for this attribute. Needed for vendor-specific attributes on standard ZCL clusters; on a manufacturer-specific cluster (`0xFC00` and up) zigpy uses the device's manufacturer ID when it isn't set. Without it, the device may not recognize or respond to the attribute request. Use the hex code for the manufacturer (e.g., `0x117C` for IKEA, `0x115F` for Xiaomi). Set `manufacturer_code=None` to explicitly suppress sending a manufacturer code, even on manufacturer-specific clusters. This replaces the older `is_manufacturer_specific=True` approach which obtained the code from the device's NodeDescriptor.

**`access`**: Controls attribute read/write/report capabilities. Not needed to explicitly specify - defaults to `"rwp"`. Values:
- `"r"` - Read-only
- `"w"` - Write-only
- `"rw"` - Read and write
- `"rp"` - Read and reportable (device sends reports on change)
- `"rwp"` - Read, write, and reportable

**Custom enum types** for attribute values - Define `t.enum8` or `t.enum16` subclasses:
```python
class BoschOperatingMode(t.enum8):
    """Operating mode values."""
    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05

# Use in attribute definition:
operating_mode = ZCLAttributeDef(
    id=0x4007, type=BoschOperatingMode, manufacturer_code=0x1209
)
```

**`_CONSTANT_ATTRIBUTES`**: Force specific attribute values, overriding what the device reports. Useful when devices report incorrect values (e.g., wrong multiplier/divisor for energy metering):

```python
class MeteringClusterFixed(CustomCluster, Metering):
    """Fix incorrect multiplier and divisor values."""

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }
```

Key base classes in `zhaquirks/__init__.py`:
- `LocalDataCluster`: Prevents remote calls, responds locally
- `EventableCluster`: Converts cluster requests to events

## Entity Creation Rules

When adding entities with v2 quirks:

1. **`fallback_name`** is always required - English entity name in sentence case (e.g., "Soil moisture" not "Soil Moisture"). Abbreviations like "LED" stay uppercase.

2. **`translation_key`** is optional but required when no device class is set. Typically the attribute name or slugified entity name. A `translation_key` must map to the same `fallback_name` everywhere in the repo unless the entity uses `translation_placeholders` (`test_translation_key_and_fallback_name_match` enforces it), so reuse an existing key and its exact name when the entity means the same thing.

3. Entity name priority in Home Assistant: translation_key → device_class name → fallback_name

4. Don't pass arguments that equal their default. Default `entity_type`: `.sensor()` STANDARD, `.binary_sensor()` DIAGNOSTIC, everything else CONFIG. An entity the user can change is never DIAGNOSTIC.

5. `.enum()` creates a writable select by default. For a read-only attribute pass `entity_platform=EntityPlatform.SENSOR` together with `entity_type=EntityType.DIAGNOSTIC` (or `STANDARD`): an enum sensor can't use the default CONFIG (`test_enum_sensor_category`).

## Testing

Test fixtures are in `tests/conftest.py`:

```python
# For v1 quirks
quirked = zigpy_device_from_quirk(quirk_class)

# For v2 quirks
quirked = zigpy_device_from_v2_quirk(manufacturer, model)
```

Don't add new signature match tests (`assert_signature_matches_quirk`); they only exist for old v1 quirks.

**When tests are NOT needed:** Purely declarative v2 quirks that contain no custom logic do not require test coverage. This includes quirks that only use existing custom clusters (already tested elsewhere), `.device_automation_triggers()`, `.friendly_name()`, `.applies_to()`, `.skip_configuration()`, `_CONSTANT_ATTRIBUTES`, or other pure definitions. Adding `.applies_to()` to an existing quirk doesn't need a test either. Once a device's diagnostics are in ZHA's test data, ZHA's snapshot tests cover the entities its quirk creates, so don't write tests that only assert what the builder produced. Example:

```python
(
    QuirkBuilder("Manufacturer", "Model")
    .friendly_name(model="Wireless Mini Switch", manufacturer="Acme")
    .replaces(ExistingCustomCluster)
    .device_automation_triggers({
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_SINGLE},
        (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_DOUBLE},
    })
    .add_to_registry()
)
```

Tests **are** needed when a quirk introduces custom logic such as custom clusters with overridden methods (e.g., `handle_cluster_request`, `_update_attribute`, `write_attributes`), value parsing or command handling, non-trivial filter functions, or custom entity classes. A one-line `attribute_converter` lambda doesn't need its own test.

**End-to-end tests:** if your quirk is complex, its high-level behavior should be tested. Use `tests/zha_helpers.py` with diagnostics for your device:
```python
async with zha_gateway() as gateway:
    device = await join_device_from_diagnostics(gateway, "your_device.json", DEVICE_REGISTRY)
```

## Code Organization

Quirks are organized by manufacturer in `zhaquirks/<manufacturer>/`:
- `__init__.py`: Required, or the directory's quirks are never imported. Holds clusters, constants and base classes *shared* by several device files
- `<device>.py`: Device-specific quirks, including clusters only that device uses

Tuya devices go in `zhaquirks/tuya/` whatever the brand on the box.

## Key Imports

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

## Code Style

**Avoid magic numbers** for cluster IDs, attribute IDs, and command IDs that already have a definition. Reference the definition instead (a new attribute's ID belongs inline in its `ZCLAttributeDef`, not in a module constant):

```python
# Good - use cluster and attribute/command references
Metering.cluster_id                            # Cluster ID (int)
Metering.AttributeDefs.multiplier.id           # Attribute ID (int)
Metering.AttributeDefs.multiplier.name         # Attribute name (str)
WindowCovering.ServerCommandDefs.go_to_lift_percentage.id  # Server command ID
IasZone.ClientCommandDefs.status_change_notification.id    # Client command ID

# Bad - magic numbers
0x0702  # What cluster is this?
0x0301  # What attribute is this?
0x00    # What command is this?
```

**Accessing clusters on an endpoint** - Use the cluster's `ep_attribute` (e.g., `IasZone.ep_attribute` is `"ias_zone"`):
```python
# Access cluster on current endpoint
self.endpoint.ias_zone.update_attribute(
    IasZone.AttributeDefs.zone_status.id,
    IasZone.ZoneStatus.Alarm_1,
)

# Access cluster on a different endpoint
self.endpoint.device.endpoints[1].electrical_measurement.update_attribute(
    ElectricalMeasurement.AttributeDefs.active_power.id,
    value,
)
```

**Handling commands in cluster request handlers** - Compare by ID using command definitions:
```python
def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
    if hdr.command_id in (
        LevelControl.ServerCommandDefs.move.id,
        LevelControl.ServerCommandDefs.move_with_on_off.id,
    ):
        # Handle move command
        pass
```

## PR Requirements

- Run `pre-commit run --all-files` before submitting
- New quirks require device diagnostics data (download from HA device page → three dots → "Download diagnostics")
- Add tests for custom logic only (see Testing)
