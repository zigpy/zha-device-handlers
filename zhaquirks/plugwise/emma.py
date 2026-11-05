"""Plugwise Emma 170-01 smart thermostat.

The thermostat carries OpenTherm boiler telemetry in manufacturer-specific
attributes on the Thermostat cluster (0x0201), gated by manufacturer code
0x1172. The application and OEM fault codes are the high and low byte of
OpenTherm message ID 5. All temperatures are in hundredths of a degree.

External heat demand overrides the boiler water setpoint until the timeout
expires. The two maximum setpoints read 0 until the boiler has reported them
over OpenTherm, and writing them requires the boiler to allow external control.

Firmware version 10 is the first version officially supported by ZHA. It rejects
ConfigureReporting requests outside the bounds it enforces instead of applying
values it can honour, so the clusters registered for it clamp what ZHA asks for.
Firmware below that version accepts ZHA's defaults and keeps them.
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl import ReportingConfig
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import Status, ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

PLUGWISE: Final = "Plugwise"
PLUGWISE_MFG_CODE: Final = 0x1172

#: First firmware version officially supported by ZHA, and the first that
#: enforces the reporting bounds the clamping clusters below work around.
EMMA_ZHA_SUPPORT_FW_VERSION: Final = 10


class EmmaBatteryType(t.enum8):
    """Battery chemistry the thermostat is running on."""

    Alkaline = 0x00
    NiMH = 0x01


class EmmaApplicationFaultCode(t.bitmap8):
    """OpenTherm application fault bits, the high byte of OpenTherm message ID 5."""

    ServiceRequest = 0b0000_0001
    LockoutReset = 0b0000_0010
    LowWaterPressure = 0b0000_0100
    GasFlameFault = 0b0000_1000
    AirPressureFault = 0b0001_0000
    WaterOverTemp = 0b0010_0000


class EmmaThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster with the Emma OpenTherm telemetry attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Thermostat attributes plus the Emma manufacturer-specific ones."""

        boiler_water_temperature: Final = ZCLAttributeDef(
            id=0xF002,
            type=t.int16s,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        dhw_temperature: Final = ZCLAttributeDef(
            id=0xF003,
            type=t.int16s,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        return_water_temperature: Final = ZCLAttributeDef(
            id=0xF004,
            type=t.int16s,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        application_fault_code: Final = ZCLAttributeDef(
            id=0xF005,
            type=EmmaApplicationFaultCode,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        oem_fault_code: Final = ZCLAttributeDef(
            id=0xF006,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        external_heat_demand: Final = ZCLAttributeDef(
            id=0xF000,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        external_heat_demand_timeout: Final = ZCLAttributeDef(
            id=0xF001,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        max_dhw_setpoint: Final = ZCLAttributeDef(
            id=0xF007,
            type=t.int16s,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        max_boiler_setpoint: Final = ZCLAttributeDef(
            id=0xF008,
            type=t.int16s,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )


class EmmaPowerConfigCluster(CustomCluster, PowerConfiguration):
    """Power Configuration cluster with the Emma battery type attribute."""

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """Power Configuration attributes plus the Emma battery type."""

        battery_type: Final = ZCLAttributeDef(
            id=0x007F,
            type=EmmaBatteryType,
            access="rwp",
            manufacturer_code=PLUGWISE_MFG_CODE,
        )


class ClampedReportingCluster(CustomCluster):
    """Clamp ConfigureReporting parameters into the range the firmware accepts.

    Subclasses narrow a single reporting config in `clamp_reporting`.
    """

    def clamp_reporting(
        self, attr_def: ZCLAttributeDef, config: ReportingConfig
    ) -> ReportingConfig:
        """Return the reporting config to send for `attr_def`."""
        raise NotImplementedError

    async def configure_reporting_multiple(
        self, config: dict[ZCLAttributeDef, ReportingConfig]
    ) -> dict[ZCLAttributeDef, Status]:
        """Configure reporting with every config clamped to the firmware bounds."""
        return await super().configure_reporting_multiple(
            {
                attr_def: self.clamp_reporting(attr_def, attr_config)
                for attr_def, attr_config in config.items()
            }
        )


class EmmaThermostatClusterClamped(ClampedReportingCluster, EmmaThermostatCluster):
    """Thermostat cluster that clamps reporting to the firmware bounds."""

    #: Attributes the firmware only accepts at a minimum interval of at most 1 second
    #: and a maximum interval of at most 870 seconds.
    RESTRICTED_ATTRIBUTE_IDS = frozenset(
        {
            Thermostat.AttributeDefs.local_temperature.id,
            Thermostat.AttributeDefs.pi_cooling_demand.id,
            Thermostat.AttributeDefs.pi_heating_demand.id,
            Thermostat.AttributeDefs.local_temperature_calibration.id,
            Thermostat.AttributeDefs.occupied_cooling_setpoint.id,
            Thermostat.AttributeDefs.occupied_heating_setpoint.id,
            Thermostat.AttributeDefs.system_mode.id,
            Thermostat.AttributeDefs.running_state.id,
        }
    )

    def clamp_reporting(
        self, attr_def: ZCLAttributeDef, config: ReportingConfig
    ) -> ReportingConfig:
        """Narrow the intervals on the restricted attributes and the local temperature change."""
        restricted = attr_def.id in self.RESTRICTED_ATTRIBUTE_IDS
        local_temperature = attr_def.id == Thermostat.AttributeDefs.local_temperature.id
        if not restricted and not local_temperature:
            return config
        return ReportingConfig(
            min_interval=min(config.min_interval, 1)
            if restricted
            else config.min_interval,
            max_interval=min(config.max_interval, 870)
            if restricted
            else config.max_interval,
            # hundredths of a degree
            reportable_change=min(max(config.reportable_change, 1), 10)
            if local_temperature
            else config.reportable_change,
        )


class ClampedMeasurementCluster(ClampedReportingCluster):
    """Measurement cluster whose measured value the firmware reports on fixed intervals."""

    #: Inclusive reportable change range the firmware accepts, in hundredths of a unit.
    CHANGE_RANGE: tuple[int, int]

    def clamp_reporting(
        self, attr_def: ZCLAttributeDef, config: ReportingConfig
    ) -> ReportingConfig:
        """Pin the intervals the firmware demands and clamp the change to its range."""
        if attr_def.id != self.AttributeDefs.measured_value.id:
            return config
        low, high = self.CHANGE_RANGE
        return ReportingConfig(
            min_interval=1,
            max_interval=870,
            reportable_change=min(max(config.reportable_change, low), high),
        )


class EmmaTemperatureClusterClamped(ClampedMeasurementCluster, TemperatureMeasurement):
    """Temperature Measurement cluster that clamps reporting to the firmware bounds."""

    CHANGE_RANGE = (1, 10)


class EmmaHumidityClusterClamped(ClampedMeasurementCluster, RelativeHumidity):
    """Relative Humidity cluster that clamps reporting to the firmware bounds."""

    CHANGE_RANGE = (10, 300)


class EmmaPowerConfigClusterClamped(ClampedReportingCluster, EmmaPowerConfigCluster):
    """Power Configuration cluster that clamps reporting to the firmware bounds."""

    #: Lowest maximum interval the firmware accepts, per attribute.
    MAX_INTERVAL_FLOORS = {
        PowerConfiguration.AttributeDefs.battery_voltage.id: 65534,
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id: 43200,
    }

    def clamp_reporting(
        self, attr_def: ZCLAttributeDef, config: ReportingConfig
    ) -> ReportingConfig:
        """Raise the maximum interval to the floor the firmware accepts."""
        floor = self.MAX_INTERVAL_FLOORS.get(attr_def.id)
        if floor is None:
            return config
        return ReportingConfig(
            min_interval=config.min_interval,
            max_interval=max(config.max_interval, floor),
            reportable_change=config.reportable_change,
        )


# base for both firmware variants below; never added to the registry itself.
emma_base_quirk = (
    QuirkBuilder(PLUGWISE, "170-01")
    .friendly_name(manufacturer=PLUGWISE, model="Emma thermostat")
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.boiler_water_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="boiler_water_temperature",
        fallback_name="Boiler water temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.dhw_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="dhw_temperature",
        fallback_name="DHW temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.return_water_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="return_water_temperature",
        fallback_name="Return water temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.application_fault_code.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="application_fault_code",
        fallback_name="Application fault code",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.oem_fault_code.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="oem_fault_code",
        fallback_name="OEM fault code",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.external_heat_demand.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=90.0,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="external_heat_demand",
        fallback_name="External heat demand",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.external_heat_demand_timeout.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=300,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="external_heat_demand_timeout",
        fallback_name="External heat demand timeout",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_dhw_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_dhw_setpoint",
        fallback_name="Max DHW setpoint",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_boiler_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_boiler_setpoint",
        fallback_name="Max boiler setpoint",
    )
    .enum(
        attribute_name=EmmaPowerConfigCluster.AttributeDefs.battery_type.name,
        enum_class=EmmaBatteryType,
        cluster_id=EmmaPowerConfigCluster.cluster_id,
        translation_key="battery_type",
        fallback_name="Battery type",
    )
)

(
    # version 10 and newer enforce the reporting bounds, as do devices that have
    # not reported a firmware version yet
    emma_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(
        min_version=EMMA_ZHA_SUPPORT_FW_VERSION, allow_missing=True
    )
    .replaces(EmmaThermostatClusterClamped)
    .replaces(EmmaPowerConfigClusterClamped)
    .replaces(EmmaTemperatureClusterClamped)
    .replaces(EmmaHumidityClusterClamped)
    .add_to_registry()
)

(
    # firmware below that version accepts ZHA's default reporting configuration
    emma_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(
        max_version=EMMA_ZHA_SUPPORT_FW_VERSION, allow_missing=False
    )
    .replaces(EmmaThermostatCluster)
    .replaces(EmmaPowerConfigCluster)
    .add_to_registry()
)
