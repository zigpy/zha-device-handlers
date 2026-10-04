"""Namron Simplify floor heating thermostat (4512795 white / 4512796 black)."""

from typing import Any, Final

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.hvac import (
    ControlSequenceOfOperation,
    RunningState,
    SystemMode,
    Thermostat,
    UserInterface,
)
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class ProgramMode(t.enum8):
    """Thermostat program, which the device reports in place of `system_mode`."""

    Manual = 0x00
    Home = 0x01
    Away = 0x02
    Sleep = 0x03
    Holiday = 0x04


class NamronThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster splitting the program out of `system_mode`.

    The device stores its program in `system_mode` and is turned on and off
    through the OnOff cluster. `system_mode` is rewritten to Off/Heat from the
    OnOff state and the raw value is exposed as the virtual `program_mode`.
    `running_state` is inverted and the PI demands never change, so the HVAC
    action is derived from a corrected `running_state` instead.
    """

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        # Virtual attribute, never sent to the device
        program_mode: Final = ZCLAttributeDef(id=0xF000, type=ProgramMode)
        # Holiday is in 0.01 °C like the standard setpoints, the others in 0.1 °C
        holiday_temperature: Final = ZCLAttributeDef(
            id=0x8013, type=t.int16s, manufacturer_code=None
        )
        away_temperature: Final = ZCLAttributeDef(
            id=0x8036, type=t.int16s, manufacturer_code=None
        )
        home_temperature: Final = ZCLAttributeDef(
            id=0x8039, type=t.int16s, manufacturer_code=None
        )
        sleep_temperature: Final = ZCLAttributeDef(
            id=0x803B, type=t.int16s, manufacturer_code=None
        )

    def _hvac_system_mode(self) -> SystemMode:
        on_off = self.endpoint.on_off.get(OnOff.AttributeDefs.on_off.id)
        if on_off is not None and not on_off:
            return SystemMode.Off
        return SystemMode.Heat

    def on_off_updated(self, on_off: bool) -> None:
        """Mirror the OnOff state into `system_mode`."""
        super()._update_attribute(
            self.AttributeDefs.system_mode.id,
            SystemMode.Heat if on_off else SystemMode.Off,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        if value is not None:
            if attrid == self.AttributeDefs.system_mode.id:
                super()._update_attribute(
                    self.AttributeDefs.program_mode.id, ProgramMode(int(value))
                )
                value = self._hvac_system_mode()
            elif attrid == self.AttributeDefs.ctrl_sequence_of_oper.id:
                # Reports Cooling_and_Heating, but it only heats
                value = ControlSequenceOfOperation.Heating_Only
            elif attrid == self.AttributeDefs.running_state.id:
                # Reports 0x0000 while heating and Cool_2nd_Stage_On while idle
                value = (
                    RunningState.Idle
                    if value & RunningState.Cool_2nd_Stage_On
                    else RunningState.Heat_State_On
                )
            elif attrid in (
                self.AttributeDefs.pi_heating_demand.id,
                self.AttributeDefs.pi_cooling_demand.id,
            ):
                # Always 0; ZHA only uses running_state when these are unset,
                # and clearing also drops a value cached before the quirk
                value = None

        super()._update_attribute(attrid, value)

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> Any:
        """Serve `program_mode` reads by reading `system_mode`."""
        program_mode_id = self.AttributeDefs.program_mode.id
        program_attrs = [
            attr
            for attr in attributes
            if self.find_attribute(attr).id == program_mode_id
        ]
        if not program_attrs:
            return await super().read_attributes(
                attributes, allow_cache, only_cache, manufacturer, **kwargs
            )

        success: dict = {}
        failure: dict = {}
        if others := [attr for attr in attributes if attr not in program_attrs]:
            success, failure = await super().read_attributes(
                others, allow_cache, only_cache, manufacturer, **kwargs
            )

        # A cached `system_mode` may predate the quirk, so read it fresh
        if not (allow_cache or only_cache) or self.get(program_mode_id) is None:
            await super().read_attributes(
                [self.AttributeDefs.system_mode.id],
                allow_cache=False,
                only_cache=only_cache,
                **kwargs,
            )

        value = self.get(program_mode_id)
        for attr in program_attrs:
            if value is None:
                failure[attr] = foundation.Status.FAILURE
            else:
                success[attr] = value

        return success, failure

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write `system_mode` as OnOff commands and `program_mode` as `system_mode`."""
        system_mode_id = self.AttributeDefs.system_mode.id
        program_mode_id = self.AttributeDefs.program_mode.id

        system_mode = None
        program_mode = None
        remaining = {}
        for attr, value in attributes.items():
            attr_id = self.find_attribute(attr).id
            if attr_id == system_mode_id:
                system_mode = value
            elif attr_id == program_mode_id:
                program_mode = value
            else:
                remaining[attr] = value

        records: list[foundation.WriteAttributesStatusRecord] = []
        if remaining:
            result = await super().write_attributes(remaining, manufacturer, **kwargs)
            records.extend(result[0])

        if program_mode is not None:
            status = foundation.Status.SUCCESS
            if program_mode != ProgramMode.Manual and program_mode == self.get(
                program_mode_id
            ):
                # Rewriting the active preset is ignored, so step through
                # Manual to clear a temporary setpoint override
                result = await super().write_attributes(
                    {system_mode_id: ProgramMode.Manual},
                    manufacturer,
                    update_cache=False,
                    **kwargs,
                )
                status = result[0][0].status
            if status == foundation.Status.SUCCESS:
                result = await super().write_attributes(
                    {system_mode_id: program_mode},
                    manufacturer,
                    update_cache=False,
                    **kwargs,
                )
                status = result[0][0].status
            if status == foundation.Status.SUCCESS:
                self._update_attribute(system_mode_id, program_mode)
            records.append(
                foundation.WriteAttributesStatusRecord(
                    status=status, attrid=program_mode_id
                )
            )

        if system_mode is not None:
            on_off = system_mode != SystemMode.Off
            cluster = self.endpoint.on_off
            response = await (cluster.on() if on_off else cluster.off())
            if response.status == foundation.Status.SUCCESS:
                cluster.update_attribute(OnOff.AttributeDefs.on_off.id, t.Bool(on_off))
            records.append(
                foundation.WriteAttributesStatusRecord(
                    status=response.status, attrid=system_mode_id
                )
            )

        return [records]


