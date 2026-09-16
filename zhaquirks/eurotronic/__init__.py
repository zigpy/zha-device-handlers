"""Eurotronic devices."""

from typing import Final

from zha.application.helpers import write_attributes_safe
from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.climate import Thermostat as ThermostatEntity
from zha.application.platforms.climate.const import HVACMode
from zha.zigbee.cluster_config import ReportingConfig
import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.clusters import CustomCluster

EUROTRONIC = "Eurotronic"

MANUFACTURER = 0x1037  # 4151


class HostFlags(t.bitmap24):
    """Manufacturer-specific TRV flags."""

    # unknown, defaults to 1
    Mirror_Screen = 0b00000010
    Boost = 0b00000100
    # unknown
    Clear_Off_Mode = 0b00010000
    # reported back as Clear_Off_Mode
    Set_Off_Mode = 0b00100000
    # unknown
    Child_Lock = 0b10000000


class ThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster with the manufacturer-specific attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        trv_mode: Final = ZCLAttributeDef(
            id=0x4000, type=t.enum8, manufacturer_code=MANUFACTURER
        )
        set_valve_position: Final = ZCLAttributeDef(
            id=0x4001, type=t.uint8_t, manufacturer_code=MANUFACTURER
        )
        errors: Final = ZCLAttributeDef(
            id=0x4002, type=t.uint8_t, manufacturer_code=MANUFACTURER
        )
        current_temperature_setpoint: Final = ZCLAttributeDef(
            id=0x4003, type=t.int16s, manufacturer_code=MANUFACTURER
        )
        host_flags: Final = ZCLAttributeDef(
            id=0x4008, type=HostFlags, manufacturer_code=MANUFACTURER
        )


class EurotronicThermostat(ThermostatEntity):
    """Spirit Zigbee thermostat.

    The device does not implement `system_mode`, on/off lives in `host_flags`. It
    reports a bogus `occupied_heating_setpoint`, the real setpoint is
    `current_temperature_setpoint`. Writes to `occupied_heating_setpoint` do work.
    """

    _server_cluster_config = {
        Thermostat.cluster_id: ClusterConfig(
            bind=True,
            attributes={
                Thermostat.AttributeDefs.local_temperature: AttrConfig(
                    read_on_startup=True,
                    reporting=ReportingConfig(
                        min_interval=30, max_interval=900, reportable_change=25
                    ),
                ),
                Thermostat.AttributeDefs.pi_heating_demand: AttrConfig(
                    read_on_startup=True,
                    reporting=ReportingConfig(
                        min_interval=30, max_interval=900, reportable_change=1
                    ),
                ),
                ThermostatCluster.AttributeDefs.current_temperature_setpoint: AttrConfig(
                    read_on_startup=True,
                    reporting=ReportingConfig(
                        min_interval=30, max_interval=900, reportable_change=25
                    ),
                ),
                ThermostatCluster.AttributeDefs.host_flags: AttrConfig(
                    read_on_startup=True,
                    reporting=ReportingConfig(
                        min_interval=0, max_interval=900, reportable_change=1
                    ),
                ),
            },
        )
    }

    @property
    def _host_flags(self) -> HostFlags | None:
        return self._cluster.get(ThermostatCluster.AttributeDefs.host_flags.name)

    @property
    def _occupied_heating_setpoint(self) -> int | None:
        return self._cluster.get(
            ThermostatCluster.AttributeDefs.current_temperature_setpoint.name
        )

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC operation modes."""
        return [HVACMode.OFF, HVACMode.HEAT]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return HVAC operation mode."""
        if self._host_flags is None:
            return None

        if self._host_flags & HostFlags.Clear_Off_Mode:
            return HVACMode.OFF

        return HVACMode.HEAT

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target operation mode."""
        flag = (
            HostFlags.Set_Off_Mode
            if hvac_mode == HVACMode.OFF
            else HostFlags.Clear_Off_Mode
        )

        host_flags = self._host_flags if self._host_flags is not None else HostFlags(1)

        await write_attributes_safe(
            self._cluster,
            {ThermostatCluster.AttributeDefs.host_flags.name: host_flags | flag},
        )
        self.maybe_emit_state_changed_event()
