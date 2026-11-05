"""Tuya Air Quality sensor."""

import asyncio
from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic

from zhaquirks.clusters import CustomCluster
from zhaquirks.tuya import TUYA_CLUSTER_ID, TUYA_QUERY_DATA
from zhaquirks.tuya.builder import (
    MOL_VOL_AIR_NTP,
    TuyaFormaldehydeConcentration,
    TuyaPM25Concentration,
    TuyaQuirkBuilder,
    TuyaTemperatureMeasurement,
)
from zhaquirks.tuya.mcu import TuyaMCUCluster


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


class TuyaCO2ManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster that records whether the MCU is still sending data."""

    # Set whenever the MCU sends us anything, cleared when TuyaCO2Basic checks it.
    reported_since_last_check: bool = False

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Any | None = None,
    ) -> None:
        """Note that the MCU is talking to us, then handle the request."""
        self.reported_since_last_check = True
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class TuyaCO2Basic(CustomCluster, Basic):
    """Basic cluster that re-queries the MCU when it has fallen silent.

    _TZE204_pkpfn9hc sends nothing at all on the Tuya cluster until it receives
    a data query, and it returns to that state after a power cycle. It emits no
    ZDO announce when it reboots, so the only usable signal is its periodic
    unsolicited Basic attribute report. If no datapoint arrived since the last
    such report the MCU is presumed silent and is queried again, which restores
    reporting within seconds instead of never.
    """

    # Give the MCU a moment to finish booting before asking it for data.
    QUERY_DELAY = 2

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Any | None = None,
    ) -> None:
        """Re-query the MCU if it produced no data since the last report."""
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)

        if hdr.command_id != foundation.GeneralCommand.Report_Attributes:
            return

        tuya_cluster = self.endpoint.in_clusters[TUYA_CLUSTER_ID]
        if tuya_cluster.reported_since_last_check:
            tuya_cluster.reported_since_last_check = False
            return

        self.debug("Tuya MCU has gone silent, re-sending data query")
        self.endpoint.device.create_task(
            self._query_data(tuya_cluster),
            name=f"tuya_co2_query_data_{self.endpoint.device.ieee}",
        )

    async def _query_data(self, tuya_cluster: TuyaMCUCluster) -> None:
        """Ask the MCU to resend every datapoint."""
        await asyncio.sleep(self.QUERY_DELAY)
        await tuya_cluster.command(TUYA_QUERY_DATA)


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
        converter=lambda x: (
            round(
                ((MOL_VOL_AIR_NTP * x) / TuyaFormaldehydeConcentration.MOLECULAR_MASS),
                2,
            )
            * 1e-6
        ),
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
        converter=lambda x: (
            round(
                ((MOL_VOL_AIR_NTP * x) / TuyaFormaldehydeConcentration.MOLECULAR_MASS),
                2,
            )
            * 1e-8
        ),
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
    # Winsen MH-Z19D NDIR CO2 sensor in a desktop LCD monitor.
    #
    # Unlike the other NDIR CO2 sensors above, this one reports temperature as
    # a plain scaled integer (302 -> 30.2 degC) rather than the packed struct
    # tuya_air_quality_temperature_converter decodes, and reports humidity in
    # whole percent rather than tenths.
    #
    # It also reports configuration datapoints that are left unmapped because
    # their meaning is unconfirmed: 101 (enum, display mode), 102, 103, 104,
    # 105 and 106 (60, matching the observed 60 second reporting interval).
    TuyaQuirkBuilder("_TZE204_pkpfn9hc", "TS0601")
    .tuya_enchantment(data_query_spell=True)
    .replaces(TuyaCO2Basic)
    .tuya_co2(dp_id=2)
    .tuya_temperature(dp_id=18, scale=10)
    .tuya_humidity(dp_id=19)
    .skip_configuration()
    .add_to_registry(replacement_cluster=TuyaCO2ManufCluster)
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
