"""Tuya Light and Fan Speed switches."""

from __future__ import annotations

from typing import Any

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import EntityType, UnitOfTime
from zhaquirks.tuya import TUYA_MCU_COMMAND, PowerOnState
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import MoesBacklight, TuyaAttributesCluster, TuyaClusterData


class TuyaSpeedFan(t.enum8):
    """Tuya speed fan enum."""

    min = 0x00
    low = 0x01
    mid = 0x02
    high = 0x03
    max = 0x04


TUYA_SPEED_TO_FAN_MODE = {
    TuyaSpeedFan.min: Fan.FanMode.Low,
    TuyaSpeedFan.low: Fan.FanMode.Low,
    TuyaSpeedFan.mid: Fan.FanMode.Medium,
    TuyaSpeedFan.high: Fan.FanMode.High,
    TuyaSpeedFan.max: Fan.FanMode.High,
}

FAN_MODE_TO_TUYA_SPEED = {
    Fan.FanMode.Low: TuyaSpeedFan.low,
    Fan.FanMode.Medium: TuyaSpeedFan.mid,
    Fan.FanMode.High: TuyaSpeedFan.high,
    Fan.FanMode.On: TuyaSpeedFan.max,
}


class TuyaFanCluster(TuyaAttributesCluster, Fan):
    """Tuya custom Fan cluster using TuyaAttributesCluster."""

    _CONSTANT_ATTRIBUTES = {
        Fan.AttributeDefs.fan_mode_sequence.id: Fan.FanModeSequence.Low_Med_High,
    }

    class AttributeDefs(Fan.AttributeDefs):
        """Attribute definitions."""

        fan_switch = ZCLAttributeDef(
            id=0xEF01,
            type=t.Bool,
            access=foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Write
            | foundation.ZCLAttributeAccess.Report,
            is_manufacturer_specific=True,
        )
        fan_speed = ZCLAttributeDef(
            id=0xEF03,
            type=TuyaSpeedFan,
            access=foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Write
            | foundation.ZCLAttributeAccess.Report,
            is_manufacturer_specific=True,
        )

    def _send_mcu_command(
        self,
        attr_name: str,
        val: Any,
        manufacturer: int | UndefinedType | None = UNDEFINED,
    ) -> None:
        """Dispatch Tuya MCU command through device command bus."""
        cluster_data = TuyaClusterData(
            endpoint_id=self.endpoint.endpoint_id,
            cluster_name=self.ep_attribute,
            cluster_attr=attr_name,
            attr_value=val,
            expect_reply=False,
            manufacturer=manufacturer,
        )
        self.endpoint.device.command_bus.listener_event(
            TUYA_MCU_COMMAND,
            cluster_data,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Handle writing standard and custom fan attributes."""
        records = self._write_attr_records(attributes)
        for record in records:
            attr_name = self.attributes[record.attrid].name
            val = record.value.value

            if attr_name == "fan_mode":
                mode = Fan.FanMode(val)
                if mode == Fan.FanMode.Off:
                    self._send_mcu_command("fan_switch", False, manufacturer)
                    super()._update_attribute(
                        Fan.AttributeDefs.fan_mode.id, Fan.FanMode.Off
                    )
                elif mode == Fan.FanMode.On:
                    current_speed = self.get(
                        self.AttributeDefs.fan_speed.id, TuyaSpeedFan.mid
                    )
                    self._send_mcu_command("fan_switch", True, manufacturer)
                    super()._update_attribute(
                        Fan.AttributeDefs.fan_mode.id,
                        TUYA_SPEED_TO_FAN_MODE.get(
                            TuyaSpeedFan(current_speed), Fan.FanMode.Medium
                        ),
                    )
                else:
                    tuya_speed = FAN_MODE_TO_TUYA_SPEED.get(mode, TuyaSpeedFan.mid)
                    self._send_mcu_command("fan_speed", tuya_speed, manufacturer)
                    self._send_mcu_command("fan_switch", True, manufacturer)
                    super()._update_attribute(Fan.AttributeDefs.fan_mode.id, mode)

            elif attr_name == "fan_speed":
                tuya_speed = TuyaSpeedFan(val)
                self._send_mcu_command("fan_speed", tuya_speed, manufacturer)
                self._send_mcu_command("fan_switch", True, manufacturer)

            elif attr_name == "fan_switch":
                self._send_mcu_command("fan_switch", bool(val), manufacturer)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Synchronize standard Fan cluster attributes when Tuya DPs update."""
        super()._update_attribute(attrid, value)

        if attrid == self.AttributeDefs.fan_switch.id:
            if not value:
                super()._update_attribute(
                    Fan.AttributeDefs.fan_mode.id, Fan.FanMode.Off
                )
            else:
                current_speed = self.get(
                    self.AttributeDefs.fan_speed.id, TuyaSpeedFan.mid
                )
                super()._update_attribute(
                    Fan.AttributeDefs.fan_mode.id,
                    TUYA_SPEED_TO_FAN_MODE.get(
                        TuyaSpeedFan(current_speed), Fan.FanMode.Medium
                    ),
                )

        elif attrid == self.AttributeDefs.fan_speed.id:
            is_on = self.get(self.AttributeDefs.fan_switch.id, True)
            if is_on:
                super()._update_attribute(
                    Fan.AttributeDefs.fan_mode.id,
                    TUYA_SPEED_TO_FAN_MODE.get(TuyaSpeedFan(value), Fan.FanMode.Medium),
                )


class TuyaElectricalMeasurement(TuyaAttributesCluster, ElectricalMeasurement):
    """Tuya custom Electrical Measurement cluster using TuyaAttributesCluster."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init cluster and mark unused attributes as unsupported."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            ElectricalMeasurement.AttributeDefs.ac_frequency.id
        )
        self.add_unsupported_attribute(
            ElectricalMeasurement.AttributeDefs.power_factor.id
        )
        self.add_unsupported_attribute(
            ElectricalMeasurement.AttributeDefs.apparent_power.id
        )


# Fan and Light Switch Quirk
(
    TuyaQuirkBuilder("_TZE204_ft3laxaa", "TS0601")
    .adds(TuyaFanCluster)
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaFanCluster.ep_attribute,
        attribute_name="fan_switch",
    )
    .tuya_number(
        dp_id=2,
        attribute_name="fan_timer",
        translation_key="fan_timer",
        type=t.uint32_t,
        fallback_name="Fan Timer",
        min_value=0,
        max_value=600,
        step=1,
        multiplier=1 / 60,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.STANDARD,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaFanCluster.ep_attribute,
        attribute_name="fan_speed",
    )
    .enum(
        attribute_name=TuyaFanCluster.AttributeDefs.fan_speed.name,
        enum_class=TuyaSpeedFan,
        cluster_id=Fan.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.STANDARD,
        translation_key="fan_speed",
        fallback_name="Fan Speed",
    )
    .tuya_onoff(dp_id=5)
    .tuya_number(
        dp_id=7,
        attribute_name="switch_1_timer",
        translation_key="switch_1_timer",
        type=t.uint32_t,
        fallback_name="Switch 1 Timer",
        min_value=0,
        max_value=600,
        step=1,
        multiplier=1 / 60,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=11,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
        entity_type=EntityType.CONFIG,
    )
    .tuya_enum(
        dp_id=12,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
        entity_type=EntityType.CONFIG,
    )
    .tuya_switch(
        dp_id=13,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
        entity_type=EntityType.CONFIG,
    )
    .adds(TuyaElectricalMeasurement)
    .tuya_dp(
        dp_id=102,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_current",
    )
    .tuya_dp(
        dp_id=103,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="rms_voltage",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=TuyaElectricalMeasurement.ep_attribute,
        attribute_name="active_power",
    )
    .skip_configuration()
    .add_to_registry()
)
