# Tuya quirks

Tuya devices use datapoints (DPs) instead of ZCL attributes. Use `TuyaQuirkBuilder` (`zhaquirks/tuya/builder/__init__.py`); the repository's [tuya.md](../../../tuya.md) explains how to find DPs and documents its methods.

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

Rules:

- Prefer the dedicated methods (`.tuya_temperature()`, `.tuya_humidity()`, `.tuya_battery()`, `.tuya_illuminance()`, `.tuya_contact()`, `.tuya_onoff()`, `.tuya_metering()`, …) over a generic `.tuya_sensor()` or a hand-written `.tuya_dp()`: they map onto standard ZCL clusters, so ZHA creates its usual entities.
- Hand-rolled `TuyaMCUCluster` subclasses are for behaviour the builder can't express; they must define `data_point_handlers` as well as `dp_to_attribute`.
- Check each DP's scale and polarity against real reports or the device's Zigbee2MQTT converter. Z2M's `divideBy10` means the raw value is in tenths: `divisor=10` on `.tuya_sensor()`, while the dedicated methods' `scale` multiplies the raw value up to the ZCL unit (`.tuya_temperature()` reports hundredths of a degree, so tenths need `scale=10`). Z2M's `trueFalse0` means the value is true when the raw DP is `0`, not `1`. Keep a measurement and its thresholds on the same scale.
- Many Tuya devices reject binding and reporting setup; that is when `.skip_configuration()` applies.
- Several manufacturer IDs often share one quirk: add them with `.applies_to()` to the existing builder rather than copying it.
