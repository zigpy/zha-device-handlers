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

Use `QuirkBuilder` from `zigpy.quirks.v2` for declarative quirk definition:

```python
from zigpy.quirks.v2 import QuirkBuilder

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
- `.applies_to(manufacturer, model)` - Add manufacturer/model pair to match
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
- `.adds(cluster, endpoint_id=1, cluster_type=ClusterType.Server, constant_attributes={})` - Add a cluster. `constant_attributes` dict forces specific attribute values (same as `_CONSTANT_ATTRIBUTES` on a custom cluster)
- `.removes(cluster_id, endpoint_id=1, cluster_type=ClusterType.Server)` - Remove a cluster
- `.replaces(replacement_cluster_class, endpoint_id=1, cluster_type=ClusterType.Server)` - Replace cluster with custom implementation
- `.replace_cluster_occurrences(cluster_class, replace_server=True, replace_client=True)` - Replace across all endpoints

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
- `unique_id_suffix`: Suffix to differentiate entities when multiple use the same attribute (required when creating multiple entities from one attribute)

**Parameter order convention:** `attribute_name`, `cluster_id`, `endpoint_id` first; `translation_key` and `fallback_name` always last (in that order). Use keyword arguments for clarity.

`reporting_config` sets up automatic attribute reporting from the device:
```python
from zigpy.quirks.v2 import ReportingConfig

.sensor(
    attribute_name="measured_value",
    cluster_id=VOCIndex.cluster_id,
    reporting_config=ReportingConfig(
        min_interval=60,      # Minimum seconds between reports
        max_interval=120,     # Maximum seconds between reports
        reportable_change=1,  # Minimum change to trigger report
    ),
    ...
)
```

**Entity Methods:**
```python
# Switch (on/off control)
.switch(
    attribute_name="led_enable",
    cluster_id=CustomCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server; use ClusterType.Client for out_clusters
    force_inverted=False,             # Optional: invert on/off
    off_value=0,                      # Optional: value written when turning off (default 0)
    on_value=1,                       # Optional: value written when turning on (default 1)
    translation_key="led_enable",
    fallback_name="LED enable",
)

# Sensor (read-only value)
.sensor(
    attribute_name="temperature",
    cluster_id=TemperatureMeasurement.cluster_id,
    cluster_type=ClusterType.Server,          # Optional: default Server
    divisor=100,                              # Optional: divide raw value (default 1)
    multiplier=1,                             # Optional: multiply raw value (default 1)
    suggested_display_precision=1,            # Optional: decimal places in HA UI
    device_class=SensorDeviceClass.TEMPERATURE,  # Optional: HA device class
    state_class=SensorStateClass.MEASUREMENT,    # Optional: HA state class
    unit=UnitOfTemperature.CELSIUS,           # Optional: use unit constants, not strings
    translation_key="temperature",
    fallback_name="Temperature",
)

# Binary Sensor (on/off state)
.binary_sensor(
    attribute_name="occupancy",
    cluster_id=OccupancySensing.cluster_id,
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
    attribute_name="off_to_on_delay",
    cluster_id=CustomCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    min_value=0,                      # Optional: minimum allowed value
    max_value=65535,                  # Optional: maximum allowed value
    step=1,                           # Optional: step increment
    unit=UnitOfTime.SECONDS,          # Optional: unit constant
    mode="box",                       # Optional: "box" for text input, "slider" for slider
    multiplier=1,                     # Optional: multiply value before writing to device
    device_class=NumberDeviceClass.DURATION,  # Optional: HA device class
    translation_key="turn_on_delay",
    fallback_name="Turn on delay",
)

# Enum as SELECT (dropdown, default) - user can change value
.enum(
    attribute_name="mode",
    enum_class=ModeEnum,
    cluster_id=CustomCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    translation_key="mode",
    fallback_name="Mode",
)

# Enum as SENSOR (read-only display)
.enum(
    attribute_name="operating_mode",
    enum_class=OperatingModeEnum,
    cluster_id=CustomCluster.cluster_id,
    entity_platform=EntityPlatform.SENSOR,  # Optional: makes it read-only (default SELECT)
    entity_type=EntityType.DIAGNOSTIC,      # Optional: default CONFIG
    translation_key="operating_mode",
    fallback_name="Operating mode",
)

# Button (write attribute on press)
.write_attr_button(
    attribute_name="reset",
    attribute_value=1,
    cluster_id=CustomCluster.cluster_id,
    cluster_type=ClusterType.Server,  # Optional: default Server
    translation_key="reset",
    fallback_name="Reset",
)

