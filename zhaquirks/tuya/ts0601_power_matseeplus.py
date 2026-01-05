"""Tuya MatSeePlus 2 CT Bidirectional Energy Meter."""

from __future__ import annotations

from typing import Any, Final

from zigpy.quirks.v2.homeassistant import PERCENTAGE, EntityType, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.homeautomation import MeasurementType
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.tuya import (
    TuyaLocalCluster,
    TuyaZBElectricalMeasurement,
    TuyaZBMeteringClusterWithUnit,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

ENDPOINT_ID_CT_A = 1
ENDPOINT_ID_CT_B = 2
ENDPOINT_ID_TOTAL = 3


class TuyaEnergyFlow(t.enum8):
    """Energy flow direction attribute values."""

    Forward = 0x00
    Reverse = 0x01


class MatSeePlusLocalConfig(LocalDataCluster):
    """Cluster for storing local configuration.

    Allows control over the delayed energy flow bug mitigation.
    """

    cluster_id: Final[t.uint16_t] = 0xFC00
    name: Final = "Local Configuration"
    ep_attribute: Final = "local_config"

    class AttributeDefs(BaseAttributeDefs):
        """Configuration attributes."""

        late_energy_flow_a = ZCLAttributeDef(
            id=0x5010,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )
        late_energy_flow_b = ZCLAttributeDef(
            id=0x5011,
            type=t.Bool,
            access="rw",
            is_manufacturer_specific=True,
        )


class MatSeePlusElectricalMeasurement(TuyaZBElectricalMeasurement, TuyaLocalCluster):
    """ElectricalMeasurement cluster for MatSeePlus CT energy meter with flow delay mitigation.

    _TZE204_81yrt3lo (app_version: 74, hw_version: 1 and stack_version: 0) has a bug
    where the current energy flow values are incorrectly emitted during the next reporting interval.
    This means a change in direction result in incorrect power values.

    The bug has remained unfixed for multiple years, with no provided firmware updates from the manufacturer.
    When enabled this mitigation holds non-power attribute values until the subsequent interval's attribute report.
    This ensures correct values, but introduces a delay in entity updates.

    This is optional and defaults to off because some use cases only have energy flowing in a single direction.
    """

    # Map Endpoint ID to the corresponding late energy flow config attribute
    _EP_LATE_FLOW_CONFIG_ATTR: dict[int, str] = {
        ENDPOINT_ID_CT_A: MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_a.name,
        ENDPOINT_ID_CT_B: MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_b.name,
    }

    _CONSTANT_ATTRIBUTES: dict[int, Any] = {
        **TuyaZBElectricalMeasurement._CONSTANT_ATTRIBUTES,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.measurement_type.id: MeasurementType.Active_measurement_AC
        | MeasurementType.Phase_A_measurement,
    }

    _VALID_ATTRIBUTES: set[int] = {
        TuyaZBElectricalMeasurement.AttributeDefs.active_power.id,
        TuyaZBElectricalMeasurement.AttributeDefs.power_factor.id,
        TuyaZBElectricalMeasurement.AttributeDefs.rms_current.id,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._held_values: dict[str, Any] = {}
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.apparent_power.id
        )
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency.id
        )
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.rms_voltage.id
        )

    def _late_energy_flow_delay_handler(self, attr_name: str, value: Any) -> Any:
        """Hold non-power attribute values until the next update is received from the device."""
        if attr_name == TuyaZBElectricalMeasurement.AttributeDefs.active_power.name:
            return value
        held_value = self._held_values.pop(attr_name, None)

        config_attr = self._EP_LATE_FLOW_CONFIG_ATTR.get(self.endpoint.endpoint_id)
        if not bool(self.endpoint.device.endpoints[1].local_config.get(config_attr)):
            return value

        self._held_values[attr_name] = value
        return held_value

    def update_attribute(self, attr_name: str, value):
        """Update the cluster attribute."""
        if self.endpoint.endpoint_id in self._EP_LATE_FLOW_CONFIG_ATTR:
            value = self._late_energy_flow_delay_handler(attr_name, value)
        super().update_attribute(attr_name, value)


class MatSeePlusElectricalMeasurementTotal(
    TuyaZBElectricalMeasurement, TuyaLocalCluster
):
    """ElectricalMeasurement cluster for MatSeePlus CT Energy Meter common measurements and total power."""

    _CONSTANT_ATTRIBUTES: dict[int, Any] = {
        **MatSeePlusElectricalMeasurement._CONSTANT_ATTRIBUTES,
        TuyaZBElectricalMeasurement.AttributeDefs.measurement_type.id: MeasurementType.Active_measurement_AC,
    }

    _VALID_ATTRIBUTES: set[int] = {
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency.id,
        TuyaZBElectricalMeasurement.AttributeDefs.rms_voltage.id,
        TuyaZBElectricalMeasurement.AttributeDefs.total_active_power.id,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.active_power.id
        )
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.apparent_power.id
        )
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.power_factor.id
        )
        self.add_unsupported_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.rms_current.id
        )


