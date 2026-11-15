"""Salus ST100ZB fan coil thermostat."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.salus import COMPUTIME_MANUFACTURER_CODE


class SalusHoldType(t.enum8):
    """Whether the thermostat's own schedule may change the setpoint."""

    Schedule = 0x00
    TemporaryOverride = 0x01
    PermanentOverride = 0x02


class SalusTimeFormat(t.enum8):
    """Clock format on the display."""

    Format_12h = 0x00
    Format_24h = 0x01


class SalusThermostatCluster(CustomCluster):
    """Salus (Computime) manufacturer-specific thermostat cluster."""

    cluster_id: t.uint16_t = 0xFC04
    name: str = "Salus Thermostat"
    ep_attribute: str = "salus_thermostat"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        time_format: Final = ZCLAttributeDef(
            id=0x0003,
            type=SalusTimeFormat,
            zcl_type=DataTypeId.bool_,
            manufacturer_code=COMPUTIME_MANUFACTURER_CODE,
        )
        hold_type: Final = ZCLAttributeDef(
            id=0x000A,
            type=SalusHoldType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=COMPUTIME_MANUFACTURER_CODE,
        )


class SalusThermostat(CustomCluster, Thermostat):
    """Thermostat cluster with the absolute setpoint limits the device lacks.

    Values are the heating and cooling limit ranges of the installer settings.
    """

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 3350,
        Thermostat.AttributeDefs.abs_min_cool_setpoint_limit.id: 650,
        Thermostat.AttributeDefs.abs_max_cool_setpoint_limit.id: 3500,
    }


class SalusFanCoilType(t.enum8):
    """Fan coil type (installer setting P01)."""

    TwoPipe = 0x00
    FourPipe = 0x01


class SalusHeatCoolOption(t.enum8):
    """Heat/cool option (installer setting P02); the meaning follows P01.

    - 2-pipe: heat only, cool only, manual changeover, seasonal changeover,
      or heat or cool with auxiliary heat (the last two need the pipe sensor).
    - 4-pipe: manual changeover, heat/cool/auto changeover, or auto changeover
      only. The thermostat refuses heat only and cool only (INVALID_VALUE).
    """

    HeatOnly = 0x00
    CoolOnly = 0x01
    ManualChangeover = 0x02
    AutoChangeover = 0x03
    AuxHeatOrAutoOnly = 0x04


FOUR_PIPE_HEAT_COOL_OPTIONS: Final = frozenset(
    {
        SalusHeatCoolOption.ManualChangeover,
        SalusHeatCoolOption.AutoChangeover,
        SalusHeatCoolOption.AuxHeatOrAutoOnly,
    }
)


class SalusInstallerCluster(CustomCluster):
    """Salus (Computime) manufacturer-specific installer settings cluster.

    Writing a setting switches the thermostat to Off, as leaving the installer
    menu on the keypad does.
    """

    cluster_id: t.uint16_t = 0xFC06
    name: str = "Salus Installer"
    ep_attribute: str = "salus_installer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        fan_coil_type: Final = ZCLAttributeDef(
            id=0x0000,
            type=SalusFanCoilType,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=COMPUTIME_MANUFACTURER_CODE,
        )
        heat_cool_option: Final = ZCLAttributeDef(
            id=0x0003,
            type=SalusHeatCoolOption,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=COMPUTIME_MANUFACTURER_CODE,
        )

    async def write_attributes(self, attributes, *args, **kwargs):
        """Reset a heat/cool option that the new fan coil type doesn't allow.

        The thermostat checks the heat/cool option against the fan coil type
        when the option is written, but keeps it when the fan coil type
        changes. Auto changeover is the factory default and valid for both.
        """
        attrs = self.AttributeDefs
        names = {
            self.find_attribute(attr).name: value for attr, value in attributes.items()
        }
        if (
            names.get(attrs.fan_coil_type.name) == SalusFanCoilType.FourPipe
            and attrs.heat_cool_option.name not in names
        ):
            success, _ = await self.read_attributes([attrs.heat_cool_option.name])
            if (
                success.get(attrs.heat_cool_option.name)
                not in FOUR_PIPE_HEAT_COOL_OPTIONS
            ):
                attributes = {
                    **attributes,
                    attrs.heat_cool_option.name: SalusHeatCoolOption.AutoChangeover,
                }
        return await super().write_attributes(attributes, *args, **kwargs)


(
    QuirkBuilder("SALUS", "ST100ZB")
    .replaces(SalusThermostatCluster, endpoint_id=9)
    .replaces(SalusThermostat, endpoint_id=9)
    .enum(
        attribute_name=SalusThermostatCluster.AttributeDefs.hold_type.name,
        enum_class=SalusHoldType,
        cluster_id=SalusThermostatCluster.cluster_id,
        endpoint_id=9,
        attribute_initialized_from_cache=False,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=3600, reportable_change=1
        ),
        translation_key="hold_type",
        fallback_name="Hold type",
    )
    .enum(
        attribute_name=SalusThermostatCluster.AttributeDefs.time_format.name,
        enum_class=SalusTimeFormat,
        cluster_id=SalusThermostatCluster.cluster_id,
        endpoint_id=9,
        translation_key="time_format",
        fallback_name="Time format",
    )
    .switch(
        attribute_name=Thermostat.AttributeDefs.remote_sensing.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=9,
        translation_key="external_temperature_sensor",
        fallback_name="External temperature sensor",
    )
    .number(
        attribute_name=Thermostat.AttributeDefs.min_cool_setpoint_limit.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=9,
        min_value=6.5,
        max_value=35,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        mode="box",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="min_cool_setpoint_limit",
        fallback_name="Min cool setpoint limit",
    )
    .number(
        attribute_name=Thermostat.AttributeDefs.max_cool_setpoint_limit.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=9,
        min_value=6.5,
        max_value=35,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        mode="box",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="max_cool_setpoint_limit",
        fallback_name="Max cool setpoint limit",
    )
    .enum(
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        enum_class=UserInterface.TemperatureDisplayMode,
        cluster_id=UserInterface.cluster_id,
        endpoint_id=9,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
    )
    .binary_sensor(
        attribute_name=Thermostat.AttributeDefs.ac_error_code.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=9,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=bool,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=3600, reportable_change=1
        ),
        fallback_name="Problem",
    )
    .replaces(SalusInstallerCluster, endpoint_id=9)
    .enum(
        attribute_name=SalusInstallerCluster.AttributeDefs.fan_coil_type.name,
        enum_class=SalusFanCoilType,
        cluster_id=SalusInstallerCluster.cluster_id,
        endpoint_id=9,
        initially_disabled=True,
        translation_key="fan_coil_type",
        fallback_name="Fan coil type",
    )
    .enum(
        attribute_name=SalusInstallerCluster.AttributeDefs.heat_cool_option.name,
        enum_class=SalusHeatCoolOption,
        cluster_id=SalusInstallerCluster.cluster_id,
        endpoint_id=9,
        initially_disabled=True,
        translation_key="heat_cool_option",
        fallback_name="Heat/cool option",
    )
    .add_to_registry()
)