# Button (execute ZCL command on press)
.command_button(
    command_name="reset_to_factory_defaults",
    cluster_id=Basic.cluster_id,
    command_args=(),                  # Optional: positional args for command
    command_kwargs={},                # Optional: keyword args for command
    cluster_type=ClusterType.Server,  # Optional: default Server
    translation_key="factory_reset",
    fallback_name="Factory reset",
)
```

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

**Other Methods:**
- `.friendly_name(model="...", manufacturer="...")` - Override device name displayed in HA
- `.device_class(custom_device_class)` - Use a custom device class (e.g., `CustomDeviceV2` subclass for special request handling)
- `.skip_configuration()` - Skip attribute reporting configuration
- `.add_to_registry()` - **Required** - Registers the quirk

```python
# Example: Show user-friendly name instead of model code
.friendly_name(
    model="Hue OmniGlow lightstrip",
    manufacturer="Philips",
)
```

**Preventing Default Entity Creation:**
Hide entities that ZHA would create by default:
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
Available `new_*` parameters: `new_primary`, `new_unique_id`, `new_translation_key`, `new_device_class`, `new_state_class`, `new_entity_category`, `new_fallback_name`.

### Tuya Devices (TuyaQuirkBuilder)

Tuya devices use datapoints (DPs) instead of ZCL attributes. Use `TuyaQuirkBuilder`:

```python
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_xxx", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .tuya_switch(dp_id=5, attribute_name="valve", fallback_name="Valve")
    .skip_configuration()
    .add_to_registry()
)
```

See `tuya.md` for detailed Tuya quirk documentation including finding DPs and all available methods.

### V1 Quirks (Legacy)

V1 quirks inherit from `CustomDevice` with explicit `signature` and `replacement` dicts. The signature must match the device exactly; the replacement defines what ZHA should use instead:

```python
from zigpy.quirks import CustomDevice
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
from zigpy.quirks import CustomCluster
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
from zigpy.quirks import CustomCluster
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

**`manufacturer_code`**: Specifies the manufacturer code to send with read/write requests for this attribute. Required for vendor-specific attributes that aren't part of the ZCL standard. Without it, the device may not recognize or respond to the attribute request. Use the hex code for the manufacturer (e.g., `0x117C` for IKEA, `0x115F` for Xiaomi). Set `manufacturer_code=None` to explicitly suppress sending a manufacturer code, even on manufacturer-specific clusters. This replaces the older `is_manufacturer_specific=True` approach which obtained the code from the device's NodeDescriptor.

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

2. **`translation_key`** is optional but required when no device class is set. Typically the attribute name or slugified entity name.

3. Entity name priority in Home Assistant: translation_key → device_class name → fallback_name

## Testing

Test fixtures are in `tests/conftest.py`:

```python
# For v1 quirks
quirked = zigpy_device_from_quirk(quirk_class)

# For v2 quirks
quirked = zigpy_device_from_v2_quirk(model, manufacturer)

# Verify signature matches quirk (useful for v1 quirks)
def test_my_device_signature(assert_signature_matches_quirk):
    signature = {...}  # From HA device page "Zigbee Device Signature"
    assert_signature_matches_quirk(MyDeviceQuirk, signature)
```

**When tests are NOT needed:** Purely declarative v2 quirks that contain no custom logic do not require test coverage. This includes quirks that only use existing custom clusters (already tested elsewhere), `.device_automation_triggers()`, `.friendly_name()`, `.applies_to()`, `.skip_configuration()`, or other pure definitions. Example:

```python
(
    QuirkBuilder("Manufacturer", "Model")
    .friendly_name(model="Wireless Mini Switch", manufacturer="Acme")
    .replaces(ExistingCustomCluster)
    .device_automation_triggers({
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_1_SINGLE},
        (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_1_DOUBLE},
    })
    .add_to_registry()
)
```

Tests **are** needed when a quirk introduces custom logic such as custom clusters with overridden methods (e.g., `handle_cluster_request`, `update_attribute`), `attribute_converter` lambdas, or custom filter functions.

## Code Organization

Quirks are organized by manufacturer in `zhaquirks/<manufacturer>/`:
- `__init__.py`: Shared clusters, constants, base classes for the manufacturer
- `<device>.py`: Device-specific quirks

## Key Imports

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
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import (  # Unit constants
    UnitOfTemperature, UnitOfTime, UnitOfEnergy, UnitOfPower,
)
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder

# Cluster types
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, OnOff, Groups, Scenes
from zigpy.zcl.clusters.measurement import TemperatureMeasurement, RelativeHumidity
import zigpy.types as t
```

## Code Style

**Avoid magic numbers** for cluster IDs, attribute IDs, and command IDs. Use the cluster's definition instead:

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
- Tests should verify entity creation
