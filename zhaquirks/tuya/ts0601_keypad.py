"""Tuya TS0601 wireless Zigbee keypad (MS-K1AZ / Immax NEO 07505L).

Alarm keypad that communicates via Tuya MCU DPs on cluster 0xEF00.
Translates Tuya arm/disarm/SOS datapoints into ZHA events and IAS ACE
cluster commands for alarm control panel integration (e.g. Alarmo).

Manual: https://manuals.plus/immax/07505l-neo-smart-keypad-manual

Tuya DPs:
  DP 3:   battery_percentage (int, 0-100, read only)
  DP 24:  anti-remove/tamper alarm (bool, read only → emergency + IAS Zone)
  DP 26:  disarmed (enum, read only → disarm event)
  DP 27:  armed away (enum, read only → arm_away event)
  DP 28:  armed home (enum, read only → arm_home event)
  DP 29:  SOS trigger (enum, read only → panic event)
  DP 103: arm delay time (int, 0-180, read only via Zigbee)
  DP 104: keypad beeps (bool, read only via Zigbee)
  DP 105: quick SOS (bool, read only via Zigbee)
  DP 106: quick disarm (bool, read only via Zigbee)
  DP 107: quick arm (bool, read only via Zigbee)
  DP 108: admin code (string, read only)
  DP 109: user code (string, read only)
  DP 111: arm delay beeps (bool, read only via Zigbee)
  DP 112: unknown, always 0, sent with every arm/disarm event

Known limitations:
  - PIN codes (DP 108/109) are read-only via Zigbee; change via keypad
    settings mode only (admin code + # → 38/39 + new code + #).
  - Keypad settings (DP 103-107, 111) are reported at join/wake but not
    when changed on the keypad. They are stored as MCU cluster attributes
    (visible in ZHA cluster management) but not exposed as HA entities.
    TuyaQuirkBuilder (v2) cannot expose these because it overwrites custom
    data_point_handlers and has no mechanism for firing ZHA events from DPs.
  - The keypad does not send "arming/pending" events during arm delay;
    arm delay must be handled by HA/Alarmo, not the keypad.
  - DP 112 is sent with every arm/disarm event with value 0; purpose unknown.
"""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.security import IasAce, IasZone

from zhaquirks import Bus, PowerConfigurationCluster
from zhaquirks.const import (
    CLUSTER_COMMAND,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
    ZHA_SEND_EVENT,
)
from zhaquirks.tuya import TuyaDatapointData, TuyaLocalCluster
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

DISARM = "disarm"
ARM_AWAY = "arm_away"
ARM_HOME = "arm_home"
PANIC = "panic"
EMERGENCY = "emergency"


class TuyaKeypadManufCluster(TuyaMCUCluster):
    """Tuya keypad manufacturer cluster."""

    BATTERY_PERCENTAGE_DP_ID = 3
    ANTI_REMOVE_ALARM_DP_ID = 24
    DISARMED_DP_ID = 26
    ARMED_DP_ID = 27
    ARMED_HOME_DP_ID = 28
    SOS_DP_ID = 29
    ARM_DELAY_TIME_DP_ID = 103
    KEYPAD_BEEPS_DP_ID = 104
    QUICK_SOS_DP_ID = 105
    QUICK_DISARM_DP_ID = 106
    QUICK_ARM_DP_ID = 107
    ADMIN_CODE_DP_ID = 108
    USER_CODE_DP_ID = 109
    ARM_DELAY_BEEPS_DP_ID = 111

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            TuyaMCUCluster.cluster_id + ARM_DELAY_TIME_DP_ID: (
                "arm_delay_time",
                t.uint8_t,
            ),
            TuyaMCUCluster.cluster_id + ARM_DELAY_BEEPS_DP_ID: (
                "arm_delay_beeps",
                t.uint8_t,
            ),
            TuyaMCUCluster.cluster_id + KEYPAD_BEEPS_DP_ID: (
                "keypad_beeps",
                t.uint8_t,
            ),
            TuyaMCUCluster.cluster_id + QUICK_DISARM_DP_ID: (
                "quick_disarm",
                t.uint8_t,
            ),
            TuyaMCUCluster.cluster_id + QUICK_ARM_DP_ID: (
                "quick_arm",
                t.uint8_t,
            ),
            TuyaMCUCluster.cluster_id + QUICK_SOS_DP_ID: (
                "quick_sos",
                t.uint8_t,
            ),
            TuyaMCUCluster.cluster_id + ADMIN_CODE_DP_ID: (
                "admin_code",
                t.CharacterString,
            ),
            TuyaMCUCluster.cluster_id + USER_CODE_DP_ID: (
                "user_code",
                t.CharacterString,
            ),
        }
    )

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        BATTERY_PERCENTAGE_DP_ID: DPToAttributeMapping(
            PowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
            converter=lambda x: x * 2,
        ),
        ARM_DELAY_TIME_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "arm_delay_time",
        ),
        ARM_DELAY_BEEPS_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "arm_delay_beeps",
        ),
        KEYPAD_BEEPS_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "keypad_beeps",
        ),
        QUICK_DISARM_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_disarm",
        ),
        QUICK_ARM_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_arm",
        ),
        QUICK_SOS_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_sos",
        ),
        ADMIN_CODE_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "admin_code",
        ),
        USER_CODE_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "user_code",
        ),
    }

    DP_TO_ACTION = {
        DISARMED_DP_ID: DISARM,
        ARMED_DP_ID: ARM_AWAY,
        ARMED_HOME_DP_ID: ARM_HOME,
        SOS_DP_ID: PANIC,
        ANTI_REMOVE_ALARM_DP_ID: EMERGENCY,
    }

    DP_TO_IAS_ACE = {
        DISARMED_DP_ID: ("arm_event", IasAce.ArmMode.Disarm),
        ARMED_DP_ID: ("arm_event", IasAce.ArmMode.Arm_All_Zones),
        ARMED_HOME_DP_ID: ("arm_event", IasAce.ArmMode.Arm_Day_Home_Only),
        SOS_DP_ID: ("panic_event", None),
        ANTI_REMOVE_ALARM_DP_ID: ("emergency_event", None),
    }

    def _dp_2_event(self, datapoint: TuyaDatapointData) -> None:
        """Convert arm/disarm/SOS datapoints to ZHA events and IAS ACE commands."""
        zone_id = 0
        user_code = self._attr_cache.get(
            self.attributes_by_name["user_code"].id, "1234"
        )

        # Fire IAS ACE event via internal bus
        ias_ace = self.DP_TO_IAS_ACE.get(datapoint.dp)
        if ias_ace:
            event_name, arm_mode = ias_ace
            if arm_mode is not None:
                self.endpoint.device.ias_bus.listener_event(
                    event_name, arm_mode, user_code, zone_id
                )
            else:
                self.endpoint.device.ias_bus.listener_event(event_name)

        # Update tamper zone_status on IAS Zone cluster
        if datapoint.dp == self.ANTI_REMOVE_ALARM_DP_ID:
            zone_status = (
                IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Tamper
                if datapoint.data.payload
                else 0
            )
            self.endpoint.ias_zone._update_attribute(
                IasZone.AttributeDefs.zone_status.id, zone_status
            )

        # Fire zha_event for HA automations
        action = self.DP_TO_ACTION.get(datapoint.dp)
        if action:
            self.listener_event(ZHA_SEND_EVENT, action, {})

    data_point_handlers = {
        BATTERY_PERCENTAGE_DP_ID: "_dp_2_attr_update",
        ARM_DELAY_TIME_DP_ID: "_dp_2_attr_update",
        ARM_DELAY_BEEPS_DP_ID: "_dp_2_attr_update",
        KEYPAD_BEEPS_DP_ID: "_dp_2_attr_update",
        QUICK_DISARM_DP_ID: "_dp_2_attr_update",
        QUICK_ARM_DP_ID: "_dp_2_attr_update",
        QUICK_SOS_DP_ID: "_dp_2_attr_update",
        ADMIN_CODE_DP_ID: "_dp_2_attr_update",
        USER_CODE_DP_ID: "_dp_2_attr_update",
        DISARMED_DP_ID: "_dp_2_event",
        ARMED_DP_ID: "_dp_2_event",
        ARMED_HOME_DP_ID: "_dp_2_event",
        SOS_DP_ID: "_dp_2_event",
        ANTI_REMOVE_ALARM_DP_ID: "_dp_2_event",
    }


