# Supporting Tuya Devices

Caution, the following should work for most Tuya devices, some devices may require additional reverse engineering to unlock all functions.

# Identify Tuya Data Points

The first step in building a Tuya quirk is to identify the Tuya Datapoints (DPs) for the device. There are two ways ways to do this.

1. If the device is supported by Zigbee2MQTT, the DPs can be captured from the [herdsman converter](https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/tuya.ts).
2. Using a Tuya hub, the DPs can be captured from the Tuya developer's console. See [Zigbee2MQTT Documentation](https://www.zigbee2mqtt.io/advanced/support-new-devices/03_find_tuya_data_points.html)

# Using the datapoints to develop a Tuya Quirk

Once the DPs are identified, the quirk can be built. See below for all available methods.

## Example Tuya Quirk

```python
from zhaquirks.tuya.builder import TuyaPowerConfigurationCluster2AAA, TuyaQuirkBuilder

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

TuyaQuirkBuilder is a subclass of QuirkBuilder, retaining all of the V2 QuirkBuilder methods and adding Tuya specific methods.
For all available options on each method see [TuyaQuirkBuilder](https://github.com/zigpy/zha-device-handlers/blob/dev/zhaquirks/tuya/builder/__init__.py).

### Convenience Methods

  These methods allow exposing the most common Tuya clusters.

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

These methods expose an entity to Home Assistant.

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

Adds a enum entity.

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

Adds a sensor entity.

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

#### tuya_dp_attribute

Add a DP converter and corresponding Attribute definition.

```python
    .tuya_dp_attribute(
        dp_id=1,
        attribute_name="irrigation_mode",
        type=t.Bool,
    )
```
