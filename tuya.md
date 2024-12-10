# Supporting Tuya Devices

> [!IMPORTANT]
> The following should work for most Tuya devices. Some devices may require additional reverse engineering to unlock all functions.

# Identify Tuya Data Points

The first step in building a Tuya quirk is to identify the Tuya Datapoints (DPs) for the device. There are two ways ways to do this.

1. If the device is supported by Zigbee2MQTT, the DPs can be captured from the [herdsman converter](https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/tuya.ts).
2. Using a Tuya hub, the DPs can be captured from the Tuya developer's console. See [Zigbee2MQTT Documentation](https://www.zigbee2mqtt.io/advanced/support-new-devices/03_find_tuya_data_points.html)

# Using the datapoints to develop a Tuya Quirk

Once the DPs are identified, the quirk can be built. For each DP, identify the correct replacement for the quirk using the available methods below. For commonly used replacements, such as a power configuration cluster, we can use a convenience method, such as `.tuya_battery`. 

> [!NOTE]  
> Convenience methods will only work once, as these methods internally map Tuya datapoints to standard-compliant ZCL attributes.
> If your device has multiple identical clusters, such as `OnOff`, use multiple `.tuya_switch` calls instead to expose custom entities in Home Assistant. Otherwise, only one switch will be exposed.

For more complex replacements you may need to use a lower level method, such as `.tuya_dp_attribute` or even `.tuya_dp` and `.tuya_attribute`.

All v2 QuirkBuilder methods are available, so using `.tuya_dp` to add a DP converter, then `.adds` to add the correct class is valid.

Most v2 quirks will match only on the model and manufacturer. This reduces duplicated code where a new variant appears with a slightly different signature. Should you need to filter on a signature as well, use `.filter`.

```python
from zigpy.quirks import signature_matches

.filter(signature_matches(device_signature))
```

