"""Tuya pool sensor."""

import asyncio
from typing import Final

import zigpy.types as t

from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_MILLION,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricPotential,
    UnitOfTime,
)
from zhaquirks.const import BatterySize
from zhaquirks.tuya import (
    TUYA_QUERY_DATA,
    TUYA_SET_DATA,
    TuyaCommand,
    TuyaDatapointData,
    TuyaNewManufCluster,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

CONDUCTIVITY_MICROSIEMENS_PER_CENTIMETER: Final = "µS/cm"

DP_PH_CALIBRATION_STANDARD: Final = 103
DP_CALIBRATION_KEEP_AWAKE: Final = 105
DP_PH_CALIBRATION: Final = 114
DP_EC_CALIBRATION: Final = 115
DP_ORP_CALIBRATION: Final = 116


class PHCalibrationStandard(t.enum8):
    """Supported pH buffer sets."""

    ASIA = 0
    EUROPE = 1


class TuyaPoolManufCluster(TuyaMCUCluster):
    """Tuya Manufacturer cluster with refresh and calibration logic."""

    CALIBRATION_MEASUREMENT_DELAY: Final = 6
    CALIBRATION_SETTLE_DELAY: Final = 3

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_timer_handle = None
        self._check_timer_handle = None
        self.check_interval = 60
        self.next_refresh_interval = 0
        self.handle_auto_update_check_change()

    def handle_auto_update_cancel(self):
        """Auto update timer cancel."""
        if self._update_timer_handle:
            self._update_timer_handle.cancel()
            self._update_timer_handle = None

    def handle_auto_update_check_cancel(self):
        """Auto update interval check timer cancel."""
        if self._check_timer_handle:
            self._check_timer_handle.cancel()
            self._check_timer_handle = None

    def handle_auto_update_timers_cancel(self):
        """Cancel all auto update timers."""
        self.handle_auto_update_cancel()
        self.handle_auto_update_check_cancel()

    async def _handle_auto_update_delay(self, delay: int):
        """Wait before running the next auto update."""
        await asyncio.sleep(delay)
        self.handle_auto_update_timer_wrapper()

    async def _handle_auto_update_check_delay(self):
        """Wait before checking the auto update interval again."""
        await asyncio.sleep(self.check_interval)
        self.handle_auto_update_check_change()

    def handle_auto_update_setup_next_call(self, force_new_interval=False):
        """Auto update schedule next update."""
        tuya_cluster = self.endpoint.device.endpoints[1].in_clusters.get(
            TuyaMCUCluster.cluster_id, None
        )
        if tuya_cluster and "auto_refresh_interval" in tuya_cluster.attributes_by_name:
            interval = tuya_cluster.get("auto_refresh_interval", 0) * 60
            if interval != self.next_refresh_interval:
                self.handle_auto_update_cancel()
                self.next_refresh_interval = interval
                force_new_interval = True

        if force_new_interval and self.next_refresh_interval > 0:
            self.debug(
                "using refresh interval of %d minutes",
                self.next_refresh_interval // 60,
            )
            self._update_timer_handle = self.endpoint.device.create_task(
                self._handle_auto_update_delay(self.next_refresh_interval)
            )

    def handle_auto_update_check_change(self):
        """Auto update schedule next interval check."""
        self.handle_auto_update_setup_next_call()
        self._check_timer_handle = self.endpoint.device.create_task(
            self._handle_auto_update_check_delay()
        )

    def handle_auto_update_timer_wrapper(self):
        """Auto update handle refresh and schedule next update."""
        self.create_catching_task(self.handle_auto_update())
        self.handle_auto_update_setup_next_call(force_new_interval=True)

    async def handle_auto_update(self):
        """Auto update invoke data refresh command."""
        tuya_cluster = self.endpoint.device.endpoints[1].in_clusters[
            TuyaMCUCluster.cluster_id
        ]
        self.debug("sending refresh query command")
        await tuya_cluster.command(TUYA_QUERY_DATA)

    async def _write_dp_value(self, dp_id: int, value: int) -> None:
        """Write an integer Tuya data point."""
        command = TuyaCommand(
            status=0,
            tsn=self.endpoint.device.application.get_sequence(),
            datapoints=[TuyaDatapointData(dp_id, value)],
        )
        await self.command(TUYA_SET_DATA, command, expect_reply=True)

    async def _calibrate(
        self, source_attribute: str, calibration_dp: int, label: str
    ) -> None:
        """Calibrate from a freshly reported raw sensor reading."""
        await self._write_dp_value(DP_CALIBRATION_KEEP_AWAKE, 1)
        await asyncio.sleep(self.CALIBRATION_MEASUREMENT_DELAY)

        raw_value = self.get(source_attribute)
        if raw_value is None:
            raise ValueError(f"No {label} measurement is available for calibration")

        self.debug(
            "calibrating %s with raw value %d on data point %d",
            label,
            raw_value,
            calibration_dp,
        )
        await self._write_dp_value(calibration_dp, int(raw_value))
        try:
            await asyncio.sleep(self.CALIBRATION_SETTLE_DELAY)
        finally:
            await self._write_dp_value(calibration_dp, 0)

        await self.command(TUYA_QUERY_DATA)

    async def calibrate_ph(self) -> None:
        """Calibrate pH using the closest point in the selected buffer set."""
        await self._calibrate("ph_measured_value", DP_PH_CALIBRATION, "pH")

    async def calibrate_ec(self) -> None:
        """Calibrate electrical conductivity using the current reading."""
        await self._calibrate("ec_measured_value", DP_EC_CALIBRATION, "EC")

    async def calibrate_orp(self) -> None:
        """Calibrate oxidation-reduction potential using the current reading."""
        await self._calibrate("redox_potential", DP_ORP_CALIBRATION, "ORP")


(
    TuyaQuirkBuilder("_TZE200_v1jqz5cy", "TS0601")
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    .tuya_battery(
        dp_id=7,
        battery_type=BatterySize.Built_in,
        battery_qty=4,
        battery_voltage=36,
        scale=1,
    )
    .tuya_temperature(dp_id=2, scale=10)
    .tuya_sensor(
        dp_id=10,
        attribute_name="ph_measured_value",
        divisor=100,
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PH,
        translation_key="ph_measured_value",
        fallback_name="pH",
    )
    .tuya_sensor(
        dp_id=1,
        attribute_name="total_dissolved_solids",
        type=t.uint16_t,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="total_dissolved_solids",
        fallback_name="Total dissolved solids",
    )
    .tuya_sensor(
        dp_id=11,
        attribute_name="ec_measured_value",
        type=t.uint16_t,
        unit=CONDUCTIVITY_MICROSIEMENS_PER_CENTIMETER,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="ec_measured_value",
        fallback_name="Electrical conductivity",
    )
    .tuya_sensor(
        dp_id=117,
        attribute_name="salt_measured_value",
        type=t.uint16_t,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="salt_measured_value",
        fallback_name="Salt concentration",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="redox_potential",
        type=t.int16s,
        unit=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="redox_potential",
        fallback_name="ORP level",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="cl_measured_value",
        type=t.uint16_t,
        divisor=10,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="cl_measured_value",
        fallback_name="Chlorine concentration",
    )
    .tuya_enum(
        dp_id=DP_PH_CALIBRATION_STANDARD,
        attribute_name="ph_calibration_standard",
        enum_class=PHCalibrationStandard,
        translation_key="ph_calibration_standard",
        fallback_name="pH calibration standard",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="ph_max_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=14,
        mode="box",
        device_class=NumberDeviceClass.PH,
        translation_key="ph_max_value",
        fallback_name="pH maximum value",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="ph_min_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=14,
        mode="box",
        device_class=NumberDeviceClass.PH,
        translation_key="ph_min_value",
        fallback_name="pH minimum value",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="ec_max_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=0,
        max_value=20000,
        mode="box",
        unit=CONDUCTIVITY_MICROSIEMENS_PER_CENTIMETER,
        translation_key="ec_max_value",
        fallback_name="EC maximum value",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="ec_min_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=0,
        max_value=20000,
        mode="box",
        unit=CONDUCTIVITY_MICROSIEMENS_PER_CENTIMETER,
        translation_key="ec_min_value",
        fallback_name="EC minimum value",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="orp_max_value",
        type=t.int16s,
        multiplier=1,
        step=1,
        min_value=-999,
        max_value=999,
        mode="box",
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="orp_max_value",
        fallback_name="ORP maximum value",
    )
    .tuya_number(
        dp_id=111,
        attribute_name="orp_min_value",
        type=t.int16s,
        multiplier=1,
        step=1,
        min_value=-999,
        max_value=999,
        mode="box",
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="orp_min_value",
        fallback_name="ORP minimum value",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="cl_max_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=4,
        mode="box",
        unit=CONCENTRATION_PARTS_PER_MILLION,
        translation_key="cl_max_value",
        fallback_name="Cl maximum value",
    )
    .tuya_number(
        dp_id=113,
        attribute_name="cl_min_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=4,
        mode="box",
        unit=CONCENTRATION_PARTS_PER_MILLION,
        translation_key="cl_min_value",
        fallback_name="Cl minimum value",
    )
    .tuya_dp_attribute(
        dp_id=DP_PH_CALIBRATION,
        attribute_name="ph_calibration_result",
        type=t.int32s,
    )
    .tuya_dp_attribute(
        dp_id=DP_EC_CALIBRATION,
        attribute_name="ec_calibration_result",
        type=t.int32s,
    )
    .tuya_dp_attribute(
        dp_id=DP_ORP_CALIBRATION,
        attribute_name="orp_calibration_result",
        type=t.int32s,
    )
    .command_button(
        command_name=TuyaNewManufCluster.ServerCommandDefs.query_data.name,
        cluster_id=TuyaNewManufCluster.cluster_id,
        translation_key="update",
        fallback_name="Update",
    )
    .command_button(
        command_name="calibrate_ph",
        cluster_id=TuyaNewManufCluster.cluster_id,
        translation_key="calibrate_ph",
        fallback_name="Calibrate pH",
    )
    .command_button(
        command_name="calibrate_ec",
        cluster_id=TuyaNewManufCluster.cluster_id,
        translation_key="calibrate_ec",
        fallback_name="Calibrate EC",
    )
    .command_button(
        command_name="calibrate_orp",
        cluster_id=TuyaNewManufCluster.cluster_id,
        translation_key="calibrate_orp",
        fallback_name="Calibrate ORP",
    )
    .tuya_number(
        dp_id=9,
        attribute_name="auto_refresh_interval",
        type=t.uint16_t,
        translation_key="auto_refresh_interval",
        fallback_name="Refresh interval",
        unit=UnitOfTime.MINUTES,
        step=5,
        min_value=0,
        max_value=1440,
    )
    .add_to_registry(replacement_cluster=TuyaPoolManufCluster)
)
