"""MS-K1AZ Wireless Zigbee Keypad."""

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

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
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
    TuyaDPType,
    TuyaLocalCluster,
    TuyaMCUCluster,
)

TUYA_DP_ID_BATTERY_LEVEL_PERCENTAGE = 3  # Percentage
TUYA_DP_ID_SOS_ALARM = 23
TUYA_DP_ID_ANTI_REMOVE_ALARM = 24
TUYA_DP_ID_BATTERY_LEVEL_ENUM = 25  # "Low", "Middle", "High"
TUYA_DP_ID_DISARMED = 26
TUYA_DP_ID_ARMED = 27
TUYA_DP_ID_ARMED_HOME = 28
TUYA_DP_ID_SOS = 29
TUYA_DP_ID_ARM_DELAY_TIME = 103  # Seconds
TUYA_DP_ID_KEYPAD_BEEPS = 104  # Boolean
TUYA_DP_ID_QUICK_SOS = 105  # Boolean
TUYA_DP_ID_QUICK_DISARM = 106  # Boolean
TUYA_DP_ID_QUICK_ARM = 107  # Boolean
TUYA_DP_ID_ADMIN_CODE = 108  # String
TUYA_DP_ID_USER_CODE = 109  # String
TUYA_DP_ID_RESET = 110  # Boolean
TUYA_DP_ID_ARM_DELAY_BEEPS = 111  # Boolean
TUYA_DP_ID_UNKNOWN = 112


class TuyaAlarmControlPanelCluster(IasAce, TuyaLocalCluster):
    """Tuya Alarm Control Panel cluster."""


class TuyaPowerConfigurationCluster3AAA(PowerConfigurationCluster, TuyaLocalCluster):
    """PowerConfiguration cluster for devices with 3 AAA batteries."""

    BATTERY_SIZE = 0x0031
    BATTERY_QUANTITY = 0x0033
    BATTERY_RATED_VOLTAGE = 0x0034

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: PowerConfiguration.BatterySize.AAA,
        BATTERY_QUANTITY: 3,
        BATTERY_RATED_VOLTAGE: 15,
    }


class WirelessZigbeeKeypadManufCluster(TuyaMCUCluster):
    """Wireless Zigbee Keypad manufacturer cluster."""

    cluster_id = TuyaMCUCluster.cluster_id

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            cluster_id + TUYA_DP_ID_ARM_DELAY_TIME: ("arm_delay_time", t.uint32_t),
            cluster_id + TUYA_DP_ID_KEYPAD_BEEPS: ("keypad_beeps", t.Bool),
            cluster_id + TUYA_DP_ID_QUICK_SOS: ("quick_sos", t.Bool),
            cluster_id + TUYA_DP_ID_QUICK_DISARM: ("quick_disarm", t.Bool),
            cluster_id + TUYA_DP_ID_QUICK_ARM: ("quick_arm", t.Bool),
            cluster_id + TUYA_DP_ID_ADMIN_CODE: ("admin_code", t.CharacterString),
            cluster_id + TUYA_DP_ID_USER_CODE: ("user_code", t.CharacterString),
            cluster_id + TUYA_DP_ID_RESET: ("reset", t.Bool),
            cluster_id + TUYA_DP_ID_ARM_DELAY_BEEPS: ("arm_delay_beeps", t.Bool),
        }
    )

    dp_to_attribute = {
        TUYA_DP_ID_BATTERY_LEVEL_PERCENTAGE: DPToAttributeMapping(
            TuyaPowerConfigurationCluster3AAA.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
            converter=lambda x: x * 2,
        ),
        TUYA_DP_ID_ARM_DELAY_TIME: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "arm_delay_time",
            TuyaDPType.VALUE,
        ),
        TUYA_DP_ID_KEYPAD_BEEPS: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "keypad_beeps",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_ID_QUICK_SOS: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_sos",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_ID_QUICK_DISARM: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_disarm",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_ID_QUICK_ARM: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "quick_arm",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_ID_ADMIN_CODE: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "admin_code",
            TuyaDPType.STRING,
        ),
        TUYA_DP_ID_USER_CODE: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "user_code",
            TuyaDPType.STRING,
        ),
        TUYA_DP_ID_RESET: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "reset",
            TuyaDPType.BOOL,
        ),
        TUYA_DP_ID_ARM_DELAY_BEEPS: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "arm_delay_beeps",
            TuyaDPType.BOOL,
        ),
    }

    data_point_handlers = {
        TUYA_DP_ID_BATTERY_LEVEL_PERCENTAGE: "_dp_2_attr_update",
        TUYA_DP_ID_ARM_DELAY_TIME: "_dp_2_attr_update",
        TUYA_DP_ID_KEYPAD_BEEPS: "_dp_2_attr_update",
        TUYA_DP_ID_QUICK_SOS: "_dp_2_attr_update",
        TUYA_DP_ID_QUICK_DISARM: "_dp_2_attr_update",
        TUYA_DP_ID_QUICK_ARM: "_dp_2_attr_update",
        TUYA_DP_ID_ADMIN_CODE: "_dp_2_attr_update",
        TUYA_DP_ID_USER_CODE: "_dp_2_attr_update",
        TUYA_DP_ID_RESET: "_dp_2_attr_update",
        TUYA_DP_ID_ARM_DELAY_BEEPS: "_dp_2_attr_update",
    }


class WirelessZigbeeKeypad(CustomDevice):
    """MS-K1AZ Wireless Zigbee Keypad."""

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
                    TuyaPowerConfigurationCluster3AAA,
                    TuyaAlarmControlPanelCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            }
        },
    }
