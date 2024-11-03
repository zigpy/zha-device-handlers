# Supporting Tuya Devices

Caution, the following should work for most Tuya devices, some devices may require additional reverse engineering to unlock all functions.

# Identify Tuya Data Points

The first step in building a Tuya quirk is to identify the Tuya Datapoints (DPs) for the device. There are two ways ways to do this.

1. If the device is supported by Zigbee2MQTT, the DPs can be captured from the [herdsman converter](https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/tuya.ts).
2. Using a Tuya hub, the DPs can be captured from the Tuya developer's console. See [Zigbee2MQTT Documentation](https://www.zigbee2mqtt.io/advanced/support-new-devices/03_find_tuya_data_points.html)

# Using the datapoints to develop a Tuya Quirk

## TuyaQuirkBuilder is a subclass of QuirkBuilder, retaining all of the V2 QuirkBuilder methods and adding Tuya specific methods

### Convenience Methods
  These methods allow exposing the most common Tuya clusters.

#### tuya_battery(dp_id: int, power_cfg: PowerConfiguration = TuyaPowerConfigurationCluster2AAA, scale: float = 2)
- Adds a battery power cluster.
- `.tuya_battery(dp_id=2, power_config=TuyaPowerConfigurationCluster4AAA)`

#### tuya_metering(dp_id: int, metering_cfg: TuyaLocalCluster = TuyaValveWaterConsumed)
- Adds a metering cluster.
- `.tuya_metering(dp_id=3)`

#### tuya_onoff(dp_id: int, onoff_cfg: TuyaLocalCluster = TuyaOnOffNM)
- Adds an on/off cluster.
- `.tuya_onoff(dp_id=4)`

#### tuya_humidity(dp_id: int, rh_cfg: TuyaLocalCluster = TuyaRelativeHumidity, scale: float = 100)
- Adds a humidity cluster.
- `.tuya_humidity(dp_id=5)`

#### tuya_soil_moisture(dp_id: int, soil_cfg: TuyaLocalCluster = TuyaSoilMoisture, scale: float = 100)
- Adds a soil moisture cluster.
- `.tuya_soil_moisture(dp_id=6, scale=10)`

#### tuya_temperature(dp_id: int, temp_cfg: TuyaLocalCluster = TuyaTemperatureMeasurement, scale: float = 10)
- Adds a temperature cluster.
- `.tuya_temperature(dp_id=7)`

### Entity Methods
- These methods expose an entity to Home Assistant.

#### tuya_switch( \
        dp_id=int, \   
        endpoint_id: int = 1, \
        force_inverted: bool = False, \
        invert_attribute_name: str | None = None, \
        off_value: int = 0, \
        on_value: int = 1, \
        entity_platform=EntityPlatform.SWITCH, \
        entity_type: EntityType = EntityType.CONFIG, \
        initially_disabled: bool = False, \
        attribute_initialized_from_cache: bool = True, \
        translation_key: str | None = None, \
        fallback_name: str | None = None, \
    )

#### tuya_enum

#### tuya_number

#### tuya_binary_sensor

#### tuya_sensor

### Base Methods

#### tuya_dp

#### tuya_dp_attribute