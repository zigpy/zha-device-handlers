"""Quirk for Knockautx WTFHA025 thermostat using classic architecture.
It is a wall-mounted thermostat with screen and main power.
It acts as a Zigbee router.
This Quirk manage basic information : temp, target temp, mode Off/Manual/Auto, heating status.
Unfortunately :
  - I'm not able to fetch schedule nor redefine it. Anyway I'll use HA scheduler.
  - Enabling auto mode in HA interface means faking a heat+cool system.
    If you want to hide Cooling mode you will loose "auto" mode.
    To do so use value "Heating_Only" instead of "Cooling_and_Heating" in the line :
          _CONSTANT_ATTRIBUTES = {0x001B: Thermostat.ControlSequenceOfOperation.Cooling_and_Heating }
"""

import logging
from typing import Final
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef
import zigpy.types as t

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufClusterAttributes,
    TuyaThermostat,
    TuyaThermostatCluster,
    TuyaUserInterfaceCluster,
)

LOGGER = logging.getLogger(__name__)

# Mapping identified Datapoints
KNOCKAUTX_STATE_ATTR = 0x017D       # DP 1   : System On/Off
KNOCKAUTX_HEATING_ATTR = 0x0166     # DP 102 : Heat State (0=Idle, 1=Heating)
KNOCKAUTX_TARGET_TEMP_ATTR = 0x027E # DP 126 : Target Temp
KNOCKAUTX_TEMPERATURE_ATTR = 0x027F # DP 127 : Local Temp
KNOCKAUTX_MODE_ATTR = 0x0480        # DP 128 : Mode (Manual=0 / Auto=1)


class KnockautxWTFHA025BasicCluster(Basic):
    """Cluster Basic avec attributs spécifiques non identifiés."""

    attributes = Basic.attributes.copy()
    attributes.update(
        {
            0xFFE2: ("manufacturer_specific_ffe2", t.uint8_t, True),
            0xFFE4: ("manufacturer_specific_ffe4", t.uint8_t, True),
        }
    )


