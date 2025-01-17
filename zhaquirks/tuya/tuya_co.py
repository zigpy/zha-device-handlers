"""Tuya Air Quality sensor."""

import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder, TuyaTemperatureMeasurement


class CustomTemperature(t.Struct):
    """Custom temperature wrapper."""

    field_1: t.int16s_be
    temperature: t.int16s_be

    @classmethod
    def from_value(cls, value):
        """Convert from a raw value to a Struct data."""
        return cls.deserialize(value.serialize())[0]


(
    TuyaQuirkBuilder("_TZE200_7bztmfm1", "TS0601")
    .applies_to("_TZE200_mja3fuja", "TS0601")
    .applies_to("_TZE200_dwcarsat", "TS0601")
    .applies_to("_TZE204_dwcarsat", "TS0601")
    .applies_to("_TZE200_8ygsuhe1", "TS0601")  # Tuya Air quality device with GPP
    .applies_to("_TZE200_ryfmq5rl", "TS0601")
    .applies_to("_TZE200_yvx5lh6k", "TS0601")
    .applies_to("_TZE204_yvx5lh6k", "TS0601")
    .applies_to("_TZE200_c2fmom5z", "TS0601")
    .applies_to("_TZE204_c2fmom5z", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_dp(
        dp_id=18,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=lambda x: CustomTemperature.from_value(x).temperature * 10,
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=19, scale=10)
    .tuya_pm25(dp_id=20)
    .tuya_voc(dp_id=21)
    .tuya_formaldehyde(dp_id=22)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_3ejwxpmu", "TS0601")  # Tuya NIDR CO2 sensor
    .tuya_co2(dp_id=2)
    .tuya_dp(
        dp_id=18,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=lambda x: CustomTemperature.from_value(x).temperature * 10,
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=19, scale=10)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_ogkdpgy2", "TS0601")  # Tuya NIDR CO2 sensor with GPP.
    .applies_to("_TZE204_ogkdpgy2", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_dp(
        dp_id=18,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=lambda x: CustomTemperature.from_value(x).temperature * 10,
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=19, scale=10)
    .skip_configuration()
    .add_to_registry()
)
