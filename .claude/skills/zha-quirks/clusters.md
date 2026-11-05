# Custom clusters

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

## Working with clusters in code

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

