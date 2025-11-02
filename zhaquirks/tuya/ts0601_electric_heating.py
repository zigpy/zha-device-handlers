"""Map from manufacturer to standard clusters for electric heating thermostats."""

from typing import Final, Optional, Union

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TUYA_MCU_COMMAND,
    NoManufacturerCluster,
    TuyaLocalCluster,
    TuyaManufClusterAttributes,
    TuyaThermostat,
    TuyaThermostatCluster,
    TuyaUserInterfaceCluster,
)
from zhaquirks.tuya.mcu import TuyaClusterData

# info from https://github.com/zigpy/zha-device-handlers/pull/538#issuecomment-723334124
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/fromZigbee.js#L239
# and https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/converters/common.js#L113
MOESBHT_TARGET_TEMP_ATTR = 0x0210  # [0,0,0,21] target room temp (degree)
MOESBHT_TEMPERATURE_ATTR = 0x0218  # [0,0,0,200] current room temp (decidegree)
MOESBHT_SCHEDULE_MODE_ATTR = 0x0403  # [1] false [0] true   /!\ inverted
MOESBHT_MANUAL_MODE_ATTR = 0x0402  # [1] false [0] true /!\ inverted
MOESBHT_ENABLED_ATTR = 0x0101  # [0] off [1] on
MOESBHT_RUNNING_MODE_ATTR = 0x0424  # [1] idle [0] heating /!\ inverted
MOESBHT_CHILD_LOCK_ATTR = 0x0128  # [0] unlocked [1] child-locked

# MoesBHT6 attributes (variant with single mode attribute)
MOESBHT6_TARGET_TEMP_ATTR = 0x0210  # [0,0,0,21] target room temp (degree)
MOESBHT6_TEMPERATURE_ATTR = 0x0218  # [0,0,0,200] current room temp (decidegree)
MOESBHT6_MODE_ATTR = 0x0402  # [0] manual [1] scheduled
MOESBHT6_ENABLED_ATTR = 0x0101  # [0] off [1] on
MOESBHT6_RUNNING_MODE_ATTR = 0x0424  # [1] idle [0] heating
MOESBHT6_RUNNING_STATE_ATTR = 0x0424  # [1] idle [0] heating
MOESBHT6_CHILD_LOCK_ATTR = 0x0128  # [0] unlocked [1] child-locked


class MoesBHTManufCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of some electric heating thermostats."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions."""

        target_temperature: Final = ZCLAttributeDef(
            id=MOESBHT_TARGET_TEMP_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        temperature: Final = ZCLAttributeDef(
            id=MOESBHT_TEMPERATURE_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        schedule_mode: Final = ZCLAttributeDef(
            id=MOESBHT_SCHEDULE_MODE_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        manual_mode: Final = ZCLAttributeDef(
            id=MOESBHT_MANUAL_MODE_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        enabled: Final = ZCLAttributeDef(
            id=MOESBHT_ENABLED_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        running_mode: Final = ZCLAttributeDef(
            id=MOESBHT_RUNNING_MODE_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        child_lock: Final = ZCLAttributeDef(
            id=MOESBHT_CHILD_LOCK_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MOESBHT_TARGET_TEMP_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "occupied_heating_setpoint",
                value * 100,  # degree to centidegree
            )
        elif attrid == MOESBHT_TEMPERATURE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "local_temperature",
                value * 10,  # decidegree to centidegree
            )
        elif attrid == MOESBHT_SCHEDULE_MODE_ATTR:
            if value == 0:  # value is inverted
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "scheduled"
                )
        elif attrid == MOESBHT_MANUAL_MODE_ATTR:
            if value == 0:  # value is inverted
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "manual"
                )
        elif attrid == MOESBHT_ENABLED_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("enabled_change", value)
        elif attrid == MOESBHT_RUNNING_MODE_ATTR:
            # value is inverted
            self.endpoint.device.thermostat_bus.listener_event(
                "state_change", 1 - value
            )
        elif attrid == MOESBHT_CHILD_LOCK_ATTR:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)


class MoesBHTThermostat(TuyaThermostatCluster):
    """Thermostat cluster for some electric heating controllers."""

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to degree
            return {MOESBHT_TARGET_TEMP_ATTR: round(value / 100)}
        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {MOESBHT_ENABLED_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {MOESBHT_ENABLED_ATTR: 1}
            self.error("Unsupported value for SystemMode")
        elif attribute == "programing_oper_mode":
            # values are inverted
            if value == self.ProgrammingOperationMode.Simple:
                return {MOESBHT_MANUAL_MODE_ATTR: 0, MOESBHT_SCHEDULE_MODE_ATTR: 1}
            if value == self.ProgrammingOperationMode.Schedule_programming_mode:
                return {MOESBHT_MANUAL_MODE_ATTR: 1, MOESBHT_SCHEDULE_MODE_ATTR: 0}
            self.error("Unsupported value for ProgrammingOperationMode")

        return super().map_attribute(attribute, value)

    def program_change(self, mode):
        """Programming mode change."""
        if mode == "manual":
            value = self.ProgrammingOperationMode.Simple
        else:
            value = self.ProgrammingOperationMode.Schedule_programming_mode

        self._update_attribute(
            self.attributes_by_name["programing_oper_mode"].id, value
        )

    def enabled_change(self, value):
        """System mode change."""
        if value == 0:
            mode = self.SystemMode.Off
        else:
            mode = self.SystemMode.Heat
        self._update_attribute(self.attributes_by_name["system_mode"].id, mode)


class MoesBHTUserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for tuya electric heating thermostats."""

    _CHILD_LOCK_ATTR = MOESBHT_CHILD_LOCK_ATTR


class MoesBHT(TuyaThermostat):
    """Tuya thermostat for devices like the Moes BHT-002GCLZB valve and BHT-003GBLZB Electric floor heating."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184],
        #  output_clusters=[10, 25]
        MODELS_INFO: [
            ("_TZE200_aoclfnxz", "TS0601"),
            ("_TZE200_2ekuz3dz", "TS0601"),
            ("_TZE200_ye5jkfsb", "TS0601"),
            ("_TZE200_u9bfwha0", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesBHTManufCluster,
                    MoesBHTThermostat,
                    MoesBHTUserInterface,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class MoesBHT6ManufCluster(
    TuyaManufClusterAttributes, NoManufacturerCluster, TuyaLocalCluster
):
    """Manufacturer Specific Cluster for MoesBHT6 variant thermostats."""

    class AttributeDefs(TuyaManufClusterAttributes.AttributeDefs):
        """Attribute definitions."""

        target_temperature: Final = ZCLAttributeDef(
            id=MOESBHT6_TARGET_TEMP_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        temperature: Final = ZCLAttributeDef(
            id=MOESBHT6_TEMPERATURE_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        system_mode: Final = ZCLAttributeDef(
            id=MOESBHT6_MODE_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        enabled: Final = ZCLAttributeDef(
            id=MOESBHT6_ENABLED_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        running_mode: Final = ZCLAttributeDef(
            id=MOESBHT6_RUNNING_MODE_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )
        running_state: Final = ZCLAttributeDef(
            id=MOESBHT6_RUNNING_STATE_ATTR,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        child_lock: Final = ZCLAttributeDef(
            id=MOESBHT6_CHILD_LOCK_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        self.debug(
            "Sending Tuya Cluster Command. Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )

        # (off, on)
        if command_id in (0x0000, 0x0001):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr="enabled",
                attr_value=command_id,
                expect_reply=expect_reply,
                manufacturer=-1,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MOESBHT6_TARGET_TEMP_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "occupied_heating_setpoint",
                value * 100,  # degree to centidegree
            )
        elif attrid == MOESBHT6_TEMPERATURE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "temperature_change",
                "local_temperature",
                value * 10,  # decidegree to centidegree
            )
        elif attrid == MOESBHT6_MODE_ATTR:
            if value == 0:  # manual
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "manual"
                )
            elif value == 1:  # scheduled
                self.endpoint.device.thermostat_bus.listener_event(
                    "program_change", "scheduled"
                )
        elif attrid == MOESBHT6_ENABLED_ATTR:
            self.endpoint.device.thermostat_bus.listener_event("enabled_change", value)
        elif attrid in (MOESBHT6_RUNNING_MODE_ATTR, MOESBHT6_RUNNING_STATE_ATTR):
            self.endpoint.device.thermostat_bus.listener_event("running_change", value)
        elif attrid == MOESBHT6_CHILD_LOCK_ATTR:
            self.endpoint.device.ui_bus.listener_event("child_lock_change", value)


class MoesBHT6Thermostat(TuyaThermostatCluster):
    """Thermostat cluster for MoesBHT6 variant electric heating controllers."""

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""

        if attribute == "occupied_heating_setpoint":
            # centidegree to degree
            return {MOESBHT6_TARGET_TEMP_ATTR: round(value / 100)}
        if attribute == "system_mode":
            if value == self.SystemMode.Off:
                return {MOESBHT6_ENABLED_ATTR: 0}
            if value == self.SystemMode.Heat:
                return {MOESBHT6_ENABLED_ATTR: 1}
            self.error("Unsupported value for SystemMode")
        elif attribute == "programing_oper_mode":
            if value == self.ProgrammingOperationMode.Simple:
                return {MOESBHT6_MODE_ATTR: 0}
            if value == self.ProgrammingOperationMode.Schedule_programming_mode:
                return {MOESBHT6_MODE_ATTR: 1}
            self.error("Unsupported value for ProgrammingOperationMode")
        elif attribute == "running_state":
            if value == self.RunningState.Idle:
                return {MOESBHT6_RUNNING_STATE_ATTR: 1}
            if value == self.RunningState.Heat_State_On:
                return {MOESBHT6_RUNNING_STATE_ATTR: 0}
            self.error("Unsupported value for RunningState")
        elif attribute == "running_mode":
            if value == self.RunningMode.Off:
                return {MOESBHT6_RUNNING_MODE_ATTR: 1}
            if value == self.RunningMode.Heat:
                return {MOESBHT6_RUNNING_MODE_ATTR: 0}
            self.error("Unsupported value for RunningMode")

        return super().map_attribute(attribute, value)

    def program_change(self, mode):
        """Programming mode change."""
        if mode == "manual":
            value = self.ProgrammingOperationMode.Simple
        else:
            value = self.ProgrammingOperationMode.Schedule_programming_mode

        self._update_attribute(
            self.attributes_by_name["programing_oper_mode"].id, value
        )

    def enabled_change(self, value):
        """System mode change."""
        if value == 0:
            mode = self.SystemMode.Off
        else:
            mode = self.SystemMode.Heat
        self._update_attribute(self.attributes_by_name["system_mode"].id, mode)

    def running_change(self, value):
        """Change running state."""
        if value == 0:
            mode = self.RunningMode.Heat
            state = self.RunningState.Heat_State_On
        else:
            mode = self.RunningMode.Off
            state = self.RunningState.Idle
        self._update_attribute(self.attributes_by_name["running_mode"].id, mode)
        self._update_attribute(self.attributes_by_name["running_state"].id, state)


class MoesBHT6UserInterface(TuyaUserInterfaceCluster):
    """HVAC User interface cluster for MoesBHT6 variant thermostats."""

    _CHILD_LOCK_ATTR = MOESBHT6_CHILD_LOCK_ATTR


class MoesBHT6(TuyaThermostat):
    """Tuya thermostat for devices like the Moes BHT-006GBZB Electric floor heating."""

    signature = {
        MODELS_INFO: [
            ("_TZE204_u9bfwha0", "TS0601"),
        ],
        ENDPOINTS: {
            #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184],
            #  output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufClusterAttributes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MoesBHT6ManufCluster,
                    MoesBHT6Thermostat,
                    MoesBHT6UserInterface,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
