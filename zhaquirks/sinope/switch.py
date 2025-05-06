"""Module to handle quirks of the Sinopé Technologies switches.

Supported devices, SP2600ZB, SP2610ZB, RM3250ZB, RM3500ZB,
VA4200WZ, VA4201WZ, VA4200ZB, VA4201ZB, VA4220ZB, VA4221ZB and MC3100ZB,
2nd gen VA4220ZB, VA4221ZB with flow meeter FS4220, FS4221.
"""

from typing import Final

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.measurement import (
    FlowMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import (
    ZCL_CLUSTER_REVISION_ATTR,
    BaseAttributeDefs,
    ZCLAttributeDef,
)

from zhaquirks.sinope import (
    SINOPE,
    SINOPE_MANUFACTURER_CLUSTER_ID,
    CustomDeviceTemperatureCluster,
)


class KeypadLock(t.enum8):
    """Keypad_lockout values."""

    Unlocked = 0x00
    Locked = 0x01
    Partial_lock = 0x02


class FlowAlarm(t.enum8):
    """Abnormal flow alarm."""

    Off = 0x00
    On = 0x01


class AlarmAction(t.enum8):
    """Flow alarm action."""

    Nothing = 0x00
    Notify = 0x01
    Close = 0x02
    Close_notify = 0x03
    No_flow = 0x04


class PowerSource(t.uint32_t):
    """Valve power source types."""

    Battery = 0x00000000
    ACUPS_01 = 0x00000001
    DC_power = 0x0001D4C0


class EmergencyPower(t.uint32_t):
    """Valve emergency power source types."""

    Battery = 0x00000000
    ACUPS_01 = 0x00000001
    Battery_ACUPS_01 = 0x0000003C


class AbnormalAction(t.bitmap16):
    """Action in case of abnormal flow detected."""

    Nothing = 0x0000
    Close_valve = 0x0001
    Close_notify = 0x0003


class ColdStatus(t.enum8):
    """Cold_load_pickup_status values."""

    Active = 0x00
    Off = 0x01


class FlowDuration(t.uint32_t):
    """Abnormal flow duration."""

    M_15 = 0x00000384
    M_30 = 0x00000708
    M_45 = 0x00000A8C
    M_60 = 0x00000E10
    M_75 = 0x00001194
    M_90 = 0x00001518
    H_3 = 0x00002A30
    H_6 = 0x00005460
    H_12 = 0x0000A8C0
    H_24 = 0x00015180


class InputDelay(t.uint16_t):
    """Delay for on/off input."""

    Off = 0x0000
    M_1 = 0x003C
    M_2 = 0x0078
    M_5 = 0x012C
    M_10 = 0x0258
    M_15 = 0x0384
    M_30 = 0x0708
    H_1 = 0x0E10
    H_2 = 0x1C20
    H_3 = 0x2A30


class EnergySource(t.enum8):
    """Power source."""

    Unknown = 0x0000
    DC_mains = 0x0001
    Battery = 0x0003
    DC_source = 0x0004
    ACUPS_01 = 0x0081
    ACUPS01 = 0x0082


class ValveStatus(t.bitmap8):
    """Valve_status."""

    Off = 0x00
    Off_armed = 0x01
    On = 0x02


class DeviceStatus(t.bitmap32):
    """Device general status."""

    Ok = 0x00000000
    Leak_cable = 0x00000040
    Temp_cable = 0x00000020


class ZoneStatus(t.uint16_t):
    """IAS zone status."""

    Ok = 0x0030
    Connector_1 = 0x0031
    Connector_2 = 0x0032
    Low_battery = 0x0038
    Connector_low_bat = 0x003A


class FlowMeter(t.LVList):
    """Flow meter configuration values."""

    No_flow_meter = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    FS4220 = [194, 17, 0, 0, 136, 119, 0, 0, 1, 0, 0, 0]
    FS4221 = [159, 38, 0, 0, 76, 85, 1, 0, 1, 0, 0, 0]
    FS4222 = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]


class UnitOfMeasure(t.enum8):
    """Unit_of_measure."""

    KWh = 0x00
    Lh = 0x07


