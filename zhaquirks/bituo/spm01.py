"""BITUO TECHNIK SPM01X single-phase energy meter."""  # codespell:ignore technik

from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class SPM01ElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """ElectricalMeasurement cluster for the single-phase SPM01X.

    The SPM01X is a single-phase meter, but its firmware reports the Phase B/C
    and total measurement attributes with placeholder values (0, -1, and
    0xFFFF). That populates ZHA's attribute cache and causes phantom "Phase B/C"
    and "Total power" sensors to be created.
    """

    PHANTOM_ATTRIBUTES = frozenset(
        {
            ElectricalMeasurement.AttributeDefs.total_active_power.id,
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

    def is_attribute_unsupported(self, attr):
        """Report the phantom attributes as always unsupported."""
        if self.find_attribute(attr).id in self.PHANTOM_ATTRIBUTES:
            return True
        return super().is_attribute_unsupported(attr)


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
