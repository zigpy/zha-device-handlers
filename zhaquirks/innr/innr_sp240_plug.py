"""Innr SP 240 and SP 242 plugs.

The SP 242 is the UK version of the SP 240, with the same clusters and firmware
versions.
"""

from zigpy.zcl import ReportingConfig
from zigpy.zcl.clusters.general import LevelControl
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import Status, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.innr import MeteringClusterInnrNew, MeteringClusterInnrOld


class InnrCluster(CustomCluster):
    """Innr manufacturer specific cluster."""

    cluster_id = 0xE001


class ElectricalMeasurementClusterSP240(CustomCluster, ElectricalMeasurement):
    """Electrical measurement cluster that does not report the AC scaling constants.

    The plug only has eight attribute reporting slots. Its AC multiplier and divisor
    attributes are constants, but reporting them would take up to six of those slots
    and leave none for energy, current and voltage. They are still read as usual.
    """

    _UNREPORTED_ATTRIBUTE_IDS = frozenset(
        {
            ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id,
            ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id,
            ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id,
            ElectricalMeasurement.AttributeDefs.ac_current_divisor.id,
            ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id,
            ElectricalMeasurement.AttributeDefs.ac_power_divisor.id,
        }
    )

    async def configure_reporting_multiple(
        self, config: dict[ZCLAttributeDef, ReportingConfig]
    ) -> dict[ZCLAttributeDef, Status]:
        """Configure reporting, skipping the AC scaling constants."""
        to_configure = {
            attr_def: reporting_config
            for attr_def, reporting_config in config.items()
            if attr_def.id not in self._UNREPORTED_ATTRIBUTE_IDS
        }
        results = (
            await super().configure_reporting_multiple(to_configure)
            if to_configure
            else {}
        )
        return {
            attr_def: (
                results[attr_def]
                if attr_def in to_configure
                else Status.UNREPORTABLE_ATTRIBUTE
            )
            for attr_def in config
        }


(
    QuirkBuilder(manufacturer="innr", model="SP 240")
    .applies_to(manufacturer="innr", model="SP 242")
    # Firmware version 421410437 fixed the divisor and multiplier bug,
    # so only apply this quirk to versions older than that (max_version is exclusive).
    .firmware_version_filter(max_version=0x191B3685, allow_missing=False)
    # the plug cannot dim, so don't bind, configure reporting for or expose LevelControl
    .removes(LevelControl.cluster_id, endpoint_id=1)
    .replaces(MeteringClusterInnrOld, endpoint_id=1)
    .replaces(ElectricalMeasurementClusterSP240, endpoint_id=1)
    .replaces(InnrCluster, endpoint_id=1)
    .add_to_registry()
)

(
    QuirkBuilder(manufacturer="innr", model="SP 240")
    .applies_to(manufacturer="innr", model="SP 242")
    # Firmware version 421410437 fixed the divisor and multiplier bug,
    # so apply this quirk to that and newer versions to force correct new values,
    # in case the old quirk persisted the old values into the database.
    .firmware_version_filter(min_version=0x191B3685, allow_missing=True)
    # the plug cannot dim, so don't bind, configure reporting for or expose LevelControl
    .removes(LevelControl.cluster_id, endpoint_id=1)
    .replaces(MeteringClusterInnrNew, endpoint_id=1)
    .replaces(ElectricalMeasurementClusterSP240, endpoint_id=1)
    .replaces(InnrCluster, endpoint_id=1)
    .add_to_registry()
)
