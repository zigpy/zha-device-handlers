"""Schneider Electric thermostats quirks."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    EntityPlatform,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.hvac import SystemMode, Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef

from zhaquirks.schneiderelectric import SE_MANUF_NAME, SEBasic


class SETemperatureSensorType(t.enum8):
    """Temperature sensor connected to thermostat."""

    Sensor2kOhm = 0x01
    Sensor10kOhm = 0x02
    Sensor12kOhm = 0x03
    Sensor15kOhm = 0x04
    Sensor33kOhm = 0x05
    Sensor47kOhm = 0x06
    SensorAbsent = 0xFF


class SEControlStatus(t.enum8):
    """Control status of the thermostat."""

    # Operating normally
    NormalOperation = 0x00

    # No temperature value is available. The output is using Fallback rules
    NoTemperature = 0x20

    # Output has been forced using a remote override
    RemoteDemandOverride = 0x40

    # Demand is constrained by Window Open rules
    WindowOpen = 0x41

    # Demand forced by "emergency" button
    LocalForceOn = 0x61

    # The output is being driven as part of a maintenance operation
    Maintenance = 0x82

    # Output held on, or off, despite a change in demand due to minimum times
    OutputTemporalLimit = 0x83

    # The output has been placed into a safe state due to a sensor failure
    SensorFault = 0x84


class SELocalTemperatureSourceSelect(t.enum8):
    """Local temperature source select."""

    # Internal temperature sensor
    Ambient = 0x02

    # External temperature sensor
    External = 0x03


class SEControlType(t.enum8):
    """Control type of the thermostat."""

    OnOff = 0x00
    PI = 0x01
    NoControl = 0xFF


class SEHeatCoolInputMode(t.enum8):
    """Heat/Cool input mode."""

    CoolingWhenActive = 0x00
    HeatingWhenActive = 0x01
    NotConnected = 0xFF


class SEThermostatApplication(t.enum8):
    """Thermostat application."""

    OccupiedSpace = 0x00
    Floor = 0x01
    NotKnown = 0xFF


class SEHeatingFuel(t.enum8):
    """Heating fuel."""

    Electricity = 0x00
    Gas = 0x01
    Oil = 0x02
    SolidFuel = 0x03
    Solar = 0x04
    ComunityHeating = 0x05
    HeatPump = 0x06
    NotSpecified = 0xFF


class SEHeatTransferMedium(t.enum8):
    """Heat transfer medium."""

    Nothing = 0x00
    Hydronic = 0x01
    Air = 0x02


class SEHeatingEmitterType(t.enum8):
    """Heating emitter type."""

    Direct = 0x00
    Radiator = 0x01
    FanAssistedRadiator = 0x02
    RadiantPanel = 0x03
    Floor = 0x04
    NotSpecified = 0xFF


class SEDemandOverrideType(t.enum8):
    """Demand override type."""

    NoDemandOverride = 0x00
    CoolingDemandOverride = 0x03
    HeatingDemandOverride = 0x04


class SESetpointChangeReason(t.enum8):
    """Setpoint change reason."""

    SetpointAdjustment = 0x00
    BoostUsed = 0x01
    BoostCancel = 0x02
    SystemModeChange = 0x03
    AwayStart = 0x04
    AwayEnd = 0x05


class SEAffectedSetpoint(t.enum8):
    """Affected setpoint."""

    Nothing = 0x00
    OccupiedHeating = 0x01
    OccupiedCooling = 0x02
    UnoccupiedHeating = 0x03
    UnoccupiedCooling = 0x04


class SECoolingOutputMode(t.enum8):
    """Cooling output mode."""

    Disabled = 0x00
    Relay = 0x01
    RelayNC = 0x04


class SEHeatingOutputMode(t.enum8):
    """Heating output mode."""

    Disabled = 0x00
    Relay = 0x01
    OpenTherm = 0x02
    FilPilote = 0x03
    RelayNC = 0x04


class SEMetering(CustomCluster, Metering):
    """Schneider Electric Metering cluster."""

    class AttributeDefs(Metering.AttributeDefs):
        """Schneider Electric Metering cluster attributes."""

        # This attribute specifies the demand of a switched load when it is energised
        se_fixed_load_demand: Final = ZCLAttributeDef(
            id=0x4510,
            type=t.uint24_t,
            access="rw",
            is_manufacturer_specific=True,
        )


class SETemperatureMeasurement(CustomCluster, TemperatureMeasurement):
    """Schneider Electric Temperature Measurement cluster."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Schneider Electric Temperature Measurement cluster attributes."""

        se_sensor_correction: Final = ZCLAttributeDef(
            id=0xE020,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )


