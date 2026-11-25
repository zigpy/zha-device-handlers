"""Zehnder thermostats."""

from zha.application.helpers import write_attributes_safe
from zha.application.platforms.climate import Thermostat
from zha.application.platforms.climate.const import HVACMode
import zigpy.device
from zigpy.zcl.clusters.hvac import SystemMode, Thermostat as ThermostatCluster

from zhaquirks.builder import QuirkBuilder


class ZehnderThermostat(Thermostat):
    """Zehnder thermostat, which heats in the auto system mode."""

    HVAC_MODE_2_SYSTEM = {
        HVACMode.OFF: SystemMode.Off,
        HVACMode.HEAT: SystemMode.Auto,
    }

    SYSTEM_MODE_2_HVAC = {
        SystemMode.Off: HVACMode.OFF,
        SystemMode.Auto: HVACMode.HEAT,
    }

    hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target operation mode."""
        if hvac_mode not in self.hvac_modes:
            self.warning(
                "can't set '%s' mode. Supported modes are: %s",
                hvac_mode,
                self.hvac_modes,
            )
            return

        await write_attributes_safe(
            self._cluster,
            {
                ThermostatCluster.AttributeDefs.system_mode.name: (
                    self.HVAC_MODE_2_SYSTEM[hvac_mode]
                )
            },
        )
        self.maybe_emit_state_changed_event()

    @property
    def current_temperature(self):
        """Force no current temperature."""
        return None

    @property
    def system_mode_string(self) -> str | None:
        """Return a formatted system mode string."""
        if self.hvac_mode is None:
            return None
        system_mode = self.SYSTEM_MODE_2_HVAC.get(self._system_mode, "unknown")
        return f"[{self._system_mode}]/{system_mode}"

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return HVAC operation mode."""
        return self.SYSTEM_MODE_2_HVAC.get(self._system_mode)


def has_thermostat(device: zigpy.device.Device) -> bool:
    """Return whether the device has a thermostat cluster."""
    return any(
        ThermostatCluster.cluster_id in endpoint.in_clusters
        for endpoint_id, endpoint in device.endpoints.items()
        if endpoint_id != 0
    )


(
    # The manufacturer name is padded with spaces on some devices
    QuirkBuilder("ZEHNDER GROUP VAUX ANDIGNY      ", None)
    .applies_to("ZEHNDER GROUP VAUX ANDIGNY", None)
    .filter(has_thermostat)
    .replaces_entity(
        Thermostat,
        ZehnderThermostat,
        cluster_id=ThermostatCluster.cluster_id,
    )
    .add_to_registry()
)
