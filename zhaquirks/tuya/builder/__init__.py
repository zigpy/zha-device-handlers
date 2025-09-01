"""Tuya QuirkBuilder."""

from collections.abc import Callable
from enum import Enum
import inspect
import math
import pathlib
from types import FrameType
from typing import Any, Self

from zigpy.quirks import _DEVICE_REGISTRY
from zigpy.quirks.registry import DeviceRegistry
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder, QuirksV2RegistryEntry
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import (
    PM25,
    CarbonDioxideConcentration,
    ElectricalConductivity,
    FormaldehydeConcentration,
    IlluminanceMeasurement,
    RelativeHumidity,
    SoilMoisture,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import BatterySize
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TUYA_SET_DATA,
    BaseEnchantedDevice,
    PowerConfiguration,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster,
)
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster, TuyaOnOffNM

MOL_VOL_AIR_NTP = 0.2445  # molar volume of air at NTP in cL/mol


BATTERY_VOLTAGES = {
    BatterySize.No_battery: None,
    BatterySize.Built_in: None,
    BatterySize.Other: None,
    BatterySize.AA: 15,
    BatterySize.AAA: 15,
    BatterySize.C: 15,
    BatterySize.D: 15,
    BatterySize.AA: 15,
    BatterySize.CR2: 30,
    BatterySize.CR123A: 30,
    BatterySize.CR2450: 30,
    BatterySize.CR2032: 30,
    BatterySize.CR1632: 30,
    BatterySize.Unknown: None,
}


class TuyaCO2Concentration(CarbonDioxideConcentration, TuyaLocalCluster):
    """Tuya Carbon Dioxide concentration measurement."""


class TuyaElectricalConductivity(ElectricalConductivity, TuyaLocalCluster):
    """Tuya Electrical Conductivity measurement."""


class TuyaFormaldehydeConcentration(FormaldehydeConcentration, TuyaLocalCluster):
    """Tuya Formaldehyde concentration measurement."""

    MOLECULAR_MASS = 30.026


class TuyaIasContact(IasZone, TuyaLocalCluster):
    """Tuya local IAS contact cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Contact_Switch
    }


class TuyaIasFire(IasZone, TuyaLocalCluster):
    """Tuya local IAS smoke/fire cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Fire_Sensor
    }


class TuyaIasVibration(IasZone, TuyaLocalCluster):
    """Tuya local IAS vibration cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Vibration_Movement_Sensor
    }


class TuyaPM25Concentration(PM25, TuyaLocalCluster):
    """Tuya PM25 concentration measurement."""


class TuyaIasGas(IasZone, TuyaLocalCluster):
    """Tuya local IAS gas cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Carbon_Monoxide_Sensor
    }


class TuyaRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster."""


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""


class TuyaSoilMoisture(SoilMoisture, TuyaLocalCluster):
    """Tuya local SoilMoisture cluster with a device RH_MULTIPLIER factor if required."""


class TuyaValveWaterConsumed(Metering, TuyaLocalCluster):
    """Tuya Valve Water consumed cluster."""

    VOLUME_LITERS = 0x0007
    WATER_METERING = 0x02

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.unit_of_measure.id: VOLUME_LITERS,
        Metering.AttributeDefs.metering_device_type.id: WATER_METERING,
    }


class TuyaValveWaterConsumedNoInstDemand(TuyaValveWaterConsumed):
    """Tuya Valve Water consumed cluster without instantaneous demand."""

    def __init__(self, *args, **kwargs):
        """Init a TuyaValveWaterConsumedNoInstDemand cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(Metering.AttributeDefs.instantaneous_demand.id)


