"""Tuya Air Quality sensor."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_7bztmfm1", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_temperature(dp_id=18, scale=10)
    .tuya_humidity(dp_id=19, scale=10)
    .tuya_pm25(dp_id=20)
    .tuya_voc(dp_id=21)
    .tuya_formaldehyde(dp_id=22)
    .skip_configuration()
    .add_to_registry()
)
