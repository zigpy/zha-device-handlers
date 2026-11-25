"""Tuya QuirkBuilder."""

from collections.abc import Callable
from enum import Enum
import inspect
import math
import pathlib
from typing import Any, Self

from zha.quirks import QuirkRegistryEntry
from zha.zigbee.store import device_value
from zigpy.profiles import zha
from zigpy.store import StoredValue
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
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

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zhaquirks.const import BatterySize
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TUYA_SET_DATA,
    BaseEnchantedDevice,
    PowerConfiguration,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    DPToDeviceValueMapping,
    TuyaMCUCluster,
    TuyaOnOffNM,
    TuyaWindowCovering,
    tuya_device_value_writer,
)

MOL_VOL_AIR_NTP = 0.2445  # molar volume of air at NTP in cL/mol


def _as_stored(value: Any) -> Any:
    """Read a Tuya device value as stored: a JSON number, string or bool."""
    return value


BATTERY_VOLTAGES = {
    BatterySize.No_battery: None,
    BatterySize.Built_in: None,
    BatterySize.Other: None,
    BatterySize.AA: 15,
    BatterySize.AAA: 15,
    BatterySize.C: 15,
    BatterySize.D: 15,
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


class TuyaIasWaterLeak(IasZone, TuyaLocalCluster):
    """Tuya local IAS water leak cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Water_Sensor
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

    def __init__(self, *args, **kwargs) -> None:
        """Init the TuyaQuirkBuilder."""
        super().__init__(*args, **kwargs)
        self.tuya_data_point_handlers: dict[int, str] = {}
        self.tuya_dp_to_attribute: dict[
            int, list[DPToAttributeMapping | DPToDeviceValueMapping]
        ] = {}
        self.tuya_attributes_to_dp_converters: dict[int, Callable[[Any], Any]] = {}
        self.new_attributes: set[foundation.ZCLAttributeDef] = set()
        # quirk_file will point to the init call above if called from this QuirkBuilder,
        # so we need to re-set it correctly
        current_frame = inspect.currentframe()
        assert current_frame is not None
        caller = current_frame.f_back
        assert caller is not None
        self.quirk_file = pathlib.Path(caller.f_code.co_filename)
        self.quirk_file_line = caller.f_lineno

    def _tuya_battery(
        self,
        dp_id: int,
        power_cfg: type[PowerConfiguration],
        scale: float,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Battery Power Configuration."""
        self.tuya_dp(
            dp_id,
            power_cfg.ep_attribute,
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(power_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_battery(
        self,
        dp_id: int,
        power_cfg: type[PowerConfiguration] | None = None,
        battery_type: BatterySize | None = BatterySize.AA,
        battery_qty: int | None = 2,
        battery_voltage: int | None = None,
        scale: float = 2,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Battery Power Configuration."""

        if power_cfg:
            return self._tuya_battery(
                dp_id=dp_id, power_cfg=power_cfg, scale=scale, endpoint_id=endpoint_id
            )

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
            dp_id=dp_id,
            power_cfg=TuyaPowerConfigurationClusterBattery,
            scale=scale,
            endpoint_id=endpoint_id,
        )

    def tuya_illuminance(
        self,
        dp_id: int,
        illuminance_cfg: type[TuyaLocalCluster] = TuyaIlluminance,
        converter: Callable[[Any], Any] | None = (
            lambda x: 10000 * math.log10(x) + 1 if x != 0 else 0
        ),
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Illuminance Configuration."""
        self.tuya_dp(
            dp_id,
            illuminance_cfg.ep_attribute,
            IlluminanceMeasurement.AttributeDefs.measured_value.name,
            converter=converter,
            endpoint_id=endpoint_id,
        )
        self.adds(illuminance_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_contact(self, dp_id: int, endpoint_id: int = 1) -> Self:
        """Add a Tuya IAS contact sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasContact,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x != 0 else 0,
            endpoint_id=endpoint_id,
        )
        return self

    def tuya_co2(
        self,
        dp_id: int,
        co2_cfg: type[TuyaLocalCluster] = TuyaCO2Concentration,
        scale: float = 1e-6,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya CO2 Configuration."""
        self.tuya_dp(
            dp_id,
            co2_cfg.ep_attribute,
            CarbonDioxideConcentration.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(co2_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_electrical_conductivity(
        self,
        dp_id: int,
        ec_cfg: type[TuyaLocalCluster] = TuyaElectricalConductivity,
        scale: float = 1,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Electrical Conductivity Configuration."""
        self.tuya_dp(
            dp_id,
            ec_cfg.ep_attribute,
            ElectricalConductivity.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(ec_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_formaldehyde(
        self,
        dp_id: int,
        form_cfg: type[TuyaLocalCluster] = TuyaFormaldehydeConcentration,
        # Convert from µg/m3 to ppm, note, ZHA will scale by 1e6
        converter: Callable[[Any], Any] | None = lambda x: (
            round(
                ((MOL_VOL_AIR_NTP * x) / TuyaFormaldehydeConcentration.MOLECULAR_MASS),
                2,
            )
            * 1e-6
        ),
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Formaldehyde Configuration."""
        self.tuya_dp(
            dp_id,
            form_cfg.ep_attribute,
            FormaldehydeConcentration.AttributeDefs.measured_value.name,
            converter=converter,
            endpoint_id=endpoint_id,
        )
        self.adds(form_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_pm25(
        self,
        dp_id: int,
        pm25_cfg: type[TuyaLocalCluster] = TuyaPM25Concentration,
        scale: float = 1,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya PM25 Configuration."""
        self.tuya_dp(
            dp_id,
            pm25_cfg.ep_attribute,
            PM25.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(pm25_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_gas(self, dp_id: int, endpoint_id: int = 1) -> Self:
        """Add a Tuya IAS gas sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasGas,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x == 0 else 0,
            endpoint_id=endpoint_id,
        )
        return self

    def tuya_smoke(self, dp_id: int, endpoint_id: int = 1) -> Self:
        """Add a Tuya IAS smoke/fire sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasFire,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x == 0 else 0,
            endpoint_id=endpoint_id,
        )
        return self

    def tuya_ias(
        self,
        dp_id: int,
        ias_cfg: type[TuyaLocalCluster],
        converter: Callable[[Any], Any] | None = None,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya IAS Configuration."""
        self.tuya_dp(
            dp_id,
            ias_cfg.ep_attribute,
            IasZone.AttributeDefs.zone_status.name,
            converter=converter,
            endpoint_id=endpoint_id,
        )
        self.adds(ias_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_metering(
        self,
        dp_id: int,
        metering_cfg: type[TuyaLocalCluster] = TuyaValveWaterConsumedNoInstDemand,
        scale: float = 1,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Metering Configuration."""
        self.tuya_dp(
            dp_id,
            metering_cfg.ep_attribute,
            attribute_name="current_summ_delivered",
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(metering_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_onoff(
        self,
        dp_id: int,
        onoff_cfg: type[TuyaLocalCluster] = TuyaOnOffNM,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya OnOff Configuration."""
        self.tuya_dp(
            dp_id,
            onoff_cfg.ep_attribute,
            "on_off",
            endpoint_id=endpoint_id,
        )
        self.adds(onoff_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_cover(
        self,
        control_dp: int,
        position_state_dp: int,
        position_control_dp: int,
        invert: bool = True,
        cover_cfg: type[TuyaLocalCluster] = TuyaWindowCovering,
    ) -> Self:
        """Add a Tuya WindowCovering Configuration.

        :param control_dp: DP ID for open/stop/close control (enum).
        :param position_state_dp: DP ID for current position reports (0-100).
        :param position_control_dp: DP ID for setting target position (0-100).
        :param invert: Invert position values (most Tuya covers report
            0=closed, 100=open which is opposite to ZCL convention).
        :param cover_cfg: Custom WindowCovering cluster class to use.
        """
        converter = (lambda x: 100 - x) if invert else None
        dp_converter = (lambda x: 100 - x) if invert else None

        self.tuya_dp(
            control_dp,
            cover_cfg.ep_attribute,
            TuyaWindowCovering.AttributeDefs.tuya_cover_command.name,
        )
        self.tuya_dp(
            position_state_dp,
            cover_cfg.ep_attribute,
            WindowCovering.AttributeDefs.current_position_lift_percentage.name,
            converter=converter,
            dp_converter=dp_converter,
        )
        self.tuya_dp(
            position_control_dp,
            cover_cfg.ep_attribute,
            WindowCovering.AttributeDefs.current_position_lift_percentage.name,
            converter=converter,
            dp_converter=dp_converter,
        )
        self.adds(cover_cfg)
        self.replaces_endpoint(1, device_type=zha.DeviceType.WINDOW_COVERING_DEVICE)
        return self

    def tuya_humidity(
        self,
        dp_id: int,
        rh_cfg: type[TuyaLocalCluster] = TuyaRelativeHumidity,
        scale: float = 100,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Relative Humidity Configuration."""
        self.tuya_dp(
            dp_id,
            rh_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(rh_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_soil_moisture(
        self,
        dp_id: int,
        soil_cfg: type[TuyaLocalCluster] = TuyaSoilMoisture,
        scale: float = 100,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Soil Moisture Configuration."""
        self.tuya_dp(
            dp_id,
            soil_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(soil_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_temperature(
        self,
        dp_id: int,
        temp_cfg: type[TuyaLocalCluster] = TuyaTemperatureMeasurement,
        scale: float = 100,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya Temperature Configuration."""
        self.tuya_dp(
            dp_id,
            temp_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(temp_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_vibration(self, dp_id: int, endpoint_id: int = 1) -> Self:
        """Add a Tuya IAS vibration sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasVibration,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x != 0 else 0,
            endpoint_id=endpoint_id,
        )
        return self

    def tuya_voc(
        self,
        dp_id: int,
        voc_cfg: type[TuyaLocalCluster] = TuyaAirQualityVOC,
        scale: float = 1e-6,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a Tuya VOC Configuration."""
        self.tuya_dp(
            dp_id,
            voc_cfg.ep_attribute,
            TuyaAirQualityVOC.AttributeDefs.measured_value.name,
            converter=lambda x: x * scale,
            endpoint_id=endpoint_id,
        )
        self.adds(voc_cfg, endpoint_id=endpoint_id)
        return self

    def tuya_water_leak(self, dp_id: int, endpoint_id: int = 1) -> Self:
        """Add a Tuya IAS water leak sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasWaterLeak,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x != 0 else 0,
            endpoint_id=endpoint_id,
        )
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
                    endpoint_id=endpoint_id,
                )
            ],
            dp_handler,
            dp_converter,
        )
        return self

    def tuya_dp_multi(
        self,
        dp_id: int,
        attribute_mapping: list[DPToAttributeMapping | DPToDeviceValueMapping],
        dp_handler: str = "_dp_2_attr_update",
        dp_converter: Callable[[Any], Any] | None = None,
    ) -> Self:  # fmt: skip
        """Add Tuya DP Converter that maps to multiple attributes."""

        if dp_id in self.tuya_dp_to_attribute:
            raise ValueError(f"DP {dp_id} is already mapped.")

        mapped_values = {
            (mapping.value.namespace, mapping.value.key)
            for mappings in self.tuya_dp_to_attribute.values()
            for mapping in mappings
            if isinstance(mapping, DPToDeviceValueMapping)
        }

        for mapping in attribute_mapping:
            if not isinstance(mapping, DPToDeviceValueMapping):
                continue

            if (
                mapping.converter is not None
                and mapping.wire_type is not None
                and dp_converter is None
            ):
                raise ValueError(
                    f"Device value {mapping.value.key!r} is read through a converter,"
                    " which a write cannot invert: give the datapoint a dp_converter"
                )

            value_id = (mapping.value.namespace, mapping.value.key)

            if value_id in mapped_values:
                raise ValueError(
                    f"Device value {mapping.value.key!r} is already mapped"
                )

            mapped_values.add(value_id)

        self.tuya_dp_to_attribute.update({dp_id: attribute_mapping})
        self.tuya_data_point_handlers.update({dp_id: dp_handler})
        if dp_converter:
            self.tuya_attributes_to_dp_converters.update({dp_id: dp_converter})
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

    def _tuya_device_value(
        self,
        dp_id: int,
        attribute_name: str,
        *,
        converter: Callable[[Any], Any] | None = None,
        wire_type: Callable[[Any], Any] | None = None,
        fallback_name: str | None,
        attribute_initialized_from_cache: bool,
    ) -> StoredValue[Any]:
        """Map a datapoint to a device value named `attribute_name` and return it.

        This is the `as_device_value` path of the entity helpers: no invented
        attribute is added to the Tuya cluster.
        """
        if fallback_name is None:
            raise ValueError(f"A device value entity needs a fallback_name: {dp_id}")

        if not attribute_initialized_from_cache:
            raise ValueError(
                "A device value cannot be read from the device, so it cannot be "
                f"read at startup (attribute_initialized_from_cache=False): {dp_id}"
            )

        # Kept as the converter returns it: the wire type need not fit a converted
        # value (a float, a signed value)
        value = device_value(attribute_name, _as_stored)
        self.tuya_dp_multi(
            dp_id,
            [DPToDeviceValueMapping(value, converter=converter, wire_type=wire_type)],
        )

        return value

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
        *,
        translation_placeholders: dict[str, str] | None = None,
        as_device_value: bool = False,
        child_device_id: str | None | UndefinedType = UNDEFINED,
    ) -> Self:
        """Add an EntityMetadata containing SwitchMetadata and return self.

        This method allows exposing a switch entity in Home Assistant.

        With `as_device_value`, the datapoint is kept as a device value named
        `attribute_name` in the device's store instead of an invented attribute on
        the Tuya cluster, and the switch writes it through the Tuya cluster. The
        switch keeps the unique ID it has otherwise.
        """
        if as_device_value:
            if invert_attribute_name is not None:
                raise ValueError(
                    "A device value switch cannot be inverted by an attribute: "
                    f"{invert_attribute_name}"
                )

            if entity_platform != EntityPlatform.SWITCH:
                raise ValueError(
                    f"A device value switch is a switch, not a {entity_platform}"
                )

            value = self._tuya_device_value(
                dp_id,
                attribute_name,
                wire_type=t.Bool,
                fallback_name=fallback_name,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
            )

            return self.device_value_switch(
                value,
                writer=tuya_device_value_writer(value),
                unique_id_suffix=f"{endpoint_id}-{attribute_name}",
                force_inverted=force_inverted,
                off_value=off_value,
                on_value=on_value,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
                fallback_name=fallback_name,
            )

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
            translation_placeholders=translation_placeholders,
            child_device_id=child_device_id,
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
        *,
        translation_placeholders: dict[str, str] | None = None,
        as_device_value: bool = False,
        child_device_id: str | None | UndefinedType = UNDEFINED,
    ) -> Self:
        """Add an EntityMetadata containing ZCLEnumMetadata and return self.

        This method allows exposing an enum based entity in Home Assistant.

        With `as_device_value`, the datapoint is kept as a device value named
        `attribute_name` in the device's store instead of an invented attribute on
        the Tuya cluster, and the select writes it through the Tuya cluster. The
        select keeps the unique ID it has otherwise.
        """
        if as_device_value:
            if entity_platform != EntityPlatform.SELECT:
                raise ValueError(
                    "Only a select can show an enum device value so far, not a "
                    f"{entity_platform}"
                )

            if not access & foundation.ZCLAttributeAccess.Write:
                raise ValueError(f"A device value select must be writable: {access!r}")

            if not issubclass(enum_class, int):
                raise TypeError(
                    f"An enum datapoint needs an int enum, not {enum_class!r}"
                )

            value = self._tuya_device_value(
                dp_id,
                attribute_name,
                wire_type=enum_class,
                fallback_name=fallback_name,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
            )

            return self.device_value_select(
                value,
                enum_class,
                writer=tuya_device_value_writer(value),
                unique_id_suffix=f"{endpoint_id}-{attribute_name}",
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
                fallback_name=fallback_name,
            )

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
            translation_placeholders=translation_placeholders,
            child_device_id=child_device_id,
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
        *,
        translation_placeholders: dict[str, str] | None = None,
        as_device_value: bool = False,
        child_device_id: str | None | UndefinedType = UNDEFINED,
    ) -> Self:
        """Add an EntityMetadata containing NumberMetadata and return self.

        This method allows exposing a number entity in Home Assistant.

        With `as_device_value`, the datapoint is kept as a device value named
        `attribute_name` in the device's store instead of an invented attribute on
        the Tuya cluster, and the number writes it through the Tuya cluster, cast to
        `type`. The number keeps the unique ID it has otherwise.
        """
        if as_device_value:
            if not access & foundation.ZCLAttributeAccess.Write:
                raise ValueError(f"A device value number must be writable: {access!r}")

            value = self._tuya_device_value(
                dp_id,
                attribute_name,
                wire_type=type,
                fallback_name=fallback_name,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
            )

            return self.device_value_number(
                value,
                writer=tuya_device_value_writer(value),
                unique_id_suffix=f"{endpoint_id}-{attribute_name}",
                min_value=min_value,
                max_value=max_value,
                step=step,
                unit=unit,
                mode=mode,
                multiplier=multiplier,
                entity_type=entity_type,
                device_class=device_class,
                initially_disabled=initially_disabled,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
                fallback_name=fallback_name,
            )

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
            translation_placeholders=translation_placeholders,
            child_device_id=child_device_id,
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
        *,
        translation_placeholders: dict[str, str] | None = None,
        as_device_value: bool = False,
        child_device_id: str | None | UndefinedType = UNDEFINED,
    ) -> Self:
        """Add an EntityMetadata containing BinarySensorMetadata and return self.

        This method allows exposing a binary sensor entity in Home Assistant.

        With `as_device_value`, the datapoint is kept as a device value named
        `attribute_name` in the device's store instead of an invented attribute on
        the Tuya cluster. The binary sensor keeps the unique ID it has otherwise.
        """
        if as_device_value:
            value = self._tuya_device_value(
                dp_id,
                attribute_name,
                fallback_name=fallback_name,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
            )

            return self.device_value_binary_sensor(
                value,
                unique_id_suffix=f"{endpoint_id}-{attribute_name}",
                entity_type=entity_type,
                device_class=device_class,
                initially_disabled=initially_disabled,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
                fallback_name=fallback_name,
            )

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
            translation_placeholders=translation_placeholders,
            child_device_id=child_device_id,
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
        *,
        translation_placeholders: dict[str, str] | None = None,
        child_device_id: str | None | UndefinedType = UNDEFINED,
        as_device_value: bool = False,
    ) -> Self:
        """Add an EntityMetadata containing ZCLSensorMetadata and return self.

        This method allows exposing a sensor entity in Home Assistant.

        With `as_device_value`, the datapoint is kept as a device value named
        `attribute_name` in the device's store instead of an invented attribute on
        the Tuya cluster. The sensor keeps the unique ID it has otherwise.
        """
        if as_device_value:
            if dp_converter is not None:
                raise ValueError("A device value sensor is read-only: no dp_converter")

            if translation_key is None and device_class is None:
                raise ValueError(
                    "A device value sensor needs a translation_key or device_class"
                )

            value = self._tuya_device_value(
                dp_id,
                attribute_name,
                converter=converter,
                fallback_name=fallback_name,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
            )

            return self.device_value_sensor(
                value,
                unique_id_suffix=f"{endpoint_id}-{attribute_name}",
                divisor=divisor,
                multiplier=multiplier,
                entity_type=entity_type,
                device_class=device_class,
                state_class=state_class,
                unit=unit,
                initially_disabled=initially_disabled,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
                fallback_name=fallback_name,
            )

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
            translation_placeholders=translation_placeholders,
            child_device_id=child_device_id,
            fallback_name=fallback_name,
        )

        return self

    def tuya_enchantment(
        self, read_attr_spell: bool = True, data_query_spell: bool = False
    ) -> Self:
        """Set the Tuya enchantment spells."""

        class EnchantedDeviceV2(CustomZigpyDevice, BaseEnchantedDevice):
            """Enchanted device class for v2 quirks."""

        EnchantedDeviceV2.tuya_spell_read_attributes = read_attr_spell
        EnchantedDeviceV2.tuya_spell_data_query = data_query_spell

        self.device_class(EnchantedDeviceV2)

        return self

    def add_to_registry(
        self,
        replacement_cluster: type[TuyaMCUCluster] = TuyaMCUCluster,
        force_add_cluster: bool = False,
        mcu_write_command: foundation.GeneralCommand | int | t.uint8_t = TUYA_SET_DATA,
    ) -> QuirkRegistryEntry:
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
            or self.tuya_attributes_to_dp_converters
            or force_add_cluster
        ):

            class NewAttributeDefs(TuyaMCUCluster.AttributeDefs):
                """Attribute Definitions."""

            for attr in self.new_attributes:
                setattr(NewAttributeDefs, attr.name, attr)

            class TuyaReplacementCluster(replacement_cluster):  # type: ignore[valid-type]
                """Replacement Tuya Cluster."""

                data_point_handlers: dict[int, str]
                dp_to_attribute: dict[
                    int, list[DPToAttributeMapping | DPToDeviceValueMapping]
                ]

                class AttributeDefs(NewAttributeDefs):
                    """Attribute Definitions."""

            TuyaReplacementCluster.data_point_handlers = self.tuya_data_point_handlers
            TuyaReplacementCluster.dp_to_attribute = self.tuya_dp_to_attribute
            TuyaReplacementCluster.attributes_to_dp_converters = (
                self.tuya_attributes_to_dp_converters
            )
            TuyaReplacementCluster.mcu_write_command = mcu_write_command

            self.replaces(TuyaReplacementCluster)
        return super().add_to_registry()
