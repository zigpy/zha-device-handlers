"""MS-K1AZ Wireless Zigbee Keypad."""
from typing import Dict

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
from zigpy.zcl.clusters.security import IasAce

from zhaquirks import Bus, PowerConfigurationCluster
from zhaquirks.const import (
    CLUSTER_COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaDatapointData,
    TuyaDPType,
    TuyaLocalCluster,
    TuyaMCUCluster,
)


class WirelessZigbeeKeypadManufCluster(TuyaMCUCluster):
    """Wireless Zigbee Keypad manufacturer cluster."""

    TUYA_CLUSTER_ID = TuyaMCUCluster.cluster_id

    BATTERY_PERCENTAGE_DP_ID = 3  # Integer, read only
    SOS_ALARM_DP_ID = 23  # Enum, read only
    ANTI_REMOVE_ALARM_DP_ID = 24  # Enum, read only
    BATTERY_LEVEL_DP_ID = 25  # Enum, read only
    DISARMED_DP_ID = 26  # Enum, read only
    ARMED_DP_ID = 27  # Enum, read only
    ARMED_HOME_DP_ID = 28  # Enum, read only
    SOS_DP_ID = 29  # Enum, read only
    ARM_DELAY_TIME_DP_ID = 103  # Integer, 0-180, read/write
    KEYPAD_BEEPS_DP_ID = 104  # Boolean, read/write
    QUICK_SOS_DP_ID = 105  # Boolean, read/write
    QUICK_DISARM_DP_ID = 106  # Boolean, read/write
    QUICK_ARM_DP_ID = 107  # Boolean, read/write
    ADMIN_CODE_DP_ID = 108  # String, read only
    USER_CODE_DP_ID = 109  # String, read only
    RESET_DP_ID = 110  # Boolean, write only
    ARM_DELAY_BEEPS_DP_ID = 111  # Boolean, read/write

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            TUYA_CLUSTER_ID + ARM_DELAY_TIME_DP_ID: ("arm_delay_time", t.uint8_t),
            TUYA_CLUSTER_ID + ARM_DELAY_BEEPS_DP_ID: ("arm_delay_beeps", t.uint8_t),
            TUYA_CLUSTER_ID + KEYPAD_BEEPS_DP_ID: ("keypad_beeps", t.uint8_t),
            TUYA_CLUSTER_ID + QUICK_DISARM_DP_ID: ("quick_disarm", t.uint8_t),
            TUYA_CLUSTER_ID + QUICK_ARM_DP_ID: ("quick_arm", t.uint8_t),
            TUYA_CLUSTER_ID + QUICK_SOS_DP_ID: ("quick_sos", t.uint8_t),
            TUYA_CLUSTER_ID + ADMIN_CODE_DP_ID: ("admin_code", t.CharacterString),
            TUYA_CLUSTER_ID + USER_CODE_DP_ID: ("user_code", t.CharacterString),
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        BATTERY_PERCENTAGE_DP_ID: DPToAttributeMapping(
            PowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
            converter=lambda x: x * 2,
        ),
        ARM_DELAY_TIME_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "arm_delay_time",
            TuyaDPType.VALUE,
        ),
        ARM_DELAY_BEEPS_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "arm_delay_beeps",
            TuyaDPType.BOOL,
        ),
        KEYPAD_BEEPS_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "keypad_beeps",
            TuyaDPType.BOOL,
        ),
        QUICK_DISARM_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_disarm",
            TuyaDPType.BOOL,
        ),
        QUICK_ARM_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_arm",
            TuyaDPType.BOOL,
        ),
        QUICK_SOS_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_sos",
            TuyaDPType.BOOL,
        ),
        ADMIN_CODE_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "admin_code",
            TuyaDPType.STRING,
        ),
        USER_CODE_DP_ID: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "user_code",
            TuyaDPType.STRING,
        ),
    }

    def _dp_2_event(self, datapoint: TuyaDatapointData) -> None:
        """Convert DP to Event."""
        zone_id = 0
        user_code = self._attr_cache.get(
            self.attributes_by_name["user_code"].id, "1234"
        )

        if datapoint.dp == self.DISARMED_DP_ID:
            self.endpoint.device.ias_bus.listener_event(
                "arm_event", IasAce.ArmMode.Disarm, user_code, zone_id
            )
        elif datapoint.dp == self.ARMED_DP_ID:
            self.endpoint.device.ias_bus.listener_event(
                "arm_event", IasAce.ArmMode.Arm_All_Zones, user_code, zone_id
            )
        elif datapoint.dp == self.ARMED_HOME_DP_ID:
            self.endpoint.device.ias_bus.listener_event(
                "arm_event", IasAce.ArmMode.Arm_Day_Home_Only, user_code, zone_id
            )
        elif datapoint.dp == self.ANTI_REMOVE_ALARM_DP_ID:
            self.endpoint.device.ias_bus.listener_event("emergency_event")
        elif datapoint.dp == self.SOS_DP_ID:
            self.endpoint.device.ias_bus.listener_event("panic_event")

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
    }


class AlarmControlPanelCluster(TuyaLocalCluster, IasAce):
    """Tuya Alarm Control Panel cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ias_bus.add_listener(self)

    def arm_event(self, arm_mode: IasAce.ArmMode, arm_disarm_code: str, zone_id: int):
        """Handle arm event."""
        self.listener_event(
            CLUSTER_COMMAND,
            self.endpoint.endpoint_id,
            self.commands_by_name["arm"].id,
            [arm_mode, arm_disarm_code, zone_id],
        )

    def emergency_event(self):
        """Handle emergency event."""
        self.listener_event(
            CLUSTER_COMMAND,
            self.endpoint.endpoint_id,
            self.commands_by_name["emergency"].id,
            [],
        )

    def panic_event(self):
        """Handle panic event."""
        self.listener_event(
            CLUSTER_COMMAND,
            self.endpoint.endpoint_id,
            self.commands_by_name["panic"].id,
            [],
        )


class TuyaPowerConfigurationCluster3AAA(TuyaLocalCluster, PowerConfigurationCluster):
    """PowerConfiguration cluster for devices with 3 AAA batteries."""

    BATTERY_SIZE = 0x0031
    BATTERY_QUANTITY = 0x0033
    BATTERY_RATED_VOLTAGE = 0x0034

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: PowerConfiguration.BatterySize.AAA,
        BATTERY_QUANTITY: 3,
        BATTERY_RATED_VOLTAGE: 15,
    }


class WirelessZigbeeKeypad(CustomDevice):
    """MS-K1AZ Wireless Zigbee Keypad."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.ias_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        # "endpoints": {
        #   "1": {
        #     "profile_id": 260,
        #     "device_type": "0x0051",
        #     "in_clusters": [
        #       "0x0000",
        #       "0x0004",
        #       "0x0005",
        #       "0xef00"
        #     ],
        #     "out_clusters": [
        #       "0x000a",
        #       "0x0019"
        #     ]
        #   }
        # }
        MODELS_INFO: [("_TZE200_n9clpsht", "TS0601")],
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
                    WirelessZigbeeKeypadManufCluster,
                    AlarmControlPanelCluster,
                    TuyaPowerConfigurationCluster3AAA,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            }
        },
    }