Once the quirk is complete, enable custom quirks and test. See [Configuration - YAML in ZHA documentation](https://www.home-assistant.io/integrations/zha/).

## Example Tuya Quirk

```python
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_bjawzodf", "TS0601")
    .applies_to("_TZE200_zl1kmjqx", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2, scale=10)
    .tuya_battery(dp_id=4)
    .skip_configuration()
    .add_to_registry()
)
```

## TuyaQuirkBuilder

TuyaQuirkBuilder is a subclass of QuirkBuilder, retaining all of the v2 QuirkBuilder methods and adding Tuya specific methods.

### Convenience Methods

These methods allow exposing the most common Tuya clusters. These methods were added as part of the quirk building process and it is likely that there are other convenience methods that should be created. If you find that you are repeating the `.tuya_dp` and `.adds` formula, please PR or suggest additional methods.

#### tuya_battery(dp_id: int, power_cfg: PowerConfiguration = TuyaPowerConfigurationCluster2AAA, scale: float = 2)

Adds a battery power cluster.

```python
.tuya_battery(dp_id=2, power_config=TuyaPowerConfigurationCluster4AAA)
```

#### tuya_metering(dp_id: int, metering_cfg: TuyaLocalCluster = TuyaValveWaterConsumed)

Adds a metering cluster.

```python
.tuya_metering(dp_id=3)
```

#### tuya_onoff(dp_id: int, onoff_cfg: TuyaLocalCluster = TuyaOnOffNM)

Adds an on/off cluster.

```python
.tuya_onoff(dp_id=4)
```

#### tuya_humidity(dp_id: int, rh_cfg: TuyaLocalCluster = TuyaRelativeHumidity, scale: float = 100)

Adds a humidity cluster.

```python
.tuya_humidity(dp_id=5)
```

#### tuya_soil_moisture(dp_id: int, soil_cfg: TuyaLocalCluster = TuyaSoilMoisture, scale: float = 100)

Adds a soil moisture cluster.

```python
.tuya_soil_moisture(dp_id=6, scale=10)
```

#### tuya_temperature(dp_id: int, temp_cfg: TuyaLocalCluster = TuyaTemperatureMeasurement, scale: float = 10)

Adds a temperature cluster.

```python
.tuya_temperature(dp_id=7)
```

### Entity Methods

These methods expose an entity to Home Assistant. The following examples do not cover all available arguments, nor are they listed here to help keep this documentation accurate. For available arguments on each method see [TuyaQuirkBuilder](https://github.com/zigpy/zha-device-handlers/blob/dev/zhaquirks/tuya/builder/__init__.py).

#### tuya_switch

Adds a switch entity.

```python
.tuya_switch(
    dp_id=1,
    attribute_name="valve_on_off_1",
    entity_type=EntityType.STANDARD,
    translation_key="valve_on_off_1",
    fallback_name="Valve 1",
)
```

#### tuya_enum

Adds an enum entity.

Note: In the Tuya developer console, these will appear to be string enums. I have yet to run into a string enum, so assume that they are `t.enum8`.

```python
class GiexBatteryStatus(t.enum8):
"""Giex Soil Battery Status Enum."""

    Low = 0x00
    Middle = 0x01
    High = 0x02

.tuya_enum(
    dp_id=14,
    attribute_name="battery_status",
    enum_class=GiexBatteryStatus,
    translation_key="battery_status",
    fallback_name="Battery Status",
    entity_type=EntityType.DIAGNOSTIC,
    entity_platform=EntityPlatform.SENSOR,
    initially_disabled=True,
)
```

#### tuya_number

Adds a number entity.

```python
.tuya_number(
    dp_id=13,
    attribute_name="valve_countdown_1",
    type=t.uint16_t,
    device_class=SensorDeviceClass.DURATION,
    unit=UnitOfTime.MINUTES,
    min_value=0,
    max_value=1440,
    step=1,
    translation_key="valve_countdown_1",
    fallback_name="Irrigation time 1",
)
```

#### tuya_binary_sensor

Adds a binary sensor entity.

```python
.tuya_binary_sensor(
    dp_id=8,
    attribute_name="system_online",
    translation_key="system_online",
    fallback_name="System online",
)
```

#### tuya_sensor

Adds a sensor entity. Sensors can't return string values, you also need to ensure the return type matches the [device_class](https://developers.home-assistant.io/docs/core/entity/sensor/#available-device-classes).

```python
.tuya_sensor(
    dp_id=25,
    attribute_name="valve_duration_1",
    type=t.uint32_t,
    state_class=SensorStateClass.MEASUREMENT,
    device_class=SensorDeviceClass.DURATION,
    unit=UnitOfTime.SECONDS,
    entity_type=EntityType.STANDARD,
    translation_key="irrigation_duration_1",
    fallback_name="Irrigation duration 1",
)
```

Some Tuya DPs will return an incompatible type, this example returns a string value that must be converted via a function.

```python
def giex_string_to_td(v: str) -> int:
    """Convert Giex String Duration to seconds."""
    dt = datetime.strptime(v, "%H:%M:%S,%f")
    return timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second).seconds

.tuya_sensor(
    dp_id=114,
    attribute_name="irrigation_duration",
    type=t.uint32_t,
    converter=lambda x: giex_string_to_td(x),
    state_class=SensorStateClass.MEASUREMENT,
    device_class=SensorDeviceClass.DURATION,
    unit=UnitOfTime.SECONDS,
    translation_key="irrigation_duration",
    fallback_name="Last irrigation duration",
)
```

### Base Methods

#### tuya_dp

Adds a DP converter.

```python
.tuya_dp(
    dp_id=4,
    ep_attribute=TuyaPowerConfigurationCluster2AAA.ep_attribute,
    attribute_name="battery_percentage_remaining",
    converter=lambda x: {0: 50, 1: 100, 2: 200}[x],
)
```

#### tuya_attribute

Add an Attribute definition

```python
.tuya_attribute(
    dp_id=4,
    attribute_name="irrigation_mode",
    type=t.Bool,
)
```

#### tuya_dp_attribute

Add a DP converter and corresponding Attribute definition.

```python
.tuya_dp_attribute(
    dp_id=1,
    attribute_name="irrigation_mode",
    type=t.Bool,
)
```

### Building tests for v2 Quirks

To get a device from a v2 Quirk, use `zigpy_device_from_v2_quirk`.

```python
async def test_tuya():
    """Example Tuya Test."""

    quirked = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked.endpoints[1]

    temperature_listener = ClusterListener(ep.temperature)

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    message = b"\x09\xe0\x02\x0b\x33\x01\x02\x00\x04\x00\x00\x00\xfd\x02\x02\x00\x04\x00\x00\x00\x47\x04\x02\x00\x04\x00\x00\x00\x64"
    hdr, data = ep.tuya_manufacturer.deserialize(message)

    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(temperature_listener.attribute_updates) == 1
    assert (
        temperature_listener.attribute_updates[0][1]
        == data.data.datapoints[0].data.payload * temp_scale
    )
```