class TuyaAirQualityVOC(TuyaLocalCluster):
    """Tuya VOC level cluster."""

    cluster_id = 0x042E
    name = "VOC Level"
    ep_attribute = "voc_level"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute Definitions."""

        measured_value = ZCLAttributeDef(
            id=0x0000,
            type=t.Single,
            access="rp",
            is_manufacturer_specific=True,
        )
        min_measured_value = ZCLAttributeDef(
            id=0x0001,
            type=t.Single,
            access="rp",
            is_manufacturer_specific=True,
        )
        max_measured_value = ZCLAttributeDef(
            id=0x0002,
            type=t.Single,
            access="rp",
            is_manufacturer_specific=True,
        )
        tolerance = ZCLAttributeDef(
            id=0x0003,
            type=t.Single,
            access="rp",
            is_manufacturer_specific=True,
        )


class TuyaIlluminance(IlluminanceMeasurement, TuyaLocalCluster):
    """Tuya local illuminance cluster."""

    _CONSTANT_ATTRIBUTES = {
        IlluminanceMeasurement.AttributeDefs.light_sensor_type.id: IlluminanceMeasurement.LightSensorType.Photodiode
    }


class TuyaQuirkBuilder(QuirkBuilder):
    """Tuya QuirkBuilder."""

    def __init__(
        self,
        manufacturer: str | None = None,
        model: str | None = None,
        registry: DeviceRegistry = _DEVICE_REGISTRY,
    ) -> None:
        """Init the TuyaQuirkBuilder."""
        self.tuya_data_point_handlers: dict[int, str] = {}
        self.tuya_dp_to_attribute: dict[int, list[DPToAttributeMapping]] = {}
        self.new_attributes: set[foundation.ZCLAttributeDef] = set()
        super().__init__(manufacturer, model, registry)
        # quirk_file will point to the init call above if called from this QuirkBuilder,
        # so we need to re-set it correctly
        current_frame: FrameType = inspect.currentframe()
        caller: FrameType = current_frame.f_back
        self.quirk_file = pathlib.Path(caller.f_code.co_filename)
        self.quirk_file_line = caller.f_lineno

    def _tuya_battery(
        self,
        dp_id: int,
        power_cfg: PowerConfiguration,
        scale: float,
    ) -> Self:
        """Add a Tuya Battery Power Configuration."""
        self.tuya_dp(
            dp_id,
            power_cfg.ep_attribute,
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
            converter=lambda x: x * scale,
        )
        self.adds(power_cfg)
        return self

    def tuya_battery(
        self,
        dp_id: int,
        power_cfg: PowerConfiguration | None = None,
        battery_type: BatterySize | None = BatterySize.AA,
        battery_qty: int | None = 2,
        battery_voltage: int | None = None,
        scale: float = 2,
    ) -> Self:
        """Add a Tuya Battery Power Configuration."""

        if power_cfg:
            return self._tuya_battery(dp_id=dp_id, power_cfg=power_cfg, scale=scale)

        if not battery_voltage and (battery_type and battery_qty):
            battery_voltage = BATTERY_VOLTAGES.get(battery_type)

        class TuyaPowerConfigurationClusterBattery(TuyaPowerConfigurationCluster):
            """PowerConfiguration cluster for Tuya devices."""

            _CONSTANT_ATTRIBUTES = {
                PowerConfiguration.AttributeDefs.battery_size.id: battery_type,
                PowerConfiguration.AttributeDefs.battery_rated_voltage.id: battery_voltage,
                PowerConfiguration.AttributeDefs.battery_quantity.id: battery_qty,
            }

        return self._tuya_battery(
            dp_id=dp_id, power_cfg=TuyaPowerConfigurationClusterBattery, scale=scale
        )

    def tuya_illuminance(
        self,
        dp_id: int,
        illuminance_cfg: TuyaLocalCluster = TuyaIlluminance,
        converter: Callable[[Any], Any] | None = (
            lambda x: 10000 * math.log10(x) + 1 if x != 0 else 0
        ),
    ) -> Self:
        """Add a Tuya Illuminance Configuration."""
        self.tuya_dp(
            dp_id,
            illuminance_cfg.ep_attribute,
            IlluminanceMeasurement.AttributeDefs.measured_value.name,
            converter=converter,
        )
        self.adds(illuminance_cfg)
        return self

    def tuya_contact(self, dp_id: int) -> Self:
        """Add a Tuya IAS contact sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasContact,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x != 0 else 0,
        )
        return self

    def tuya_co2(
        self,
        dp_id: int,
        co2_cfg: TuyaLocalCluster = TuyaCO2Concentration,
        scale: float = 1e-6,
    ) -> Self:
        """Add a Tuya CO2 Configuration."""
        self.tuya_dp(
            dp_id,
            co2_cfg.ep_attribute,
            CarbonDioxideConcentration.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
        )
        self.adds(co2_cfg)
        return self

    def tuya_electrical_conductivity(
        self,
        dp_id: int,
        ec_cfg: TuyaLocalCluster = TuyaElectricalConductivity,
        scale: float = 1,
    ) -> Self:
        """Add a Tuya Electrical Conductivity Configuration."""
        self.tuya_dp(
            dp_id,
            ec_cfg.ep_attribute,
            ElectricalConductivity.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
        )
        self.adds(ec_cfg)
        return self

    def tuya_formaldehyde(
        self,
        dp_id: int,
        form_cfg: TuyaLocalCluster = TuyaFormaldehydeConcentration,
        # Convert from µg/m3 to ppm, note, ZHA will scale by 1e6
        converter: float = lambda x: round(
            ((MOL_VOL_AIR_NTP * x) / TuyaFormaldehydeConcentration.MOLECULAR_MASS), 2
        )
        * 1e-6,
    ) -> Self:
        """Add a Tuya Formaldehyde Configuration."""
        self.tuya_dp(
            dp_id,
            form_cfg.ep_attribute,
            FormaldehydeConcentration.AttributeDefs.measured_value.name,
            converter=converter,
        )
        self.adds(form_cfg)
        return self

    def tuya_pm25(
        self,
        dp_id: int,
        pm25_cfg: TuyaLocalCluster = TuyaPM25Concentration,
        scale: float = 1,
    ) -> Self:
        """Add a Tuya PM25 Configuration."""
        self.tuya_dp(
            dp_id,
            pm25_cfg.ep_attribute,
            PM25.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
        )
        self.adds(pm25_cfg)
        return self

    def tuya_gas(self, dp_id: int) -> Self:
        """Add a Tuya IAS gas sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasGas,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x == 0 else 0,
        )
        return self

    def tuya_smoke(self, dp_id: int) -> Self:
        """Add a Tuya IAS smoke/fire sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasFire,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x == 0 else 0,
        )
        return self

    def tuya_ias(
        self,
        dp_id: int,
        ias_cfg: TuyaLocalCluster,
        converter: Callable[[Any], Any] | None = None,
    ) -> Self:
        """Add a Tuya IAS Configuration."""
        self.tuya_dp(
            dp_id,
            ias_cfg.ep_attribute,
            IasZone.AttributeDefs.zone_status.name,
            converter=converter,
        )
        self.adds(ias_cfg)
        return self

    def tuya_metering(
        self,
        dp_id: int,
        metering_cfg: TuyaLocalCluster = TuyaValveWaterConsumedNoInstDemand,
        scale: float = 1,
    ) -> Self:
        """Add a Tuya Metering Configuration."""
        self.tuya_dp(
            dp_id,
            metering_cfg.ep_attribute,
            attribute_name="current_summ_delivered",
            converter=lambda x: x * scale,
        )
        self.adds(metering_cfg)
        return self

    def tuya_onoff(
        self,
        dp_id: int,
        onoff_cfg: TuyaLocalCluster = TuyaOnOffNM,
    ) -> Self:
        """Add a Tuya OnOff Configuration."""
        self.tuya_dp(
            dp_id,
            onoff_cfg.ep_attribute,
            "on_off",
        )
        self.adds(onoff_cfg)
        return self

    def tuya_humidity(
        self,
        dp_id: int,
        rh_cfg: TuyaLocalCluster = TuyaRelativeHumidity,
        scale: float = 100,
    ) -> Self:
        """Add a Tuya Relative Humidity Configuration."""
        self.tuya_dp(
            dp_id,
            rh_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
        )
        self.adds(rh_cfg)
        return self

    def tuya_soil_moisture(
        self,
        dp_id: int,
        soil_cfg: TuyaLocalCluster = TuyaSoilMoisture,
        scale: float = 100,
    ) -> Self:
        """Add a Tuya Soil Moisture Configuration."""
        self.tuya_dp(
            dp_id,
            soil_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
        )
        self.adds(soil_cfg)
        return self

    def tuya_temperature(
        self,
        dp_id: int,
        temp_cfg: TuyaLocalCluster = TuyaTemperatureMeasurement,
        scale: float = 100,
    ) -> Self:
        """Add a Tuya Temperature Configuration."""
        self.tuya_dp(
            dp_id,
            temp_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
        )
        self.adds(temp_cfg)
        return self

    def tuya_vibration(self, dp_id: int) -> Self:
        """Add a Tuya IAS vibration sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasVibration,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x != 0 else 0,
        )
        return self

    def tuya_voc(
        self,
        dp_id: int,
        voc_cfg: TuyaLocalCluster = TuyaAirQualityVOC,
        scale: float = 1e-6,
    ) -> Self:
        """Add a Tuya VOC Configuration."""
        self.tuya_dp(
            dp_id,
            voc_cfg.ep_attribute,
            TuyaAirQualityVOC.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
        )
        self.adds(voc_cfg)
        return self

    def tuya_attribute(
        self,
        dp_id: int,
        attribute_name: str,
        type: type = t.uint16_t,
        access: foundation.ZCLAttributeAccess = foundation.ZCLAttributeAccess.NONE,
        is_manufacturer_specific=True,
    ) -> Self:
        """Add an attribute to AttributeDefs."""
        attr_id: int = int.from_bytes([0xEF, dp_id])

        self.new_attributes.add(
            foundation.ZCLAttributeDef(
                id=attr_id,
                type=type,
                access=access,
                is_manufacturer_specific=is_manufacturer_specific,
                name=attribute_name,
            )
        )

        return self

    def tuya_dp(
        self,
        dp_id: int,
        ep_attribute: str,
        attribute_name: str,
        converter: Callable[[Any], Any] | None = None,
        dp_converter: Callable[[Any], Any] | None = None,
        endpoint_id: int | None = None,
        dp_handler: str = "_dp_2_attr_update",
    ) -> Self:
        """Add Tuya DP Converter."""

        self.tuya_dp_multi(
            dp_id,
            [
                DPToAttributeMapping(
                    ep_attribute,
                    attribute_name,
                    converter=converter,
                    dp_converter=dp_converter,
                    endpoint_id=endpoint_id,
                )
            ],
            dp_handler,
        )
        return self

    def tuya_dp_multi(
        self,
        dp_id: int,
        attribute_mapping: list[DPToAttributeMapping],
        dp_handler: str = "_dp_2_attr_update",
    ) -> Self:  # fmt: skip
        """Add Tuya DP Converter that maps to multiple attributes."""

        if dp_id in self.tuya_dp_to_attribute:
            raise ValueError(f"DP {dp_id} is already mapped.")

        self.tuya_dp_to_attribute.update({dp_id: attribute_mapping})
        self.tuya_data_point_handlers.update({dp_id: dp_handler})
        return self

    def tuya_dp_attribute(
        self,
        dp_id: int,
        attribute_name: str,
        ep_attribute: str = TuyaMCUCluster.ep_attribute,
        converter: Callable[[Any], Any] | None = None,
        dp_converter: Callable[[Any], Any] | None = None,
        endpoint_id: int | None = None,
        dp_handler: str = "_dp_2_attr_update",
        type: type = t.uint16_t,
        access: foundation.ZCLAttributeAccess = foundation.ZCLAttributeAccess.NONE,
        is_manufacturer_specific=True,
    ) -> Self:
        """Add an Tuya DataPoint and corresponding AttributeDef."""
        self.tuya_attribute(
            dp_id=dp_id,
            attribute_name=attribute_name,
            type=type,
            access=access,
            is_manufacturer_specific=is_manufacturer_specific,
        )
        self.tuya_dp(
            dp_id=dp_id,
            ep_attribute=ep_attribute,
            attribute_name=attribute_name,
            dp_converter=dp_converter,
            converter=converter,
            endpoint_id=endpoint_id,
            dp_handler=dp_handler,
        )
        return self

    def tuya_switch(
        self,
        dp_id: int,
        attribute_name: str = "on_off",
        endpoint_id: int = 1,
        force_inverted: bool = False,
        invert_attribute_name: str | None = None,
        off_value: int = 0,
        on_value: int = 1,
        entity_platform=EntityPlatform.SWITCH,
        entity_type: EntityType = EntityType.CONFIG,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        translation_key: str | None = None,
        fallback_name: str | None = None,
    ) -> Self:
        """Add an EntityMetadata containing SwitchMetadata and return self.

        This method allows exposing a switch entity in Home Assistant.
        """
        self.tuya_dp_attribute(
            dp_id=dp_id,
            attribute_name=attribute_name,
            type=t.Bool,
            access=foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Write,
        )
        self.switch(
            attribute_name=attribute_name,
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=endpoint_id,
            force_inverted=force_inverted,
            invert_attribute_name=invert_attribute_name,
            off_value=off_value,
            on_value=on_value,
            entity_platform=entity_platform,
            entity_type=entity_type,
            initially_disabled=initially_disabled,
            attribute_initialized_from_cache=attribute_initialized_from_cache,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )
        return self

    def tuya_enum(
        self,
        dp_id: int,
        attribute_name: str,
        enum_class: type[Enum],
        access: foundation.ZCLAttributeAccess = foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Write,
        endpoint_id: int = 1,
        entity_platform: EntityPlatform = EntityPlatform.SELECT,
        entity_type: EntityType = EntityType.CONFIG,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        translation_key: str | None = None,
        fallback_name: str | None = None,
    ) -> Self:
        """Add an EntityMetadata containing ZCLEnumMetadata and return self.

        This method allows exposing an enum based entity in Home Assistant.
        """
        self.tuya_dp_attribute(
            dp_id=dp_id,
            attribute_name=attribute_name,
            type=enum_class,
            access=access,
        )
        self.enum(
            attribute_name=attribute_name,
            enum_class=enum_class,
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=endpoint_id,
            entity_platform=entity_platform,
            entity_type=entity_type,
            initially_disabled=initially_disabled,
            attribute_initialized_from_cache=attribute_initialized_from_cache,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )

        return self

    def tuya_number(
        self,
        dp_id: int,
        type: type,
        attribute_name: str,
        access: foundation.ZCLAttributeAccess = foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Write,
        endpoint_id: int = 1,
        min_value: float | None = None,
        max_value: float | None = None,
        step: float | None = None,
        unit: str | None = None,
        mode: str | None = None,
        multiplier: float | None = None,
        entity_type: EntityType = EntityType.CONFIG,
        device_class: NumberDeviceClass | None = None,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        translation_key: str | None = None,
        fallback_name: str | None = None,
    ) -> Self:
        """Add an EntityMetadata containing NumberMetadata and return self.

        This method allows exposing a number entity in Home Assistant.
        """
        self.tuya_dp_attribute(
            dp_id=dp_id,
            attribute_name=attribute_name,
            type=type,
            access=access,
        )
        self.number(
            attribute_name=attribute_name,
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=endpoint_id,
            min_value=min_value,
            max_value=max_value,
            step=step,
            unit=unit,
            mode=mode,
            multiplier=multiplier,
            entity_type=entity_type,
            device_class=device_class,
            initially_disabled=initially_disabled,
            attribute_initialized_from_cache=attribute_initialized_from_cache,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )

        return self

    def tuya_binary_sensor(
        self,
        dp_id: int,
        attribute_name: str,
        endpoint_id: int = 1,
        entity_type: EntityType = EntityType.DIAGNOSTIC,
        device_class: BinarySensorDeviceClass | None = None,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        translation_key: str | None = None,
        fallback_name: str | None = None,
    ) -> Self:
        """Add an EntityMetadata containing BinarySensorMetadata and return self.

        This method allows exposing a binary sensor entity in Home Assistant.
        """
        self.tuya_dp_attribute(
            dp_id=dp_id,
            attribute_name=attribute_name,
            type=t.Bool,
            access=foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Report,
        )
        self.binary_sensor(
            attribute_name=attribute_name,
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=endpoint_id,
            entity_type=entity_type,
            device_class=device_class,
            initially_disabled=initially_disabled,
            attribute_initialized_from_cache=attribute_initialized_from_cache,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )

        return self

    def tuya_sensor(
        self,
        dp_id: int,
        attribute_name: str,
        type: type,
        converter: Callable[[Any], Any] | None = None,
        dp_converter: Callable[[Any], Any] | None = None,
        endpoint_id: int = 1,
        divisor: int = 1,
        multiplier: int = 1,
        entity_type: EntityType = EntityType.STANDARD,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        unit: str | None = None,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        translation_key: str | None = None,
        fallback_name: str | None = None,
    ) -> Self:
        """Add an EntityMetadata containing ZCLSensorMetadata and return self.

        This method allows exposing a sensor entity in Home Assistant.
        """

        self.tuya_dp_attribute(
            dp_id=dp_id,
            attribute_name=attribute_name,
            type=type,
            converter=converter,
            dp_converter=dp_converter,
            access=foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Report,
        )
        self.sensor(
            attribute_name=attribute_name,
            cluster_id=TUYA_CLUSTER_ID,
            endpoint_id=endpoint_id,
            divisor=divisor,
            multiplier=multiplier,
            entity_type=entity_type,
            device_class=device_class,
            state_class=state_class,
            unit=unit,
            initially_disabled=initially_disabled,
            attribute_initialized_from_cache=attribute_initialized_from_cache,
            translation_key=translation_key,
            fallback_name=fallback_name,
        )

        return self

    def tuya_enchantment(
        self, read_attr_spell: bool = True, data_query_spell: bool = False
    ) -> Self:
        """Set the Tuya enchantment spells."""

        class EnchantedDeviceV2(CustomDeviceV2, BaseEnchantedDevice):
            """Enchanted device class for v2 quirks."""

        EnchantedDeviceV2.tuya_spell_read_attributes = read_attr_spell
        EnchantedDeviceV2.tuya_spell_data_query = data_query_spell

        self.device_class(EnchantedDeviceV2)

        return self

    def add_to_registry(
        self,
        replacement_cluster: TuyaMCUCluster = TuyaMCUCluster,
        force_add_cluster: bool = False,
        mcu_write_command: foundation.GeneralCommand | int | t.uint8_t = TUYA_SET_DATA,
    ) -> QuirksV2RegistryEntry:
        """Build the quirks v2 registry entry.

        :param replacement_cluster: The cluster to add or replace the Tuya cluster with.
        :param force_add_cluster: Force add the Tuya cluster,
            even if no new Tuya attributes/datapoints were added before.
        :param mcu_write_command: The MCU command to use for the Tuya MCU cluster.
            Default is TUYA_SET_DATA. Few devices use TUYA_SEND_DATA instead.
        :return: The quirks v2 registry entry.
        """

        if (
            self.new_attributes
            or self.tuya_data_point_handlers
            or self.tuya_dp_to_attribute
            or force_add_cluster
        ):

            class NewAttributeDefs(TuyaMCUCluster.AttributeDefs):
                """Attribute Definitions."""

            for attr in self.new_attributes:
                setattr(NewAttributeDefs, attr.name, attr)

            class TuyaReplacementCluster(replacement_cluster):  # type: ignore[valid-type]
                """Replacement Tuya Cluster."""

                data_point_handlers: dict[int, str]
                dp_to_attribute: dict[int, list[DPToAttributeMapping]]

                class AttributeDefs(NewAttributeDefs):
                    """Attribute Definitions."""

            TuyaReplacementCluster.data_point_handlers = self.tuya_data_point_handlers
            TuyaReplacementCluster.dp_to_attribute = self.tuya_dp_to_attribute

            TuyaReplacementCluster.mcu_write_command = mcu_write_command

            self.replaces(TuyaReplacementCluster)
        return super().add_to_registry()