class MatSeePlusMetering(TuyaZBMeteringClusterWithUnit, TuyaLocalCluster):
    """Metering cluster for MatSeePlus CT energy meter."""

    _VALID_ATTRIBUTES: set[int] = {
        TuyaZBMeteringClusterWithUnit.AttributeDefs.current_summ_delivered.id,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.current_summ_received.id,
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            TuyaZBMeteringClusterWithUnit.AttributeDefs.instantaneous_demand.id
        )


class TuyaMatSeePlusManufCluster(TuyaMCUCluster):
    """Handle MatSeePlus power datapoint logic, addressing known firmware issues.

    - Sequence power DP value signing and reporting to Electrical Measurement clusters respective of reporting sequence and config.
    - Recalculate the AB total power because the reported value on DP 115 is inaccurate due to the flow delay bug.
    """

    ENERGY_FLOW_A: Final = "energy_flow_a"
    ENERGY_FLOW_B: Final = "energy_flow_b"
    POWER_A: Final = "power_a"
    POWER_B: Final = "power_b"

    def __init__(self, *args, **kwargs):
        """Init."""
        self._interval: int | None = None
        self._interval_complete: bool = True
        self._report_interval_a: int | None = None
        self._report_interval_b: int | None = None
        self._power_a: int | None = None
        self._power_b: int | None = None
        self._deferred_power_a: int | None = None
        self._deferred_power_b: int | None = None
        super().__init__(*args, **kwargs)

    @staticmethod
    def _align_unsigned_value_with_energy_flow(
        value: int, direction: TuyaEnergyFlow | None
    ) -> int | None:
        """Align the input value with specified energy flow direction."""
        if value and value > 0 and direction == TuyaEnergyFlow.Reverse:
            value = -value
        return value

    def _maybe_report_total_power(self):
        """Calculate and report total power if both channels are ready."""
        if (
            self._interval is not None
            and self._interval == self._report_interval_a == self._report_interval_b
            and self._power_a is not None
            and self._power_b is not None
        ):
            self.endpoint.device.endpoints[
                ENDPOINT_ID_TOTAL
            ].electrical_measurement.update_attribute(
                MatSeePlusElectricalMeasurementTotal.AttributeDefs.total_active_power.name,
                self._power_a + self._power_b,
            )

    def _process_power_and_energy_flow(
        self,
        attr_name: str,
        value: int | TuyaEnergyFlow,
        power_attr: str,
        energy_flow_attr: str,
        late_energy_flow: bool,
        report_endpoint_id: int,
        current_power: int | None,
        deferred_power: int | None,
        report_interval: int | None,
    ) -> tuple[int | None, int | None, int | None]:
        """Process power and energy flow DP updates.

        Computes signed power based on DP reporting order and user configuration.

        If late_energy_flow == True, the flow DP value applies to the previous interval's power
        (firmware bug on _TZE204_81yrt3lo), so power is signed when the flow DP arrives.

        Special handling for zero power with late_energy_flow enabled:
        The device omits the energy flow DP when power is zero, so when zero power arrives,
        we sign the last received power value with the stored flow and defer the actual zero
        until the next interval. This prevents the zero from overwriting the stored value
        before total power calculation and maintains consistent update timing.

        Returns tuple of (current_power, deferred_power, report_interval).
        """
        power = None

        # Compute signed power based on configuration and DP reporting order
        if self._interval is None:
            pass
        elif late_energy_flow:
            if deferred_power is not None:
                # Release deferred power before processing new values
                power = deferred_power
                deferred_power = None

            if attr_name == energy_flow_attr:
                # Sign previous power using current flow value
                power = self._align_unsigned_value_with_energy_flow(
                    self.get(power_attr), value
                )
            elif attr_name == power_attr and value == 0:
                # The flow DP was omitted in this interval, sign previous power using stored energy flow
                power = self._align_unsigned_value_with_energy_flow(
                    self.get(power_attr), self.get(energy_flow_attr)
                )
                # Defer zero power until next interval
                deferred_power = 0
        elif attr_name == power_attr:
            # Sign power immediately
            power = self._align_unsigned_value_with_energy_flow(
                value, self.get(energy_flow_attr)
            )
            deferred_power = None

        # Update and report current power if there is a new value, otherwise keep existing value
        if power is not None:
            current_power = power
            report_interval = self._interval
            self.endpoint.device.endpoints[
                report_endpoint_id
            ].electrical_measurement.update_attribute(
                MatSeePlusElectricalMeasurement.AttributeDefs.active_power.name,
                power,
            )

        return current_power, deferred_power, report_interval

    def update_attribute(self, attr_name: str, value):
        """Handle reports to Electrical Measurement power attributes after aligning with energy flow.

        DP reporting sequence per interval:
        1. ENERGY_FLOW_A (omitted if current interval power is 0, contains value for previous interval on _TZE204_81yrt3lo)
        2. POWER_A (for current interval)
        3. ENERGY_FLOW_B (omitted if current interval power is 0, contains value for previous interval on _TZE204_81yrt3lo)
        4. POWER_B (for current interval)
        """

        if attr_name in (self.ENERGY_FLOW_A, self.POWER_A):
            # Increment interval when the first A sequence update is received
            if self._interval_complete:
                self._interval_complete = False
                self._interval = (self._interval or 0) + 1

            # Process new values for ENERGY_FLOW_A and POWER_A
            self._power_a, self._deferred_power_a, self._report_interval_a = (
                self._process_power_and_energy_flow(
                    attr_name,
                    value,
                    power_attr=self.POWER_A,
                    energy_flow_attr=self.ENERGY_FLOW_A,
                    late_energy_flow=self.endpoint.local_config.get(
                        MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_a.name
                    ),
                    current_power=self._power_a,
                    deferred_power=self._deferred_power_a,
                    report_endpoint_id=ENDPOINT_ID_CT_A,
                    report_interval=self._report_interval_a,
                )
            )

        elif attr_name in (self.ENERGY_FLOW_B, self.POWER_B):
            # Process new values for ENERGY_FLOW_B and POWER_B
            self._power_b, self._deferred_power_b, self._report_interval_b = (
                self._process_power_and_energy_flow(
                    attr_name,
                    value,
                    power_attr=self.POWER_B,
                    energy_flow_attr=self.ENERGY_FLOW_B,
                    late_energy_flow=self.endpoint.local_config.get(
                        MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_b.name
                    ),
                    current_power=self._power_b,
                    deferred_power=self._deferred_power_b,
                    report_endpoint_id=ENDPOINT_ID_CT_B,
                    report_interval=self._report_interval_b,
                )
            )

            # Attempt to report total power
            self._maybe_report_total_power()

            # Mark interval complete after POWER_B is processed
            if attr_name == self.POWER_B:
                self._interval_complete = True

        super().update_attribute(attr_name, value)


