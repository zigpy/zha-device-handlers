"""BITUO TECHNIK SPM01X single-phase energy meter."""  # codespell:ignore technik

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef


class SPM01ElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """ElectricalMeasurement cluster for the single-phase SPM01X.

    The SPM01X is a single-phase meter, but its firmware reports the Phase B/C
    measurement attributes with placeholder values (0 or -1). That populates
    ZHA's attribute cache and causes phantom "Phase B/C" sensors to be created.
    """

    PHANTOM_PHASE_BC_ATTRIBUTES = frozenset(
        {
            ElectricalMeasurement.AttributeDefs.active_power_ph_b.id,
            ElectricalMeasurement.AttributeDefs.active_power_ph_c.id,
            ElectricalMeasurement.AttributeDefs.rms_current_ph_b.id,
            ElectricalMeasurement.AttributeDefs.rms_current_ph_c.id,
            ElectricalMeasurement.AttributeDefs.rms_voltage_ph_b.id,
            ElectricalMeasurement.AttributeDefs.rms_voltage_ph_c.id,
            ElectricalMeasurement.AttributeDefs.power_factor_ph_b.id,
            ElectricalMeasurement.AttributeDefs.power_factor_ph_c.id,
        }
    )

    def _update_attribute(self, attrid, value):
        """Ignore reports/restores for the phantom Phase B/C attributes."""
        attr_id = attrid.id if isinstance(attrid, ZCLAttributeDef) else attrid
        if attr_id in self.PHANTOM_PHASE_BC_ATTRIBUTES:
            return
        super()._update_attribute(attrid, value)


(
    QuirkBuilder("BITUO TECHNIK", "SPM01X")  # codespell:ignore technik
    .replaces(SPM01ElectricalMeasurement)
    # The On/Off cluster does not control a relay: command "on" (0x01) resets
    # the accumulated energy to zero. Hide the entities ZHA creates by default
    # for this cluster (the switch, and the "opening" binary sensor)
    # and expose a button instead.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        # Avoid preventing the quirk-defined reset button from being created
        function=lambda entity: (
            getattr(entity, "translation_key", None) != "reset_energy"
        ),
    )
    .command_button(
        OnOff.ServerCommandDefs.on.name,
        OnOff.cluster_id,
        entity_type=EntityType.CONFIG,
        initially_disabled=True,
        translation_key="reset_energy",
        fallback_name="Reset energy",
    )
    .add_to_registry()
)