class TuyaAlarmControlPanelCluster(TuyaLocalCluster, IasAce):
    """IAS ACE cluster that receives arm/disarm/panic events from the Tuya MCU."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ias_bus.add_listener(self)

    def arm_event(self, arm_mode: IasAce.ArmMode, arm_disarm_code: str, zone_id: int):
        """Handle arm event from Tuya MCU cluster."""
        self.listener_event(
            CLUSTER_COMMAND,
            self.endpoint.endpoint_id,
            self.commands_by_name["arm"].id,
            [arm_mode, arm_disarm_code, zone_id],
        )

    def emergency_event(self):
        """Handle emergency/tamper event from Tuya MCU cluster."""
        self.listener_event(
            CLUSTER_COMMAND,
            self.endpoint.endpoint_id,
            self.commands_by_name["emergency"].id,
            [],
        )

    def panic_event(self):
        """Handle SOS/panic event from Tuya MCU cluster."""
        self.listener_event(
            CLUSTER_COMMAND,
            self.endpoint.endpoint_id,
            self.commands_by_name["panic"].id,
            [],
        )


class TuyaIasZoneTamper(TuyaLocalCluster, IasZone):
    """IAS Zone cluster for tamper/anti-remove detection."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.attributes_by_name["zone_type"].id: IasZone.ZoneType.Contact_Switch,
    }


class TuyaPowerConfigurationCluster3AAA(TuyaLocalCluster, PowerConfigurationCluster):
    """PowerConfiguration cluster for devices with 3 AAA batteries."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.attributes_by_name[
            "battery_size"
        ].id: PowerConfiguration.BatterySize.AAA,
        PowerConfiguration.attributes_by_name["battery_quantity"].id: 3,
        PowerConfiguration.attributes_by_name["battery_rated_voltage"].id: 15,
    }


class TuyaWirelessZigbeeKeypad(CustomDevice):
    """Tuya TS0601 wireless Zigbee keypad."""

    device_automation_triggers = {
        (DISARM, DISARM): {ENDPOINT_ID: 1, COMMAND: DISARM},
        (ARM_AWAY, ARM_AWAY): {ENDPOINT_ID: 1, COMMAND: ARM_AWAY},
        (ARM_HOME, ARM_HOME): {ENDPOINT_ID: 1, COMMAND: ARM_HOME},
        (PANIC, PANIC): {ENDPOINT_ID: 1, COMMAND: PANIC},
        (EMERGENCY, EMERGENCY): {ENDPOINT_ID: 1, COMMAND: EMERGENCY},
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            ("_TZE200_n9clpsht", "TS0601"),
            ("_TZE200_nyvavzbj", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaMCUCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ANCILLARY_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaKeypadManufCluster,
                    TuyaAlarmControlPanelCluster,
                    TuyaPowerConfigurationCluster3AAA,
                    TuyaIasZoneTamper,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            }
        },
    }