# MatSeePlus Tuya PJ-1203A 2 CT Bidirectional Energy Meter base quirk
pj_1203a_base_quirk = (
    TuyaQuirkBuilder()
    .tuya_enchantment()
    .adds_endpoint(ENDPOINT_ID_CT_B)
    .adds_endpoint(ENDPOINT_ID_TOTAL)
    .adds(MatSeePlusElectricalMeasurement)
    .adds(MatSeePlusElectricalMeasurement, endpoint_id=ENDPOINT_ID_CT_B)
    .adds(MatSeePlusElectricalMeasurementTotal, endpoint_id=ENDPOINT_ID_TOTAL)
    .adds(MatSeePlusMetering)
    .adds(MatSeePlusMetering, endpoint_id=ENDPOINT_ID_CT_B)
    .adds(MatSeePlusLocalConfig)
    # Metering attributes
    .tuya_dp(
        dp_id=106,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_delivered.name,
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_delivered.name,
        endpoint_id=ENDPOINT_ID_CT_B,
    )
    .tuya_dp(
        dp_id=107,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_received.name,
    )
    .tuya_dp(
        dp_id=109,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_received.name,
        endpoint_id=ENDPOINT_ID_CT_B,
    )
    # Power attributes handled within manufacturer cluster
    .tuya_dp_attribute(
        dp_id=101,
        attribute_name=TuyaMatSeePlusManufCluster.POWER_A,
        type=t.uint32_t_be,
    )
    .tuya_dp_attribute(
        dp_id=105,
        attribute_name=TuyaMatSeePlusManufCluster.POWER_B,
        type=t.uint32_t_be,
    )
    .tuya_dp_attribute(
        dp_id=102,
        attribute_name=TuyaMatSeePlusManufCluster.ENERGY_FLOW_A,
        type=TuyaEnergyFlow,
    )
    .tuya_dp_attribute(
        dp_id=104,
        attribute_name=TuyaMatSeePlusManufCluster.ENERGY_FLOW_B,
        type=TuyaEnergyFlow,
    )
    # Electrical measurement attributes
    .tuya_dp(
        dp_id=110,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=MatSeePlusElectricalMeasurement.AttributeDefs.power_factor.name,
    )
    .tuya_dp(
        dp_id=121,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=MatSeePlusElectricalMeasurement.AttributeDefs.power_factor.name,
        endpoint_id=ENDPOINT_ID_CT_B,
    )
    .tuya_dp(
        dp_id=113,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=MatSeePlusElectricalMeasurement.AttributeDefs.rms_current.name,
    )
    .tuya_dp(
        dp_id=114,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=MatSeePlusElectricalMeasurement.AttributeDefs.rms_current.name,
        endpoint_id=ENDPOINT_ID_CT_B,
    )
    .tuya_dp(
        dp_id=112,
        ep_attribute=MatSeePlusElectricalMeasurementTotal.ep_attribute,
        attribute_name=MatSeePlusElectricalMeasurementTotal.AttributeDefs.rms_voltage.name,
        endpoint_id=ENDPOINT_ID_TOTAL,
    )
    .tuya_dp(
        dp_id=111,
        ep_attribute=MatSeePlusElectricalMeasurementTotal.ep_attribute,
        attribute_name=MatSeePlusElectricalMeasurementTotal.AttributeDefs.ac_frequency.name,
        endpoint_id=ENDPOINT_ID_TOTAL,
    )
    # Local configuration attributes
    .switch(
        MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_a.name,
        MatSeePlusLocalConfig.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="late_energy_flow_a",
        fallback_name="Late energy flow A",
        initially_disabled=True,
    )
    .switch(
        MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_b.name,
        MatSeePlusLocalConfig.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="late_energy_flow_b",
        fallback_name="Late energy flow B",
        initially_disabled=True,
    )
    # Device configuration attributes
    .tuya_number(
        dp_id=129,
        attribute_name="reporting_interval",
        type=t.uint32_t_be,
        unit=UnitOfTime.SECONDS,
        min_value=10,
        max_value=60,
        step=1,
        translation_key="reporting_interval",
        fallback_name="Reporting interval",
        entity_type=EntityType.CONFIG,
    )
    .tuya_number(
        dp_id=122,
        attribute_name="ac_frequency_coefficient",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_ac_frequency",
        fallback_name="Calibrate AC frequency",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=116,
        attribute_name="voltage_coefficient",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_voltage",
        fallback_name="Calibrate voltage",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=119,
        attribute_name="current_summ_delivered_coefficient_a",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_summ_delivered_a",
        fallback_name="Calibrate summation delivered A",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=125,
        attribute_name="current_summ_delivered_coefficient_b",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_summ_delivered_b",
        fallback_name="Calibrate summation delivered B",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=127,
        attribute_name="current_summ_received_coefficient_a",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_summ_received_a",
        fallback_name="Calibrate summation received A",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=128,
        attribute_name="current_summ_received_coefficient_b",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_summ_received_b",
        fallback_name="Calibrate summation received B",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=118,
        attribute_name="power_coefficient_a",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_power_a",
        fallback_name="Calibrate power A",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=124,
        attribute_name="power_coefficient_b",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_power_b",
        fallback_name="Calibrate power B",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=117,
        attribute_name="current_coefficient_a",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_current_a",
        fallback_name="Calibrate current A",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .tuya_number(
        dp_id=123,
        attribute_name="current_coefficient_b",
        type=t.uint32_t_be,
        unit=PERCENTAGE,
        min_value=0,
        max_value=2000,
        step=0.1,
        multiplier=0.1,
        translation_key="calibrate_current_b",
        fallback_name="Calibrate current B",
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
    )
    .skip_configuration()
)

# MatSeePlus Tuya PJ-1203A versions without firmware bug
(
    pj_1203a_base_quirk.clone()
    .applies_to("_TZE284_81yrt3lo", "TS0601")
    .add_to_registry(replacement_cluster=TuyaMatSeePlusManufCluster)
)

# MatSeePlus Tuya PJ-1203A versions with known firmware bug
(
    pj_1203a_base_quirk.clone()
    .applies_to("_TZE204_81yrt3lo", "TS0601")
    .switch(
        MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_a.name,
        MatSeePlusLocalConfig.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="late_energy_flow_a",
        fallback_name="Late energy flow A",
        initially_disabled=False,
    )
    .switch(
        MatSeePlusLocalConfig.AttributeDefs.late_energy_flow_b.name,
        MatSeePlusLocalConfig.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="late_energy_flow_b",
        fallback_name="Late energy flow B",
        initially_disabled=False,
    )
    .add_to_registry(replacement_cluster=TuyaMatSeePlusManufCluster)
)