class KnockautxWTFHA025ManufCluster(TuyaManufClusterAttributes):
    """Specific cluster for Knockautx thermostat."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions based on DPs."""

        system_on_off: Final = ZCLAttributeDef(
            id=KNOCKAUTX_STATE_ATTR, type=t.Bool, is_manufacturer_specific=True
        )
        heat_state: Final = ZCLAttributeDef(
            id=KNOCKAUTX_HEATING_ATTR,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        target_temperature: Final = ZCLAttributeDef(
            id=KNOCKAUTX_TARGET_TEMP_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        temperature: Final = ZCLAttributeDef(
            id=KNOCKAUTX_TEMPERATURE_ATTR,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        system_mode: Final = ZCLAttributeDef(
            id=KNOCKAUTX_MODE_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )

    dp_to_attribute: Final = {
        1: KNOCKAUTX_STATE_ATTR,
        102: KNOCKAUTX_HEATING_ATTR,
        126: KNOCKAUTX_TARGET_TEMP_ATTR,
        127: KNOCKAUTX_TEMPERATURE_ATTR,
        128: KNOCKAUTX_MODE_ATTR,
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        # Temperature conversion:
        # Tuya sends decidedrees (e.g., 200 for 20.0°C).
        # ZCL / Home Assistant expects centidegrees (e.g., 2000 for 20.00°C).
        # Multiply by 10.
        if attrid == KNOCKAUTX_TARGET_TEMP_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change", "occupied_heating_setpoint", value * 10
            )
        elif attrid == KNOCKAUTX_TEMPERATURE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change", "local_temperature", value * 10
            )
        elif attrid == KNOCKAUTX_HEATING_ATTR:
            # KNOCKAUTX_HEATING_ATTR = 0 → Idle (0)
            # KNOCKAUTX_HEATING_ATTR = 1 → Running (1)
            running_state = value  # Direct mapping!

            LOGGER.info(f"🔥 Heating state: {value} ({'Active' if value else 'Idle'})")

            try:
                thermostat_cluster = self.endpoint.in_clusters[Thermostat.cluster_id]
                thermostat_cluster._update_attribute(0x0029, running_state)
            except KeyError:
                LOGGER.warning("Thermostat cluster not found for heating state update")
        elif attrid == KNOCKAUTX_MODE_ATTR:
            # Check if system is on (DP 1). If off, ignore visual mode change.
            # However, Tuya sometimes sends updates separately.
            # Get current On/Off state.
            on_off_status = (
                self.endpoint.device.endpoints[1]
                .in_clusters[TuyaManufClusterAttributes.cluster_id]
                .get(KNOCKAUTX_STATE_ATTR)
            )

            # If state is unknown (None), assume On to update the mode, otherwise check.
            if on_off_status is not False:  # True ou None
                if value == 0:
                    self.endpoint.device.thermostat_bus.listener_event(
                        "mode_change", TuyaThermostatCluster.SystemMode.Heat
                    )
                elif value == 1:
                    self.endpoint.device.thermostat_bus.listener_event(
                        "mode_change", TuyaThermostatCluster.SystemMode.Auto
                    )
                else:
                    # TODO find a way to alert admin regarding unforseen value from the device)
                    pass
        elif attrid == KNOCKAUTX_STATE_ATTR:
            if value == 0:  # Turn off
                self.endpoint.device.thermostat_bus.listener_event(
                    "mode_change", TuyaThermostatCluster.SystemMode.Off
                )
            else:
                # Turn on (Value = 1)
                # We need to restore the correct mode.
                # Check mode value (DP 128)
                try:
                    mode_val = (
                        self.endpoint.device.endpoints[1]
                        .in_clusters[TuyaManufClusterAttributes.cluster_id]
                        .get(KNOCKAUTX_MODE_ATTR)
                    )
                except KeyError:
                    # TODO find a way to alert admin regarding unforseen situation
                    mode_val = 0  # Default to manual if unknown

                if mode_val == 1:
                    self.endpoint.device.thermostat_bus.listener_event(
                        "mode_change", TuyaThermostatCluster.SystemMode.Auto
                    )
                else:
                    # Default or if 0 -> manual
                    self.endpoint.device.thermostat_bus.listener_event(
                        "mode_change", TuyaThermostatCluster.SystemMode.Heat
                    )


class KnockautxWTFHA025ThermostatCluster(TuyaThermostatCluster):
    """Translator for outgoing commands (HA -> Thermostat)."""

    # Define constant attributes to force HA to understand the device type.
    # 0x001B is ControlSequenceOfOperation.
    #      2 = Thermostat.ControlSequenceOfOperation.Heating_Only.
    #      4 = Thermostat.ControlSequenceOfOperation.Cooling_and_Heating
    # 4 / Cooling_and_Heating displays the cooling mode, but it is the only way to show the Auto mode in HA
    _CONSTANT_ATTRIBUTES = {
        0x001B: Thermostat.ControlSequenceOfOperation.Cooling_and_Heating
    }

    def map_attribute(self, attribute, value):
        if attribute == "occupied_heating_setpoint":
            # Temperature conversion:
            # Tuya expects decidedrees (e.g., 200 for 20.0°C).
            # ZCL sends centidegrees (e.g., 2000 for 20.00°C).
            # Divide by 10.
            return {KNOCKAUTX_TARGET_TEMP_ATTR: round(value / 10)}
        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {KNOCKAUTX_STATE_ATTR: 0}  # Turn off via DP 1

            # If not Off, ensure thermostat is On (DP 1 = 1)
            # And send specific mode (Manual=0, Auto=1)
            if value == self.SystemMode.Auto:
                return {KNOCKAUTX_STATE_ATTR: 1, KNOCKAUTX_MODE_ATTR: 1}
            elif value == self.SystemMode.Heat:
                return {KNOCKAUTX_STATE_ATTR: 1, KNOCKAUTX_MODE_ATTR: 0}
        return super().map_attribute(attribute, value)

    def mode_change(self, value):
        """Mise à jour de l'état du mode dans HA."""
        self._update_attribute(self.attributes_by_name["system_mode"].id, value)


class KnockautxWTFHA025(TuyaThermostat):
    """Appareil Knockautx WTFHA025."""

    signature = {
        MODELS_INFO: [("_TZE200_kafooqvr", "TS0601")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0051,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    KnockautxWTFHA025BasicCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    KnockautxWTFHA025ManufCluster,
                    KnockautxWTFHA025ThermostatCluster,
                    TuyaUserInterfaceCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
