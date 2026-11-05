# Entities

Entity methods create Home Assistant entities from cluster attributes or commands. Naming rules (`fallback_name`, `translation_key`) are in `AGENTS.md`; Home Assistant picks the entity name from `translation_key`, then the `device_class` name, then `fallback_name`.

Common parameters:
- `attribute_name`: ZCL attribute to expose
- `cluster_id`: Cluster containing the attribute
- `endpoint_id`: Endpoint (default 1)
- `translation_key`: For HA translations (required if no device_class)
- `fallback_name`: English name in sentence case (always required)
- `entity_type`: `EntityType.STANDARD`, `CONFIG`, or `DIAGNOSTIC`
- `initially_disabled`: Start disabled in HA
- `device_class`: HA device class for the entity
- `reporting_config`: Configure ZCL attribute reporting
- `unique_id_suffix`: Suffix appended to the entity's unique_id. Defaults to `attribute_name` (or `command_name` for command-based entities). Required when creating multiple entities from the same attribute/command on the same endpoint, since otherwise the default suffixes collide. See [unique-ids.md](unique-ids.md) before changing this on existing quirks.

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