class SinopeManufacturerCluster(CustomCluster):
    """SinopeManufacturerCluster manufacturer cluster."""

    KeypadLock: Final = KeypadLock
    FlowAlarm: Final = FlowAlarm
    AlarmAction: Final = AlarmAction
    PowerSource: Final = PowerSource
    EmergencyPower: Final = EmergencyPower
    AbnormalAction: Final = AbnormalAction
    ColdStatus: Final = ColdStatus
    FlowDuration: Final = FlowDuration
    FlowMeter: Final = FlowMeter
    InputDelay: Final = InputDelay
    DeviceStatus: Final = DeviceStatus

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        keypad_lockout: Final = ZCLAttributeDef(
            id=0x0002, type=KeypadLock, access="rw", is_manufacturer_specific=True
        )
        firmware_number: Final = ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        firmware_version: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.CharacterString,
            access="r",
            is_manufacturer_specific=True,
        )
        outdoor_temp: Final = ZCLAttributeDef(
            id=0x0010, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        unknown_attr_2: Final = ZCLAttributeDef(
            id=0x0013, type=t.enum8, access="rw", is_manufacturer_specific=True
        )
        connected_load: Final = ZCLAttributeDef(
            id=0x0060, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        current_load: Final = ZCLAttributeDef(
            id=0x0070, type=t.bitmap8, access="r", is_manufacturer_specific=True
        )
        dr_config_water_temp_min: Final = ZCLAttributeDef(
            id=0x0076, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        dr_config_water_temp_time: Final = ZCLAttributeDef(
            id=0x0077, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        dr_wt_time_on: Final = ZCLAttributeDef(
            id=0x0078, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        min_measured_temp: Final = ZCLAttributeDef(
            id=0x007C, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        max_measured_temp: Final = ZCLAttributeDef(
            id=0x007D, type=t.int16s, access="rp", is_manufacturer_specific=True
        )
        water_temp_protection_type: Final = ZCLAttributeDef(
            id=0x007E, type=t.enum8, access="rwp", is_manufacturer_specific=True
        )
        current_summation_delivered: Final = ZCLAttributeDef(
            id=0x0090, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        timer: Final = ZCLAttributeDef(
            id=0x00A0, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        timer_countdown: Final = ZCLAttributeDef(
            id=0x00A1, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        status: Final = ZCLAttributeDef(
            id=0x0200, type=DeviceStatus, access="rp", is_manufacturer_specific=True
        )
        alarm_flow_threshold: Final = ZCLAttributeDef(
            id=0x0230, type=FlowAlarm, access="rw", is_manufacturer_specific=True
        )
        alarm_options: Final = ZCLAttributeDef(
            id=0x0231, type=AlarmAction, access="r", is_manufacturer_specific=True
        )
        flow_meter_config: Final = ZCLAttributeDef(
            id=0x0240, type=FlowMeter, access="rw", is_manufacturer_specific=True
        )
        valve_countdown: Final = ZCLAttributeDef(
            id=0x0241, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )
        power_source: Final = ZCLAttributeDef(
            id=0x0250, type=PowerSource, access="rw", is_manufacturer_specific=True
        )
        emergency_power_source: Final = ZCLAttributeDef(
            id=0x0251, type=EmergencyPower, access="rw", is_manufacturer_specific=True
        )
        abnormal_flow_duration: Final = ZCLAttributeDef(
            id=0x0252, type=FlowDuration, access="rw", is_manufacturer_specific=True
        )
        abnormal_flow_action: Final = ZCLAttributeDef(
            id=0x0253, type=AbnormalAction, access="rw", is_manufacturer_specific=True
        )
        max_measured_value: Final = ZCLAttributeDef(
            id=0x0280, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        cold_load_pickup_status: Final = ZCLAttributeDef(
            id=0x0283, type=ColdStatus, access="r", is_manufacturer_specific=True
        )
        cold_load_pickup_remaining_time: Final = ZCLAttributeDef(
            id=0x0284, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        input_on_delay: Final = ZCLAttributeDef(
            id=0x02A0, type=InputDelay, access="rw", is_manufacturer_specific=True
        )
        input_off_delay: Final = ZCLAttributeDef(
            id=0x02A1, type=InputDelay, access="rw", is_manufacturer_specific=True
        )
        cluster_revision: Final = ZCL_CLUSTER_REVISION_ATTR


class SinopeTechnologiesBasicCluster(CustomCluster, Basic):
    """SinopetechnologiesBasicCluster custom cluster."""

    EnergySource: Final = EnergySource

    class AttributeDefs(Basic.AttributeDefs):
        """Sinope Manufacturer Basic Cluster Attributes."""

        power_source: Final = ZCLAttributeDef(
            id=0x0007, type=EnergySource, access="r", is_manufacturer_specific=True
        )


class SinopeTechnologiesIasZoneCluster(CustomCluster, IasZone):
    """SinopeTechnologiesIasZoneCluster custom cluster."""

    ZoneStatus: Final = ZoneStatus

    class AttributeDefs(IasZone.AttributeDefs):
        """Sinope Manufacturer ias Cluster Attributes."""

        zone_status: Final = ZCLAttributeDef(
            id=0x0002, type=ZoneStatus, access="p", is_manufacturer_specific=True
        )


class SinopeTechnologiesMeteringCluster(CustomCluster, Metering):
    """SinopeTechnologiesMeteringCluster custom cluster."""

    ValveStatus: Final = ValveStatus
    UnitOfMeasure: Final = UnitOfMeasure

    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {DIVISOR: 1000}

    class AttributeDefs(Metering.AttributeDefs):
        """Sinope Manufacturer Metering Cluster Attributes."""

        status: Final = ZCLAttributeDef(
            id=0x0200, type=ValveStatus, access="r", is_manufacturer_specific=True
        )
        unit_of_measure: Final = ZCLAttributeDef(
            id=0x0300, type=UnitOfMeasure, access="r", is_manufacturer_specific=True
        )


class SinopeTechnologiesFlowMeasurementCluster(CustomCluster, FlowMeasurement):
    """Custom flow measurement cluster that divides value by 10."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            value = value / 10
        super()._update_attribute(attrid, value)


(
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=81, device_version=0,
    # input_clusters=[0, 3, 6, 1794, 2820, 65281]
    # output_clusters=[25]>
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=81, device_version=0,
    # input_clusters=[0, 3, 6, 1794, 2820, 4096, 65281]
    # output_clusters=[25, 4096]>
    QuirkBuilder(SINOPE, "SP2600ZB")
    .applies_to(SINOPE, "SP2610ZB")
    .replaces(SinopeTechnologiesMeteringCluster)
    .replaces(SinopeManufacturerCluster)
    .sensor(  # Current summ delivered
        attribute_name=SinopeTechnologiesMeteringCluster.AttributeDefs.current_summ_delivered.name,
        cluster_id=SinopeTechnologiesMeteringCluster.cluster_id,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        reporting_config=ReportingConfig(
            min_interval=59, max_interval=1799, reportable_change=60
        ),
        translation_key="current_summ_delivered",
        fallback_name="Current summ delivered",
        entity_type=EntityType.STANDARD,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=2, device_version=0,
    # input_clusters=[0, 3, 4, 5, 6, 1794, 2820, 2821, 65281]
    # output_clusters=[3, 4, 25]>
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=2, device_version=0,
    # input_clusters=[0, 2, 3, 4, 5, 6, 1794, 2820, 2821, 65281]
    # output_clusters=[3, 4, 25]>
    QuirkBuilder(SINOPE, "RM3250ZB")
    .replaces(CustomDeviceTemperatureCluster)
    .replaces(SinopeManufacturerCluster)
    .enum(  # Keypad lock
        attribute_name=SinopeManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .number(  # Timer
        attribute_name=SinopeManufacturerCluster.AttributeDefs.timer.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="timer",
        fallback_name="Timer",
    )
    .sensor(  # Timer countdown
        attribute_name=SinopeManufacturerCluster.AttributeDefs.timer_countdown.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="timer_countdown",
        fallback_name="Timer countdown",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device temperature
        attribute_name=CustomDeviceTemperatureCluster.AttributeDefs.current_temperature.name,
        cluster_id=CustomDeviceTemperatureCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        reporting_config=ReportingConfig(
            min_interval=59, max_interval=1799, reportable_change=60
        ),
        translation_key="current_temperature",
        fallback_name="Current temperature",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=3, device_version=0,
    # input_clusters=[0, 1, 3, 4, 5, 6, 8, 2821, 65281]
    # output_clusters=[3, 25]>
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=3, device_version=0,
    # input_clusters=[0, 1, 3, 4, 5, 6, 8, 1026, 1280, 1794, 2821, 65281]
    # output_clusters=[3, 6, 25]>
    QuirkBuilder(SINOPE, "VA4200WZ")
    .applies_to(SINOPE, "VA4201WZ")
    .applies_to(SINOPE, "VA4200ZB")
    .applies_to(SINOPE, "VA4201ZB")
    .applies_to(SINOPE, "VA4220ZB")
    .applies_to(SINOPE, "VA4221ZB")
    .replaces(SinopeTechnologiesBasicCluster)
    .replaces(SinopeTechnologiesIasZoneCluster)
    .replaces(SinopeTechnologiesFlowMeasurementCluster)
    .replaces(SinopeTechnologiesMeteringCluster)
    .replaces(SinopeManufacturerCluster)
    .enum(  # energy source
        attribute_name=SinopeTechnologiesBasicCluster.AttributeDefs.power_source.name,
        cluster_id=SinopeTechnologiesBasicCluster.cluster_id,
        enum_class=EnergySource,
        translation_key="power_source",
        fallback_name="Power source",
        entity_type=EntityType.CONFIG,
    )
    .enum(  # Alarm action status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.alarm_options.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        enum_class=AlarmAction,
        translation_key="alarm_options",
        fallback_name="Alarm options",
        entity_type=EntityType.CONFIG,
    )
    .enum(  # Flow alarm
        attribute_name=SinopeManufacturerCluster.AttributeDefs.alarm_flow_threshold.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        enum_class=FlowAlarm,
        translation_key="alarm_flow",
        fallback_name="Alarm flow",
        entity_type=EntityType.CONFIG,
    )
    .enum(  # Abnormal Flow action
        attribute_name=SinopeManufacturerCluster.AttributeDefs.abnormal_flow_action.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        enum_class=AbnormalAction,
        translation_key="abnormal_flow_action",
        fallback_name="Abnormal flow action",
        entity_type=EntityType.CONFIG,
    )
    .sensor(  # Device temperature
        attribute_name=CustomDeviceTemperatureCluster.AttributeDefs.current_temperature.name,
        cluster_id=CustomDeviceTemperatureCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        reporting_config=ReportingConfig(
            min_interval=59, max_interval=1799, reportable_change=60
        ),
        translation_key="current_temperature",
        fallback_name="Current temperature",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # battery percent
        attribute_name=PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        cluster_id=PowerConfiguration.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=43200, reportable_change=1
        ),
        translation_key="battery_percentage_remaining",
        fallback_name="Battery percentage remaining",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # battery voltage
        attribute_name=PowerConfiguration.AttributeDefs.battery_voltage.name,
        cluster_id=PowerConfiguration.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=43200, reportable_change=1
        ),
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Flow rate
        attribute_name=SinopeTechnologiesMeteringCluster.AttributeDefs.instantaneous_demand.name,
        cluster_id=SinopeTechnologiesMeteringCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=600, reportable_change=1
        ),
        translation_key="instantaneous_demand",
        fallback_name="Instantaneous demand",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .number(  # Emergency_power_source
        attribute_name=SinopeManufacturerCluster.AttributeDefs.emergency_power_source.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=60,
        unit=UnitOfTime.SECONDS,
        translation_key="emergency_power_source",
        fallback_name="Emergency power source",
    )
    .number(  # Abnormal Flow Duration
        attribute_name=SinopeManufacturerCluster.AttributeDefs.abnormal_flow_duration.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=10,
        min_value=900,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="abnormal_flow_duration",
        fallback_name="Abnormal flow duration",
    )
    .number(  # Valve closing countdown
        attribute_name=SinopeManufacturerCluster.AttributeDefs.valve_countdown.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=10,
        min_value=300,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="valve_countdown",
        fallback_name="Valve countdown",
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=2, device_version=0,
    # input_clusters=[0, 1, 3, 4, 5, 6, 15, 1026, 1029, 2821, 65281]
    # output_clusters=[25]>
    # <SimpleDescriptor(endpoint=2, profile=260,
    # device_type=2, device_version=0,
    # input_clusters=[4, 5, 6, 15, 1026, 65281]
    # output_clusters=[25]>
    QuirkBuilder(SINOPE, "MC3100ZB")
    .adds_endpoint(1, device_type=zha_p.DeviceType.ON_OFF_OUTPUT)
    .adds_endpoint(2, device_type=zha_p.DeviceType.ON_OFF_OUTPUT)
    .replaces(SinopeManufacturerCluster, endpoint_id=1)
    .replaces(SinopeManufacturerCluster, endpoint_id=2)
    .number(  # Timer 1
        attribute_name=SinopeManufacturerCluster.AttributeDefs.timer.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        endpoint_id=1,
        step=1,
        min_value=0,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="timer",
        fallback_name="Timer",
    )
    .number(  # Timer 2
        attribute_name=SinopeManufacturerCluster.AttributeDefs.timer.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        endpoint_id=2,
        step=1,
        min_value=0,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="timer_2",
        fallback_name="Timer 2",
    )
    .sensor(  # battery percent
        attribute_name=PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        cluster_id=PowerConfiguration.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=43200, reportable_change=1
        ),
        translation_key="battery_percentage_remaining",
        fallback_name="Battery percentage remaining",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # battery voltage
        attribute_name=PowerConfiguration.AttributeDefs.battery_voltage.name,
        cluster_id=PowerConfiguration.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=43200, reportable_change=1
        ),
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # external probe temperature
        attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        endpoint_id=2,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=3678, reportable_change=1
        ),
        translation_key="external_temperature",
        fallback_name="External temperature",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # device temperature
        attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=3678, reportable_change=1
        ),
        translation_key="device_temperature",
        fallback_name="Device temperature",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Humidity
        attribute_name=RelativeHumidity.AttributeDefs.measured_value.name,
        cluster_id=RelativeHumidity.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=3678, reportable_change=1
        ),
        translation_key="humidity",
        fallback_name="Humidity",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .switch(  # 2nd on_off switch
        attribute_name=OnOff.AttributeDefs.on_off.name,
        cluster_id=OnOff.cluster_id,
        endpoint_id=2,
        translation_key="on_off_2",
        fallback_name="On Off 2",
        entity_type=EntityType.STANDARD,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor(endpoint=1, profile=260,
    # device_type=260, device_version=0,
    # input_clusters=[0, 2, 3, 4, 5, 6, 1026, 1280, 1794, 2820, 2821, 65281]
    # output_clusters=[10, 25]>
    QuirkBuilder(SINOPE, "RM3500ZB")
    .replaces_endpoint(1, device_type=zha_p.DeviceType.ON_OFF_OUTPUT)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .adds(Groups, endpoint_id=1)
    .adds(Scenes, endpoint_id=1)
    .adds(OnOff, endpoint_id=1)
    .adds(TemperatureMeasurement, endpoint_id=1)
    .adds(Metering, endpoint_id=1)
    .adds(ElectricalMeasurement, endpoint_id=1)
    .adds(Diagnostic, endpoint_id=1)
    .replaces(CustomDeviceTemperatureCluster)
    .replaces(SinopeTechnologiesIasZoneCluster)
    .replaces(SinopeManufacturerCluster)
    .binary_sensor(  # leak status
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=600, reportable_change=1
        ),
        translation_key="leak_status",
        fallback_name="Leak status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .binary_sensor(  # Cold load status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.cold_load_pickup_status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        endpoint_id=1,
        device_class=BinarySensorDeviceClass.TAMPER,
        translation_key="cold_load_pickup_status",
        fallback_name="Cold load pickup status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .enum(  # Keypad lock
        attribute_name=SinopeManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.CONFIG,
    )
    .number(  # water temp min limit
        attribute_name=SinopeManufacturerCluster.AttributeDefs.dr_config_water_temp_min.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=60,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="water_temp_min",
        fallback_name="Water temp min",
    )
    .sensor(  # water temperature
        attribute_name=TemperatureMeasurement.AttributeDefs.measured_value.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=580, reportable_change=100
        ),
        translation_key="water_temperature",
        fallback_name="Water temperature",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)
