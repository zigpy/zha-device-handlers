"""Tuya Air Quality sensor."""

from typing import Any

import zigpy.types as t

from zhaquirks.tuya.builder import (
    MOL_VOL_AIR_NTP,
    TuyaFormaldehydeConcentration,
    TuyaPM25Concentration,
    TuyaQuirkBuilder,
    TuyaTemperatureMeasurement,
)


def tuya_air_quality_temperature_converter(value: Any) -> int:
    """Convert Tuya air quality temperature data to centidegrees.

    Extract temperature from bytes 2-4 of the data payload and convert to centidegrees.
    The device sends a 4-byte structure: [field_1 (2 bytes), temperature (2 bytes)]
    """
    return int.from_bytes(value.serialize()[2:4], byteorder="big", signed=True) * 10


class TuyaPM25ConcentrationIgnoreValues(TuyaPM25Concentration):
    """Tuya PM25 concentration measurement cluster that ignores invalid high values."""

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Update an attribute on this cluster and ignore values over 1000."""
        if attrid == self.AttributeDefs.measured_value.id and value > 1000:
            return
        super()._update_attribute(attrid, value)


base_air_quality = (
    TuyaQuirkBuilder()
    .tuya_dp(
        dp_id=18,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=tuya_air_quality_temperature_converter,
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=19, scale=10)
    .skip_configuration()
)


(
    base_air_quality.clone()
    # 18 and 19 from base
    .applies_to("_TZE200_dwcarsat", "TS0601")
    .applies_to("_TZE204_dwcarsat", "TS0601")
    .tuya_pm25(dp_id=2, pm25_cfg=TuyaPM25ConcentrationIgnoreValues)
    .tuya_formaldehyde(
        dp_id=20,
        converter=lambda x: round(
            ((MOL_VOL_AIR_NTP * x) / TuyaFormaldehydeConcentration.MOLECULAR_MASS), 2
        )
        * 1e-6,
    )
    .tuya_voc(dp_id=21)
    .tuya_co2(dp_id=22)
    .add_to_registry()
)

(
    base_air_quality.clone()
    # 18 and 19 from base
    .applies_to("_TZE200_ryfmq5rl", "TS0601")
    .tuya_formaldehyde(
        dp_id=2,
        converter=lambda x: round(
            ((MOL_VOL_AIR_NTP * x) / TuyaFormaldehydeConcentration.MOLECULAR_MASS), 2
        )
        * 1e-8,
    )
    .tuya_voc(dp_id=21, scale=1e-7)
    .tuya_co2(dp_id=22)
    .add_to_registry()
)


(
    base_air_quality.clone()
    # 18 and 19 from base
    .applies_to("_TZE200_mja3fuja", "TS0601")
    .tuya_formaldehyde(dp_id=2)
    .tuya_voc(dp_id=21)
    .tuya_co2(dp_id=22)
    .add_to_registry()
)


(
    base_air_quality.clone()
    # 18 and 19 from base
    .applies_to("_TZE200_7bztmfm1", "TS0601")
    .applies_to("_TZE200_8ygsuhe1", "TS0601")  # Tuya Air quality device with GPP
    .applies_to("_TZE200_yvx5lh6k", "TS0601")
    .applies_to("_TZE204_yvx5lh6k", "TS0601")
    .applies_to("_TZE200_c2fmom5z", "TS0601")
    .applies_to("_TZE204_c2fmom5z", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_pm25(dp_id=20)
    .tuya_voc(dp_id=21)
    .tuya_formaldehyde(dp_id=22)
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_3ejwxpmu", "TS0601")  # Tuya NIDR CO2 sensor
    .tuya_co2(dp_id=2)
    .tuya_dp(
        dp_id=18,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=tuya_air_quality_temperature_converter,
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
        converter=tuya_air_quality_temperature_converter,
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=19, scale=10)
    .skip_configuration()
    .add_to_registry()
)
