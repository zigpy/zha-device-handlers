"""Module to handle quirks of the Sinopé Technologies water leak sensor and level monitor.

It add manufacturer attributes for IasZone cluster for the water leak alarm.
Supported devices are WL4200, WL4200S and LM4110-ZB
"""

from typing import Final

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    EntityType,
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import (
    DEGREE,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Identify,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import (
    ZCL_CLUSTER_REVISION_ATTR,
    BaseAttributeDefs,
    ZCLAttributeDef,
)

from zhaquirks.sinope import SINOPE, SINOPE_MANUFACTURER_CLUSTER_ID
from zhaquirks.sinope.switch import EnergySource, SinopeTechnologiesBasicCluster


class ManufacturerReportingMixin:
    """Mixin to configure the attributes reporting in manufacturer cluster."""

    MANUFACTURER_REPORTING = {
        # attribut_id: (min_interval, max_interval, reportable_change)
        0x0034: (10, 0, 1),  # device_status
        0x0200: (10, 0, 1),  # status
        # ... add other attributes
    }

    async def configure_reporting_all(self):
        """Configure reporting of all configured attributes."""
        for attr_id, (min_i, max_i, change) in self.MANUFACTURER_REPORTING.items():
            try:
                await self.configure_reporting(
                    attribute=attr_id,
                    min_interval=min_i,
                    max_interval=max_i,
                    reportable_change=change,
                )
                self.debug(f"Reporting configured for attr {hex(attr_id)}")
            except Exception as e:
                self.debug(f"Reporting configuration fail for attr {hex(attr_id)}: {e}")


class LeakStatus(t.enum8):
    """Leak_status values."""

    Dry = 0x00
    Leak = 0x01


class DeviceStatus(t.bitmap32):
    """Device general status."""

    Ok = 0x00000000
    Temp_sensor = 0x00000020


class ZoneStatus(t.uint16_t):
    """IAS zone status."""

    Ok = 0x0030
    Connector_1 = 0x0031
    Connector_2 = 0x0032
    Low_battery = 0x0038
    Connector_low_bat = 0x003A


class SensorStatus(t.uint16_t):
    """Sensor probe state."""

    Disconnected = 0x0021
    Ok = 0x004E
    Min_temp_alert = 0x004F
    Max_temp_alert = 0x0051


class BatteryStatus(t.bitmap32):
    """Battery status."""

    Ok = 0x00000000
    Low = 0x00000001


class SinopeManufacturerCluster(ManufacturerReportingMixin, CustomCluster):
    """SinopeManufacturerCluster manufacturer cluster."""

    DeviceStatus: Final = DeviceStatus
    SensorStatus: Final = SensorStatus

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        firmware_number: Final = ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        firmware_version: Final = ZCLAttributeDef(
            id=0x0004, type=t.CharacterString, access="r", is_manufacturer_specific=True
        )
        min_temperature_limit: Final = ZCLAttributeDef(
            id=0x0032, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        max_temperature_limit: Final = ZCLAttributeDef(
            id=0x0033, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        device_status: Final = ZCLAttributeDef(
            id=0x0034, type=t.bitmap8, access="rp", is_manufacturer_specific=True
        )
        sensor_status: Final = ZCLAttributeDef(
            id=0x0035, type=SensorStatus, access="r", is_manufacturer_specific=True
        )
        battery_type: Final = ZCLAttributeDef(
            id=0x0036, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        status: Final = ZCLAttributeDef(
            id=0x0200, type=DeviceStatus, access="rp", is_manufacturer_specific=True
        )
        cluster_revision: Final = ZCL_CLUSTER_REVISION_ATTR

    async def bind(self):
        """Bind the cluster and configure reporting."""
        await super().bind()
        await self.configure_reporting_all()


class SinopeTechnologiesIasZoneCluster(CustomCluster, IasZone):
    """SinopeTechnologiesIasZoneCluster custom cluster."""

    LeakStatus: Final = LeakStatus
    ZoneStatus: Final = ZoneStatus

    class AttributeDefs(IasZone.AttributeDefs):
        """Sinope Manufacturer IasZone Cluster Attributes."""

        zone_status: Final = ZCLAttributeDef(
            id=0x0002, type=ZoneStatus, access="p", is_manufacturer_specific=True
        )
        leak_status: Final = ZCLAttributeDef(
            id=0x0030, type=LeakStatus, access="rw", is_manufacturer_specific=True
        )


class SinopeTechnologiesPowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """SinopeTechnologiesPowerConfigurationCluster custom cluster."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.battery_voltage.id:
            value = value / 10
        super()._update_attribute(attrid, value)

    BatteryStatus: Final = BatteryStatus

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """Sinope Manufacturer ias Cluster Attributes."""

        battery_alarm_state: Final = ZCLAttributeDef(
            id=0x003E, type=BatteryStatus, access="rp", is_manufacturer_specific=True
        )


(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
    # device_version=0 input_clusters=[0, 1, 3, 1026, 1280, 2821, 65281]
    # output_clusters=[3, 25]>
    # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
    # device_version=0 input_clusters=[0, 1, 3, 20, 1026, 1280, 2821, 65281]
    # output_clusters=[3, 25]>
    QuirkBuilder(SINOPE, "WL4200")
    .applies_to(SINOPE, "WL4200S")
    .replaces(SinopeTechnologiesIasZoneCluster)
    .replaces(SinopeManufacturerCluster)
    .enum(  # Power source
        attribute_name=SinopeTechnologiesBasicCluster.AttributeDefs.power_source.name,
        cluster_id=SinopeTechnologiesBasicCluster.cluster_id,
        enum_class=EnergySource,
        translation_key="power_source",
        fallback_name="Power source",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .number(  # Checkin interval
        attribute_name=PollControl.AttributeDefs.checkin_interval.name,
        cluster_id=PollControl.cluster_id,
        step=60,
        min_value=3600,
        max_value=21600,
        unit=UnitOfTime.SECONDS,
        translation_key="checkin_interval",
        fallback_name="Checkin interval",
    )
    .number(  # Min temperature limit
        attribute_name=SinopeManufacturerCluster.AttributeDefs.min_temperature_limit.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=1,
        min_value=300,
        max_value=1500,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="min_temperature_limit",
        fallback_name="Min temperature limit",
    )
    .number(  # Max temperature limit
        attribute_name=SinopeManufacturerCluster.AttributeDefs.max_temperature_limit.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        step=1,
        min_value=1500,
        max_value=5000,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_temperature_limit",
        fallback_name="Max temperature limit",
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
    .sensor(  # Zone status
        attribute_name=SinopeTechnologiesIasZoneCluster.AttributeDefs.zone_status.name,
        cluster_id=SinopeTechnologiesIasZoneCluster.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="zone_status",
        fallback_name="Zone status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Sensor status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.sensor_status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="sensor_status",
        fallback_name="Sensor status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=0
    # device_version=0 input_clusters=[0, 1, 3, 12, 32, 1026, 2821, 65281]
    # output_clusters=[25]>
    QuirkBuilder(SINOPE, "LM4110-ZB")
    .replaces_endpoint(1, device_type=zha_p.DeviceType.METER_INTERFACE)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .adds(AnalogInput, endpoint_id=1)
    .adds(PollControl, endpoint_id=1)
    .adds(TemperatureMeasurement, endpoint_id=1)
    .adds(Diagnostic, endpoint_id=1)
    .replaces(SinopeTechnologiesPowerConfigurationCluster)
    .replaces(SinopeManufacturerCluster)
    .sensor(  # Battery status
        attribute_name=SinopeTechnologiesPowerConfigurationCluster.AttributeDefs.battery_alarm_state.name,
        cluster_id=SinopeTechnologiesPowerConfigurationCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="battery_alarm_state",
        fallback_name="Battery alarm",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Battery voltage
        attribute_name=SinopeTechnologiesPowerConfigurationCluster.AttributeDefs.battery_voltage.name,
        cluster_id=SinopeTechnologiesPowerConfigurationCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=43200, reportable_change=1
        ),
        translation_key="battery_voltage",
        fallback_name="Battery voltage",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Gauge angle
        attribute_name=AnalogInput.AttributeDefs.present_value.name,
        cluster_id=AnalogInput.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        attribute_converter=lambda x: None if x == -2 else x,
        unit=DEGREE,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        reporting_config=ReportingConfig(
            min_interval=5, max_interval=3600, reportable_change=1
        ),
        translation_key="gauge_angle",
        fallback_name="Gauge angle",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=SinopeManufacturerCluster.AttributeDefs.status.name,
        cluster_id=SinopeManufacturerCluster.cluster_id,
        endpoint_id=1,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .number(  # Checkin interval
        attribute_name=PollControl.AttributeDefs.checkin_interval.name,
        cluster_id=PollControl.cluster_id,
        step=60,
        min_value=3600,
        max_value=21600,
        unit=UnitOfTime.SECONDS,
        translation_key="checkin_interval",
        fallback_name="Checkin interval",
    )
    .add_to_registry()
)
