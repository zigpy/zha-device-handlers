"""Tuya QuirkBuilder."""

from collections.abc import Callable
from enum import Enum
from typing import Any, Optional

from zigpy.quirks import _DEVICE_REGISTRY
from zigpy.quirks.registry import DeviceRegistry
from zigpy.quirks.v2 import QuirkBuilder, QuirksV2RegistryEntry
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import (
    RelativeHumidity,
    SoilMoisture,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    PowerConfiguration,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster2AAA,
)
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster, TuyaOnOffNM


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

    def __init__(self, *args, **kwargs):
        """Init a TuyaValveWaterConsumed cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(Metering.AttributeDefs.instantaneous_demand.id)


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
        self.tuya_dp_to_attribute: dict[int, DPToAttributeMapping] = {}
        self.new_attributes: set[foundation.ZCLAttributeDef] = set()
        super().__init__(manufacturer, model, registry)

    def tuya_battery(
        self,
        dp_id: int,
        power_cfg: PowerConfiguration = TuyaPowerConfigurationCluster2AAA,
        scale: float = 2,
    ) -> QuirkBuilder:
        """Add a Tuya Battery Power Configuration."""
        self.tuya_dp(
            dp_id,
            power_cfg.ep_attribute,
            "battery_percentage_remaining",
            converter=lambda x: x * scale,
        )
        self.adds(power_cfg)
        return self

    def tuya_contact(self, dp_id: int):
        """Add a Tuya IAS contact sensor."""
        self.tuya_ias(
            dp_id=dp_id,
            ias_cfg=TuyaIasContact,
            converter=lambda x: IasZone.ZoneStatus.Alarm_1 if x != 0 else 0,
        )
        return self

    def tuya_smoke(self, dp_id: int):
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
        converter: Optional[Callable[[Any], Any]] = None,
    ) -> QuirkBuilder:
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
        metering_cfg: TuyaLocalCluster = TuyaValveWaterConsumed,
        scale: float = 1,
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
        """Add a Tuya Soil Moisture Configuration."""
        self.tuya_dp(
            dp_id,
            temp_cfg.ep_attribute,
            "measured_value",
            converter=lambda x: x * scale,
        )
        self.adds(temp_cfg)
        return self

    def tuya_attribute(
        self,
        dp_id: int,
        attribute_name: str,
        type: type = t.uint16_t,
        access: foundation.ZCLAttributeAccess = foundation.ZCLAttributeAccess.NONE,
        is_manufacturer_specific=True,
    ) -> QuirkBuilder:
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
        converter: Optional[Callable[[Any], Any]] = None,
        dp_converter: Optional[Callable[[Any], Any]] = None,
        endpoint_id: Optional[int] = None,
        dp_handler: str = "_dp_2_attr_update",
    ) -> QuirkBuilder:  # fmt: skip
        """Add Tuya DP Converter."""
        self.tuya_dp_to_attribute.update(
            {
                dp_id: DPToAttributeMapping(
                    ep_attribute,
                    attribute_name,
                    converter=converter,
                    dp_converter=dp_converter,
                    endpoint_id=endpoint_id,
                )
            }
        )
        self.tuya_data_point_handlers.update({dp_id: dp_handler})
        return self

    def tuya_dp_attribute(
        self,
        dp_id: int,
        attribute_name: str,
        ep_attribute: str = TuyaMCUCluster.ep_attribute,
        converter: Optional[Callable[[Any], Any]] = None,
        dp_converter: Optional[Callable[[Any], Any]] = None,
        endpoint_id: Optional[int] = None,
        dp_handler: str = "_dp_2_attr_update",
        type: type = t.uint16_t,
        access: foundation.ZCLAttributeAccess = foundation.ZCLAttributeAccess.NONE,
        is_manufacturer_specific=True,
    ) -> QuirkBuilder:  # fmt: skip
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
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
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
    ) -> QuirkBuilder:
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
        converter: Optional[Callable[[Any], Any]] = None,
        dp_converter: Optional[Callable[[Any], Any]] = None,
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
    ) -> QuirkBuilder:  # fmt: skip
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

    def add_to_registry(self) -> QuirksV2RegistryEntry:
        """Build the quirks v2 registry entry."""

        class NewAttributeDefs(TuyaMCUCluster.AttributeDefs):
            """Attribute Definitions."""

        for attr in self.new_attributes:
            setattr(NewAttributeDefs, attr.name, attr)

        class TuyaReplacementCluster(TuyaMCUCluster):
            """Replacement Tuya Cluster."""

            data_point_handlers: dict[int, str]
            dp_to_attribute: dict[int, DPToAttributeMapping]

            class AttributeDefs(NewAttributeDefs):
                """Attribute Definitions."""

            async def write_attributes(self, attributes, manufacturer=None):
                """Overwrite to force manufacturer code."""

                return await super().write_attributes(
                    attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
                )

        TuyaReplacementCluster.data_point_handlers = self.tuya_data_point_handlers
        TuyaReplacementCluster.dp_to_attribute = self.tuya_dp_to_attribute

        self.replaces(TuyaReplacementCluster)
        return super().add_to_registry()