class SETemperatureMeasurementExternal(SETemperatureMeasurement):
    """Schneider Electric Temperature Measurement cluster for external (floor) temperature input."""

    class AttributeDefs(SETemperatureMeasurement.AttributeDefs):
        """Schneider Electric Temperature Measurement cluster attributes."""

        se_temperature_sensor_type: Final = ZCLAttributeDef(
            id=0xE021,
            type=SETemperatureSensorType,
            access="rw",
            is_manufacturer_specific=True,
        )


class SEThermostat(CustomCluster, Thermostat):
    """Schneider Electric manufacturer specific Thermostat cluster."""

    class ClientCommandDefs(Thermostat.ClientCommandDefs):
        """Client command definitions."""

        se_pi_demand_override: Final = ZCLCommandDef(
            id=0xF1,
            schema={
                "type": SEDemandOverrideType,
                "demand": t.uint8_t,
                "duration": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(Thermostat.ServerCommandDefs):
        """Server command definitions."""

        se_local_setpoint_change_notification_command: Final = ZCLCommandDef(
            id=0x91,
            schema={
                "reason": SESetpointChangeReason,
                "system_mode": SystemMode,
                "affected_setpoint": SEAffectedSetpoint,
                "setpoint_value": t.int16s,
                "duration": t.uint16_t,
            },
            is_manufacturer_specific=True,
        )

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        se_open_window_detection_status: Final = ZCLAttributeDef(
            id=0xE012,
            type=t.Bool,
            access="r",
            is_manufacturer_specific=True,
        )
        se_open_window_detection_threshold: Final = ZCLAttributeDef(
            id=0xE013,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_open_window_event_duration: Final = ZCLAttributeDef(
            id=0xE014,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_open_window_detection_guard_period: Final = ZCLAttributeDef(
            id=0xE015,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_fallback_timeout: Final = ZCLAttributeDef(
            id=0xE200,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_boost_amount: Final = ZCLAttributeDef(
            id=0xE210,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_control_status: Final = ZCLAttributeDef(
            id=0xE211,
            type=SEControlStatus,
            access="r",
            is_manufacturer_specific=True,
        )
        se_local_temperature_source_select: Final = ZCLAttributeDef(
            id=0xE212,
            type=SELocalTemperatureSourceSelect,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_control_type: Final = ZCLAttributeDef(
            id=0xE213,
            type=SEControlType,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heat_cool_input_mode: Final = ZCLAttributeDef(
            id=0xE214,
            type=SEHeatCoolInputMode,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_unoccupied_tracking_offset: Final = ZCLAttributeDef(
            id=0xE215,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_thermostat_application: Final = ZCLAttributeDef(
            id=0xE216,
            type=SEThermostatApplication,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heating_fuel: Final = ZCLAttributeDef(
            id=0xE217,
            type=SEHeatingFuel,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heat_transfer_medium: Final = ZCLAttributeDef(
            id=0xE218,
            type=SEHeatTransferMedium,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heating_emitter_type: Final = ZCLAttributeDef(
            id=0xE21A,
            type=SEHeatingEmitterType,
            access="rw",
            is_manufacturer_specific=True,
        )


class SEUserInterface(CustomCluster, UserInterface):
    """Schneider Electric Thermostat User Interface cluster."""

    class AttributeDefs(UserInterface.AttributeDefs):
        """Attribute definitions."""

        se_brightness: Final = ZCLAttributeDef(
            id=0xE000,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_inactive_brightness: Final = ZCLAttributeDef(
            id=0xE001,
            type=t.uint8_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_activity_timeout: Final = ZCLAttributeDef(
            id=0xE002,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )


class SECycleTime(CustomCluster):
    """Schneider Electric Cycle Time cluster."""

    cluster_id = 0xFF16
    name = "SECycleTime"

    class AttributeDefs(CustomCluster.AttributeDefs):
        """Attribute definitions."""

        se_demand_percentage: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        se_cycle_time: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_min_cycle_time: Final = ZCLAttributeDef(
            id=0x0011,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        se_max_cycle_time: Final = ZCLAttributeDef(
            id=0x0012,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        se_status_flags: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.bitmap8,
            access="r",
            is_manufacturer_specific=True,
        )
        se_cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )


class SEHeatingCoolingOutput(CustomCluster):
    """Schneider Electric Heating Cooling Output cluster."""

    cluster_id = 0xFF23
    name = "SEHeatingCoolingOutput"

    class AttributeDefs(CustomCluster.AttributeDefs):
        """Attribute definitions."""

        se_measured_temperature: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.int16s,
            access="r",
            is_manufacturer_specific=True,
        )
        se_abs_min_heat_temperature_limit: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.int16s,
            access="r",
            is_manufacturer_specific=True,
        )
        se_abs_max_heat_temperature_limit: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.int16s,
            access="r",
            is_manufacturer_specific=True,
        )
        se_abs_min_cool_temperature_limit: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.int16s,
            access="r",
            is_manufacturer_specific=True,
        )
        se_abs_max_cool_temperature_limit: Final = ZCLAttributeDef(
            id=0x0006,
            type=t.int16s,
            access="r",
            is_manufacturer_specific=True,
        )
        se_min_heat_temperature_limit: Final = ZCLAttributeDef(
            id=0x0015,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_max_heat_temperature_limit: Final = ZCLAttributeDef(
            id=0x0016,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_min_cool_temperature_limit: Final = ZCLAttributeDef(
            id=0x0017,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_max_cool_temperature_limit: Final = ZCLAttributeDef(
            id=0x0018,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heat_temperature_high_limit: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heat_temperature_low_limit: Final = ZCLAttributeDef(
            id=0x0021,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_cool_temperature_high_limit: Final = ZCLAttributeDef(
            id=0x0022,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_cool_temperature_low_limit: Final = ZCLAttributeDef(
            id=0x0023,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_cooling_output_mode: Final = ZCLAttributeDef(
            id=0x0030,
            type=SECoolingOutputMode,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_heating_output_mode: Final = ZCLAttributeDef(
            id=0x0031,
            type=SEHeatingOutputMode,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_maximum_idle_time: Final = ZCLAttributeDef(
            id=0x0041,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_anti_idle_exercise_time: Final = ZCLAttributeDef(
            id=0x0042,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_preffered_exercise_time: Final = ZCLAttributeDef(
            id=0x0043,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_min_off_time: Final = ZCLAttributeDef(
            id=0x0044,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_min_on_time: Final = ZCLAttributeDef(
            id=0x0045,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_max_overall_duty_cycle: Final = ZCLAttributeDef(
            id=0xE207,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_overall_duty_cycle_period: Final = ZCLAttributeDef(
            id=0xE208,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        se_cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder(SE_MANUF_NAME, "EKO07259")
    .applies_to(SE_MANUF_NAME, "WDE002497")
    .applies_to(SE_MANUF_NAME, "WDE011680")
    .replaces(SEBasic)
    .replaces(SEBasic, endpoint_id=2)
    .replaces(SEBasic, endpoint_id=3)
    .replaces(SEBasic, endpoint_id=5)
    .replaces(SEThermostat)
    .replaces(SEUserInterface)
    .replaces(SETemperatureMeasurement, endpoint_id=2)
    .replaces(SETemperatureMeasurementExternal, endpoint_id=3)
    .replaces(SEMetering, endpoint_id=5)
    .replaces(SECycleTime)
    .replaces(SEHeatingCoolingOutput)
    .number(
        cluster_id=SEMetering.cluster_id,
        endpoint_id=5,
        attribute_name=SEMetering.AttributeDefs.se_fixed_load_demand.name,
        translation_key="fixed_load_demand",
        fallback_name="Fixed load demand",
        device_class=NumberDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        min_value=0,
        max_value=10000,
        step=1,
    )
    .number(
        cluster_id=SEUserInterface.cluster_id,
        endpoint_id=1,
        attribute_name=SEUserInterface.AttributeDefs.se_brightness.name,
        translation_key="display_brightness",
        fallback_name="Display brightness",
        # unit="%",
        min_value=0,
        max_value=100,
        step=1,
    )
    .number(
        cluster_id=SEUserInterface.cluster_id,
        endpoint_id=1,
        attribute_name=SEUserInterface.AttributeDefs.se_inactive_brightness.name,
        translation_key="display_inactive_brightness",
        fallback_name="Display inactive brightness",
        # unit="%",
        min_value=0,
        max_value=100,
        step=1,
    )
    .number(
        cluster_id=SEUserInterface.cluster_id,
        endpoint_id=1,
        attribute_name=SEUserInterface.AttributeDefs.se_activity_timeout.name,
        translation_key="display_activity_timeout",
        fallback_name="Display activity timeout",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=3600,
        step=1,
    )
    .binary_sensor(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_open_window_detection_status.name,
        translation_key="open_window_detection_status",
        fallback_name="Open window detection status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .number(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_open_window_detection_threshold.name,
        translation_key="open_window_detection_threshold",
        fallback_name="Open window detection threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0,
        max_value=12,
        multiplier=0.1,
        step=0.1,
    )
    .number(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_open_window_event_duration.name,
        translation_key="open_window_event_duration",
        fallback_name="Open window event duration",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=7620,
        step=1,
    )
    .number(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_open_window_detection_guard_period.name,
        translation_key="open_window_detection_guard_period",
        fallback_name="Open window detection guard period",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=7620,
        step=1,
    )
    .number(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_fallback_timeout.name,
        translation_key="fallback_timeout",
        fallback_name="Fallback timeout",
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=30,
        max_value=10800,
        step=1,
    )
    .number(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_boost_amount.name,
        translation_key="boost_amount",
        fallback_name="Boost amount",
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0,
        max_value=10,
        multiplier=0.01,
        step=0.5,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_control_status.name,
        translation_key="control_status",
        fallback_name="Control status",
        enum_class=SEControlStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_local_temperature_source_select.name,
        translation_key="local_temperature_source",
        fallback_name="Local temperature source",
        enum_class=SELocalTemperatureSourceSelect,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_control_type.name,
        translation_key="control_type",
        fallback_name="Control type",
        enum_class=SEControlType,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_thermostat_application.name,
        translation_key="thermostat_application",
        fallback_name="Thermostat application",
        enum_class=SEThermostatApplication,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_heating_fuel.name,
        translation_key="heating_fuel",
        fallback_name="Heating fuel",
        enum_class=SEHeatingFuel,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_heat_transfer_medium.name,
        translation_key="heat_transfer_medium",
        fallback_name="Heat transfer medium",
        enum_class=SEHeatTransferMedium,
    )
    .enum(
        cluster_id=SEThermostat.cluster_id,
        endpoint_id=1,
        attribute_name=SEThermostat.AttributeDefs.se_heating_emitter_type.name,
        translation_key="heating_emitter_type",
        fallback_name="Heating emitter type",
        enum_class=SEHeatingEmitterType,
    )
    .number(
        cluster_id=SETemperatureMeasurement.cluster_id,
        endpoint_id=2,
        attribute_name=SETemperatureMeasurement.AttributeDefs.se_sensor_correction.name,
        translation_key="ambient_sensor_correction",
        fallback_name="Ambient sensor correction",
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-10,
        max_value=10,
        step=0.1,
        multiplier=0.01,
    )
    .number(
        cluster_id=SETemperatureMeasurementExternal.cluster_id,
        endpoint_id=3,
        attribute_name=SETemperatureMeasurementExternal.AttributeDefs.se_sensor_correction.name,
        translation_key="external_sensor_correction",
        fallback_name="External sensor correction",
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-10,
        max_value=10,
        step=0.1,
        multiplier=0.01,
    )
    .enum(
        cluster_id=SETemperatureMeasurementExternal.cluster_id,
        endpoint_id=3,
        attribute_name=SETemperatureMeasurementExternal.AttributeDefs.se_temperature_sensor_type.name,
        translation_key="external_temperature_sensor_type",
        fallback_name="External temperature sensor type",
        enum_class=SETemperatureSensorType,
    )
    .add_to_registry()
)