class NamronOnOffCluster(CustomCluster, OnOff):
    """OnOff cluster forwarding its state to the thermostat's `system_mode`."""

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == OnOff.AttributeDefs.on_off.id and value is not None:
            self.endpoint.thermostat.on_off_updated(bool(value))


(
    QuirkBuilder("Namron AS", "4512796")
    .applies_to("Namron AS", "4512795")
    .replaces(NamronThermostatCluster)
    .replaces(NamronOnOffCluster)
    # PI demand always reports 0
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Thermostat.cluster_id,
        unique_id_suffix=Thermostat.AttributeDefs.pi_heating_demand.name,
    )
    # On/off is controlled through the climate entity's Off/Heat modes
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.translation_key == "switch",
    )
    # Lock2-Lock4 all behave as Lock1, so a switch replaces the select
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=UserInterface.cluster_id,
        function=lambda entity: entity.translation_key == "keypad_lockout",
    )
    .switch(
        attribute_name=UserInterface.AttributeDefs.keypad_lockout.name,
        cluster_id=UserInterface.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .enum(
        attribute_name=NamronThermostatCluster.AttributeDefs.program_mode.name,
        enum_class=ProgramMode,
        cluster_id=NamronThermostatCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.home_temperature.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=5,
        max_value=40,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="home_temperature",
        fallback_name="Home temperature",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.away_temperature.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=5,
        max_value=40,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="away_temperature",
        fallback_name="Away temperature",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.sleep_temperature.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=5,
        max_value=40,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="sleep_temperature",
        fallback_name="Sleep temperature",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.holiday_temperature.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=5,
        max_value=40,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    .add_to_registry()
)
