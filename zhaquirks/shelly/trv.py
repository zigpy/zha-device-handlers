"""Device handler for Shelly BLU TRV."""

from __future__ import annotations

from zigpy import types
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import PERCENTAGE, QuirkBuilder, ReportingConfig
from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE


class ShellyTRVModeCluster(CustomCluster):
    """Shelly manufacturer-specific TRV Mode cluster."""

    cluster_id = 0xFC24
    name = "Shelly TRV Mode"
    ep_attribute = "shelly_trv_mode"

    class AttributeDefs(BaseAttributeDefs):
        """TRV mode cluster attribute definitions."""

        trv_mode = ZCLAttributeDef(
            id=0x0000,
            type=types.uint8_t,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        position = ZCLAttributeDef(
            id=0x0001,
            type=types.uint8_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """TRV mode command definitions."""

        calibrate = ZCLCommandDef(
            id=0x0000,
            schema={},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("Shelly", "BLU TRV")
    .replaces(ShellyTRVModeCluster)
    .number(
        attribute_name=ShellyTRVModeCluster.AttributeDefs.position.name,
        cluster_id=ShellyTRVModeCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=300, reportable_change=1
        ),
        translation_key="valve_position",
        fallback_name="Valve position",
    )
    .switch(
        attribute_name=ShellyTRVModeCluster.AttributeDefs.trv_mode.name,
        cluster_id=ShellyTRVModeCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="manual_mode",
        fallback_name="Manual mode",
    )
    .command_button(
        command_name=ShellyTRVModeCluster.ServerCommandDefs.calibrate.name,
        cluster_id=ShellyTRVModeCluster.cluster_id,
        translation_key="calibrate_valve",
        fallback_name="Calibrate valve",
    )
    .add_to_registry()
)
