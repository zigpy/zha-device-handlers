# Schneider Electric

- [Schneider Electric](#schneider-electric)
  - [Introduction](#introduction)
  - [Helpers](#helpers)
  - [Devices](#devices)
    - [Shutter](#shutter)
      - [NHPB/SHUTTER/1 ❔](#nhpbshutter1-)
      - [PUCK/SHUTTER/1 ❌](#puckshutter1-)
      - [1GANG/SHUTTER/1 ❔](#1gangshutter1-)
    - [Switch](#switch)
      - [CH2AX/SWITCH/1 ❔](#ch2axswitch1-)
      - [CH10AX/SWITCH/1 ❌](#ch10axswitch1-)
      - [FLS/AIRLINK/4 ❌](#flsairlink4-)
      - [FLS/SYSTEM-M/4 ❔](#flssystem-m4-)
      - [LK Switch](#lk-switch)
      - [NHPB/SWITCH/1 ❔](#nhpbswitch1-)
      - [PUCK/SWITCH/1 ❔](#puckswitch1-)
      - [U201SRY2KWZB ❔](#u201sry2kwzb-)
      - [U202SRY2KWZB ❔](#u202sry2kwzb-)
    - [Dimmer](#dimmer)
      - [CH/DIMMER/1 ❔](#chdimmer1-)
      - [PUCK/DIMMER/1 ❔](#puckdimmer1-)
      - [LK Dimmer](#lk-dimmer)
      - [NHPB/DIMMER/1 ❔](#nhpbdimmer1-)
      - [NHROTARY/DIMMER/1 ❔](#nhrotarydimmer1-)
      - [U201DST600ZB ❔](#u201dst600zb-)
      - [U202DST600ZB ❔](#u202dst600zb-)
    - [Plug](#plug)
      - [CH/Socket/2 ❔](#chsocket2-)
      - [EH-ZB-SPD-V2 ❔](#eh-zb-spd-v2-)
      - [LK/OUTLET/1 ❔](#lkoutlet1-)
      - [SOCKET/OUTLET/1 ❔](#socketoutlet1-)
      - [SOCKET/OUTLET/2 ❔](#socketoutlet2-)
      - [SMARTPLUG/1 ❔](#smartplug1-)
    - [Thermostat](#thermostat)
      - [CCTFR6700 ❔](#cctfr6700-)
      - [EH-ZB-VACT ❔](#eh-zb-vact-)
      - [EH-ZB-RTS ❔](#eh-zb-rts-)
      - [EH-ZB-HACT ❔](#eh-zb-hact-)
      - [Thermostat ❔](#thermostat-)
      - [iTRV ❔](#itrv-)
    - [Motion](#motion)
      - [CCT595011_AS ❔](#cct595011_as-)
      - [NHMOTION/SWITCH/1 ❔](#nhmotionswitch1-)
    - [MISC](#misc)
      - [CCT592011_AS ❔](#cct592011_as-)
      - [EH-ZB-LMACT ❔](#eh-zb-lmact-)

## Introduction

The purpose of this file is to list all Zigbee capable device from Schneider Electric manufacturer, the status of their potential quirk, their basic zigbee infos and more.

All devices are listed alphabetically based on the Zigbee `model (0x0005)` attribute from `Basic (0x0000)` cluster.

All quirk infos should remain in basecode. 

Status :

- ✅ : Supported
- ❌ : Not supported
- 🆗 : No quirk needed
- ❔ : Unknown

## Helpers

Device signature can be acquired by clicking on the "Zigbee Device Signature" button in the device settings view

Sources :

- [wiserapp](https://github.com/Signalare/com.se.wiserapp) for [Homey](https://homey.app/en-us/app/com.se.wiserapp/Schneider-Electric/)
- [deconz-rest-plugin wiser](https://github.com/dresden-elektronik/deconz-rest-plugin/tree/master/devices/wiser)
- [deconz-rest-plugin merten](https://github.com/dresden-elektronik/deconz-rest-plugin/tree/master/devices/merten)
- [zigbee-herdsman-converters](https://github.com/Koenkk/zigbee-herdsman-converters/tree/master/devices/schneider_electric.js)

## Devices

### Shutter

Lift percentage is reversed

#### NHPB/SHUTTER/1 ❔

<details>
    <summary>Device signature</summary>

```json
{
  "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
  "endpoints": {
    "5": {
      "profile_id": 260,
      "device_type": "0x0202",
      "in_clusters": [
        "0x0000",
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0102",
        "0x0b05"
      ],
      "out_clusters": [
        "0x0019"
      ]
    },
    "21": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0003",
        "0x0b05",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0102"
      ]
    },
    "242": {
      "profile_id": 41440,
      "device_type": "0x0061",
      "in_clusters": [],
      "out_clusters": [
        "0x0021"
      ]
    }
  },
  "manufacturer": "Schneider Electric",
  "model": "NHPB/SHUTTER/1",
  "class": "zigpy.device.Device"
}
```

</details>

<details>
    <summary>zha_toolkit.scan_device</summary>

```json
{
  "ieee": "00:3c:84:xx:xx:xx:xx:x1",
  "nwk": "0x21d2",
  "model": "NHPB/SHUTTER/1",
  "manufacturer": "Schneider Electric",
  "manufacturer_id": "0x4190",
  "endpoints": [
    {
      "id": 5,
      "device_type": "0x0202",
      "profile": "0x0104",
      "in_clusters": {
        "0x0000": {
          "cluster_id": "0x0000",
          "title": "Basic",
          "name": "basic",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "zcl_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "app_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "stack_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 6
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "hw_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "manufacturer",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "Schneider Electric"
            },
            "0x0005": {
              "attribute_id": "0x0005",
              "attribute_name": "model",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "NHPB/SHUTTER/1"
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "date_code",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "power_source",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "generic_device_class",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0009": {
              "attribute_id": "0x0009",
              "attribute_name": "generic_device_type",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 225
            },
            "0x000a": {
              "attribute_id": "0x000a",
              "attribute_name": "product_code",
              "value_type": [
                "0x41",
                "LVBytes",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x000b": {
              "attribute_id": "0x000b",
              "attribute_name": "product_url",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "http://www.schneider-electric.com"
            },
            "0x4000": {
              "attribute_id": "0x4000",
              "attribute_name": "sw_build_id",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "002.004.016 R"
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "002.004.016 R"
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "001.000.000"
            },
            "0xe004": {
              "attribute_id": "0xe004",
              "attribute_name": "57348",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "213249FEFF5ECFD"
            },
            "0xe007": {
              "attribute_id": "0xe007",
              "attribute_name": "57351",
              "value_type": [
                "0x31",
                "enum16",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 17422
            },
            "0xe008": {
              "attribute_id": "0xe008",
              "attribute_name": "57352",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Light"
            },
            "0xe009": {
              "attribute_id": "0xe009",
              "attribute_name": "57353",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "NHPB/SHUTTER/1"
            },
            "0xe00a": {
              "attribute_id": "0xe00a",
              "attribute_name": "57354",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Home"
            },
            "0xe00b": {
              "attribute_id": "0xe00b",
              "attribute_name": "57355",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "reset_fact_default",
              "command_arguments": "<class 'zigpy.zcl.foundation.reset_fact_default'>"
            }
          },
          "commands_generated": {}
        },
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "identify_time",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            }
          }
        },
        "0x0004": {
          "cluster_id": "0x0004",
          "title": "Groups",
          "name": "groups",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "name_support",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add",
              "command_arguments": "<class 'zigpy.zcl.foundation.add'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view",
              "command_arguments": "<class 'zigpy.zcl.foundation.view'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership",
              "command_arguments": "<class 'zigpy.zcl.foundation.get_membership'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "remove_all",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove_all'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "add_if_identifying",
              "command_arguments": "<class 'zigpy.zcl.foundation.add_if_identifying'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_membership_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_response'>"
            }
          }
        },
        "0x0005": {
          "cluster_id": "0x0005",
          "title": "Scenes",
          "name": "scenes",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "count",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "current_scene",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "current_group",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "scene_valid",
              "value_type": [
                "0x10",
                "Bool",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "name_support",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add",
              "command_arguments": "<class 'zigpy.zcl.foundation.add'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view",
              "command_arguments": "<class 'zigpy.zcl.foundation.view'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove_all'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store",
              "command_arguments": "<class 'zigpy.zcl.foundation.store'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "recall",
              "command_arguments": "<class 'zigpy.zcl.foundation.recall'>"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership",
              "command_arguments": "<class 'zigpy.zcl.foundation.get_scene_membership'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_scene_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_scene_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all_scenes_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_all_scenes_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.store_scene_response'>"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_scene_membership_response'>"
            }
          }
        },
        "0x0102": {
          "cluster_id": "0x0102",
          "title": "Window Covering",
          "name": "window_covering",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "window_covering_type",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 8
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "config_status",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "current_position_lift_percentage",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 20
            },
            "0x0009": {
              "attribute_id": "0x0009",
              "attribute_name": "current_position_tilt_percentage",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0017": {
              "attribute_id": "0x0017",
              "attribute_name": "window_covering_mode",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 8
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe000": {
              "attribute_id": "0xe000",
              "attribute_name": "57344",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 120
            },
            "0xe010": {
              "attribute_id": "0xe010",
              "attribute_name": "57360",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xe012": {
              "attribute_id": "0xe012",
              "attribute_name": "57362",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 32767
            },
            "0xe013": {
              "attribute_id": "0xe013",
              "attribute_name": "57363",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xe014": {
              "attribute_id": "0xe014",
              "attribute_name": "57364",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 1200
            },
            "0xe015": {
              "attribute_id": "0xe015",
              "attribute_name": "57365",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 1200
            },
            "0xe016": {
              "attribute_id": "0xe016",
              "attribute_name": "57366",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 100
            },
            "0xe017": {
              "attribute_id": "0xe017",
              "attribute_name": "57367",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 255
            }
          },
          "commands_received": {},
          "commands_generated": {}
        },
        "0x0b05": {
          "cluster_id": "0x0b05",
          "title": "Diagnostic",
          "name": "diagnostic",
          "attributes": {
            "0x011c": {
              "attribute_id": "0x011c",
              "attribute_name": "last_message_lqi",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x011d": {
              "attribute_id": "0x011d",
              "attribute_name": "last_message_rssi",
              "value_type": [
                "0x28",
                "int8s",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {}
        }
      },
      "out_clusters": {
        "0x0019": {
          "cluster_id": "0x0019",
          "title": "Ota",
          "name": "ota",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "upgrade_server_id",
              "value_type": [
                "0xf0",
                "EUI64",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": [
                255,
                170,
                5,
                255,
                255,
                46,
                33,
                0
              ]
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "file_offset",
              "value_type": [
                "0x23",
                "uint32_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 4294967295
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "current_file_version",
              "value_type": [
                "0x23",
                "uint32_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 33820927
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "image_upgrade_status",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "manufacturer_id",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 4190
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "image_type_id",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 65535
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "3",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "6",
              "command_args": "'not_in_zcl'"
            }
          }
        }
      }
    },
    {
      "id": 21,
      "device_type": "0x0104",
      "profile": "0x0104",
      "in_clusters": {
        "0x0000": {
          "cluster_id": "0x0000",
          "title": "Basic",
          "name": "basic",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "zcl_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "app_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "stack_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 6
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "hw_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "manufacturer",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "Schneider Electric"
            },
            "0x0005": {
              "attribute_id": "0x0005",
              "attribute_name": "model",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "NHPB/SHUTTER/1"
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "date_code",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "power_source",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "generic_device_class",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0009": {
              "attribute_id": "0x0009",
              "attribute_name": "generic_device_type",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 225
            },
            "0x000a": {
              "attribute_id": "0x000a",
              "attribute_name": "product_code",
              "value_type": [
                "0x41",
                "LVBytes",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x000b": {
              "attribute_id": "0x000b",
              "attribute_name": "product_url",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "http://www.schneider-electric.com"
            },
            "0x4000": {
              "attribute_id": "0x4000",
              "attribute_name": "sw_build_id",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "002.004.016 R"
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "002.004.016 R"
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "001.000.000"
            },
            "0xe004": {
              "attribute_id": "0xe004",
              "attribute_name": "57348",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "213249FEFF5ECFD"
            },
            "0xe007": {
              "attribute_id": "0xe007",
              "attribute_name": "57351",
              "value_type": [
                "0x31",
                "enum16",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 17422
            },
            "0xe008": {
              "attribute_id": "0xe008",
              "attribute_name": "57352",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Light"
            },
            "0xe009": {
              "attribute_id": "0xe009",
              "attribute_name": "57353",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "NHPB/SHUTTER/1"
            },
            "0xe00a": {
              "attribute_id": "0xe00a",
              "attribute_name": "57354",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Home"
            },
            "0xe00b": {
              "attribute_id": "0xe00b",
              "attribute_name": "57355",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "reset_fact_default",
              "command_arguments": "<class 'zigpy.zcl.foundation.reset_fact_default'>"
            }
          },
          "commands_generated": {}
        },
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "identify_time",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            }
          }
        },
        "0x0b05": {
          "cluster_id": "0x0b05",
          "title": "Diagnostic",
          "name": "diagnostic",
          "attributes": {
            "0x011c": {
              "attribute_id": "0x011c",
              "attribute_name": "last_message_lqi",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x011d": {
              "attribute_id": "0x011d",
              "attribute_name": "last_message_rssi",
              "value_type": [
                "0x28",
                "int8s",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {}
        },
        "0xff17": {
          "cluster_id": "0xff17",
          "title": "Manufacturer Specific",
          "name": "manufacturer_specific",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "0",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "1",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 3
            },
            "0x0010": {
              "attribute_id": "0x0010",
              "attribute_name": "16",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0x0011": {
              "attribute_id": "0x0011",
              "attribute_name": "17",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0x0020": {
              "attribute_id": "0x0020",
              "attribute_name": "32",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 1
            },
            "0x0021": {
              "attribute_id": "0x0021",
              "attribute_name": "33",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {}
        }
      },
      "out_clusters": {
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify",
              "command_arguments": "<class 'zigpy.zcl.foundation.identify'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0004": {
          "cluster_id": "0x0004",
          "title": "Groups",
          "name": "groups",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_membership_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "4",
              "command_args": "'not_in_zcl'"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "5",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0005": {
          "cluster_id": "0x0005",
          "title": "Scenes",
          "name": "scenes",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_scene_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_scene_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all_scenes_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_all_scenes_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.store_scene_response'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "5",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_scene_membership_response'>"
            }
          }
        },
        "0x0006": {
          "cluster_id": "0x0006",
          "title": "On/Off",
          "name": "on_off",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "0",
              "command_args": "'not_in_zcl'"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "2",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0008": {
          "cluster_id": "0x0008",
          "title": "Level control",
          "name": "level",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "0",
              "command_args": "'not_in_zcl'"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "2",
              "command_args": "'not_in_zcl'"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "3",
              "command_args": "'not_in_zcl'"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "4",
              "command_args": "'not_in_zcl'"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "5",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "6",
              "command_args": "'not_in_zcl'"
            },
            "0x07": {
              "command_id": "0x07",
              "command_name": "7",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0102": {
          "cluster_id": "0x0102",
          "title": "Window Covering",
          "name": "window_covering",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "0",
              "command_args": "'not_in_zcl'"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "2",
              "command_args": "'not_in_zcl'"
            }
          }
        }
      }
    },
    {
      "id": 242,
      "device_type": "0x0061",
      "profile": "0xa1e0"
    }
  ]
}
```

</details>

#### PUCK/SHUTTER/1 ❌

<details>
  <summary>Jeedom logs</summary>
From [Jeedom community](https://community.jeedom.com/t/plugin-zigbee-beta-blabla/53420/699)

> Volets roulants module Schneider Electric Wiser CCT5015-0002W

```json
{
  "ieee": "00:0d:6f:ff:fe:cb:52:11",
  "nwk": 31119,
  "status": 2,
  "lqi": "231",
  "rssi": "-65",
  "last_seen": "1617382106.1621628",
  "node_descriptor": "01:40:8e:5e:10:52:52:00:00:2c:52:00:00",
  "endpoints": [
    {
      "id": 5,
      "status": 1,
      "device_type": 514,
      "profile_id": 260,
      "manufacturer": "Schneider Electric",
      "model": "PUCK\/SHUTTER\/1",
      "output_clusters": [
        {
          "id": 25,
          "name": "Ota",
          "attributes": []
        }
      ],
      "input_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": [
            {
              "id": 0,
              "name": "zcl_version",
              "value": 3
            },
            {
              "id": 1,
              "name": "app_version",
              "value": 2
            },
            {
              "id": 2,
              "name": "stack_version",
              "value": 6
            },
            {
              "id": 3,
              "name": "hw_version",
              "value": 1
            },
            {
              "id": 4,
              "name": "manufacturer",
              "value": "Schneider Electric"
            },
            {
              "id": 5,
              "name": "model",
              "value": "PUCK\/SHUTTER\/1"
            },
            {
              "id": 6,
              "name": "date_code",
              "value": ""
            },
            {
              "id": 7,
              "name": "power_source",
              "value": 1
            },
            {
              "id": 16384,
              "name": "sw_build_id",
              "value": "002.004.018 R"
            }
          ]
        },
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 4,
          "name": "Groups",
          "attributes": []
        },
        {
          "id": 5,
          "name": "Scenes",
          "attributes": []
        },
        {
          "id": 258,
          "name": "Window Covering",
          "attributes": []
        },
        {
          "id": 2821,
          "name": "Diagnostic",
          "attributes": []
        }
      ]
    },
    {
      "id": 242,
      "status": 1,
      "device_type": 97,
      "profile_id": 41440,
      "manufacturer": null,
      "model": null,
      "output_clusters": [
        {
          "id": 33,
          "name": "GreenPowerProxy",
          "attributes": []
        }
      ],
      "input_clusters": []
    }
  ],
  "signature": {
    "manufacturer": "Schneider Electric",
    "model": "PUCK\/SHUTTER\/1",
    "node_desc": {
      "byte1": 1,
      "byte2": 64,
      "mac_capability_flags": 142,
      "manufacturer_code": 4190,
      "maximum_buffer_size": 82,
      "maximum_incoming_transfer_size": 82,
      "server_mask": 11264,
      "maximum_outgoing_transfer_size": 82,
      "descriptor_capability_field": 0
    },
    "endpoints": {
      "5": {
        "profile_id": 260,
        "device_type": 514,
        "input_clusters": [
          0,
          3,
          4,
          5,
          258,
          2821
        ],
        "output_clusters": [
          25
        ]
      },
      "242": {
        "profile_id": 41440,
        "device_type": 97,
        "input_clusters": [],
        "output_clusters": [
          33
        ]
      }
    }
  },
  "class": "zigpy.device"
}
```

</details>

#### 1GANG/SHUTTER/1 ❔

### Switch

#### CH2AX/SWITCH/1 ❔

<details>
  <summary>Signature</summary>
  
```json
{
  "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
  "endpoints": {
    "1": {
      "profile_id": 260,
      "device_type": "0x0100",
      "in_clusters": [
        "0x0000",
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0b05"
      ],
      "out_clusters": [
        "0x0019"
      ]
    },
    "21": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0003",
        "0x0b05",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0102"
      ]
    },
    "242": {
      "profile_id": 41440,
      "device_type": "0x0061",
      "in_clusters": [],
      "out_clusters": [
        "0x0021"
      ]
    }
  },
  "manufacturer": "Schneider Electric",
  "model": "CH2AX/SWITCH/1",
  "class": "zigpy.device.Device"
}
```

</details>

<details>
  <summary>zha_toolkit.scan_device</summary>

```json
{
  "ieee": "2c:11:65:00:00:00:00:00",
  "nwk": "0xdb05",
  "model": "CH2AX/SWITCH/1",
  "manufacturer": "Schneider Electric",
  "manufacturer_id": "0x4190",
  "endpoints": [
    {
      "id": 1,
      "device_type": "0x0100",
      "profile": "0x0104",
      "in_clusters": {
        "0x0000": {
          "cluster_id": "0x0000",
          "title": "Basic",
          "name": "basic",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "zcl_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "app_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "stack_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 6
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "hw_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "manufacturer",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "Schneider Electric"
            },
            "0x0005": {
              "attribute_id": "0x0005",
              "attribute_name": "model",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "CH2AX/SWITCH/1"
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "date_code",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "power_source",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "generic_device_class",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0009": {
              "attribute_id": "0x0009",
              "attribute_name": "generic_device_type",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 225
            },
            "0x000a": {
              "attribute_id": "0x000a",
              "attribute_name": "product_code",
              "value_type": ["0x41", "LVBytes", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x000b": {
              "attribute_id": "0x000b",
              "attribute_name": "product_url",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "http://www.schneider-electric.com"
            },
            "0x4000": {
              "attribute_id": "0x4000",
              "attribute_name": "sw_build_id",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "002.005.007 R"
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "002.005.007 R"
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "001.000.000"
            },
            "0xe004": {
              "attribute_id": "0xe004",
              "attribute_name": "57348",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "C5F121FEFF65112"
            },
            "0xe007": {
              "attribute_id": "0xe007",
              "attribute_name": "57351",
              "value_type": ["0x31", "enum16", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 17433
            },
            "0xe008": {
              "attribute_id": "0xe008",
              "attribute_name": "57352",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Light"
            },
            "0xe009": {
              "attribute_id": "0xe009",
              "attribute_name": "57353",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "CH2AX/SWITCH/1"
            },
            "0xe00a": {
              "attribute_id": "0xe00a",
              "attribute_name": "57354",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Home"
            },
            "0xe00b": {
              "attribute_id": "0xe00b",
              "attribute_name": "57355",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "reset_fact_default",
              "command_arguments": "<class 'zigpy.zcl.foundation.reset_fact_default'>"
            }
          },
          "commands_generated": {}
        },
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "identify_time",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            }
          }
        },
        "0x0004": {
          "cluster_id": "0x0004",
          "title": "Groups",
          "name": "groups",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "name_support",
              "value_type": ["0x18", "bitmap8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add",
              "command_arguments": "<class 'zigpy.zcl.foundation.add'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view",
              "command_arguments": "<class 'zigpy.zcl.foundation.view'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership",
              "command_arguments": "<class 'zigpy.zcl.foundation.get_membership'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "remove_all",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove_all'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "add_if_identifying",
              "command_arguments": "<class 'zigpy.zcl.foundation.add_if_identifying'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_membership_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_response'>"
            }
          }
        },
        "0x0005": {
          "cluster_id": "0x0005",
          "title": "Scenes",
          "name": "scenes",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "count",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "current_scene",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "current_group",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "scene_valid",
              "value_type": ["0x10", "Bool", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "name_support",
              "value_type": ["0x18", "bitmap8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add",
              "command_arguments": "<class 'zigpy.zcl.foundation.add'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view",
              "command_arguments": "<class 'zigpy.zcl.foundation.view'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove_all'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store",
              "command_arguments": "<class 'zigpy.zcl.foundation.store'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "recall",
              "command_arguments": "<class 'zigpy.zcl.foundation.recall'>"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership",
              "command_arguments": "<class 'zigpy.zcl.foundation.get_scene_membership'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_scene_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_scene_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all_scenes_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_all_scenes_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.store_scene_response'>"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_scene_membership_response'>"
            }
          }
        },
        "0x0006": {
          "cluster_id": "0x0006",
          "title": "On/Off",
          "name": "on_off",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "on_off",
              "value_type": ["0x10", "Bool", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x4001": {
              "attribute_id": "0x4001",
              "attribute_name": "on_time",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0x4002": {
              "attribute_id": "0x4002",
              "attribute_name": "off_wait_time",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe000": {
              "attribute_id": "0xe000",
              "attribute_name": "57344",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": ["0x23", "uint32_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": ["0x18", "bitmap8", "Discrete"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 1
            },
            "0xe003": {
              "attribute_id": "0xe003",
              "attribute_name": "57347",
              "value_type": ["0x23", "uint32_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            }
          },
          "commands_received": {},
          "commands_generated": {}
        },
        "0x0b05": {
          "cluster_id": "0x0b05",
          "title": "Diagnostic",
          "name": "diagnostic",
          "attributes": {
            "0x011c": {
              "attribute_id": "0x011c",
              "attribute_name": "last_message_lqi",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 120
            },
            "0x011d": {
              "attribute_id": "0x011d",
              "attribute_name": "last_message_rssi",
              "value_type": ["0x28", "int8s", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": -70
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {}
        }
      },
      "out_clusters": {
        "0x0019": {
          "cluster_id": "0x0019",
          "title": "Ota",
          "name": "ota",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "upgrade_server_id",
              "value_type": ["0xf0", "EUI64", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": [138, 55, 9, 255, 255, 46, 33, 0]
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "file_offset",
              "value_type": ["0x23", "uint32_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 4294967295
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "current_file_version",
              "value_type": ["0x23", "uint32_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 33884159
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "image_upgrade_status",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "manufacturer_id",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 4190
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "image_type_id",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 65535
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "3",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "6",
              "command_args": "'not_in_zcl'"
            }
          }
        }
      }
    },
    {
      "id": 21,
      "device_type": "0x0104",
      "profile": "0x0104",
      "in_clusters": {
        "0x0000": {
          "cluster_id": "0x0000",
          "title": "Basic",
          "name": "basic",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "zcl_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "app_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "stack_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 6
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "hw_version",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "manufacturer",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "Schneider Electric"
            },
            "0x0005": {
              "attribute_id": "0x0005",
              "attribute_name": "model",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "CH2AX/SWITCH/1"
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "date_code",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "power_source",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "generic_device_class",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0009": {
              "attribute_id": "0x0009",
              "attribute_name": "generic_device_type",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 225
            },
            "0x000a": {
              "attribute_id": "0x000a",
              "attribute_name": "product_code",
              "value_type": ["0x41", "LVBytes", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x000b": {
              "attribute_id": "0x000b",
              "attribute_name": "product_url",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "http://www.schneider-electric.com"
            },
            "0x4000": {
              "attribute_id": "0x4000",
              "attribute_name": "sw_build_id",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "002.005.007 R"
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "002.005.007 R"
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "001.000.000"
            },
            "0xe004": {
              "attribute_id": "0xe004",
              "attribute_name": "57348",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "C5F121FEFF65112"
            },
            "0xe007": {
              "attribute_id": "0xe007",
              "attribute_name": "57351",
              "value_type": ["0x31", "enum16", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 17433
            },
            "0xe008": {
              "attribute_id": "0xe008",
              "attribute_name": "57352",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Light"
            },
            "0xe009": {
              "attribute_id": "0xe009",
              "attribute_name": "57353",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "CH2AX/SWITCH/1"
            },
            "0xe00a": {
              "attribute_id": "0xe00a",
              "attribute_name": "57354",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Home"
            },
            "0xe00b": {
              "attribute_id": "0xe00b",
              "attribute_name": "57355",
              "value_type": ["0x42", "CharacterString", "Discrete"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "reset_fact_default",
              "command_arguments": "<class 'zigpy.zcl.foundation.reset_fact_default'>"
            }
          },
          "commands_generated": {}
        },
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "identify_time",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            }
          }
        },
        "0x0b05": {
          "cluster_id": "0x0b05",
          "title": "Diagnostic",
          "name": "diagnostic",
          "attributes": {
            "0x011c": {
              "attribute_id": "0x011c",
              "attribute_name": "last_message_lqi",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 120
            },
            "0x011d": {
              "attribute_id": "0x011d",
              "attribute_name": "last_message_rssi",
              "value_type": ["0x28", "int8s", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": -70
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {}
        },
        "0xff17": {
          "cluster_id": "0xff17",
          "title": "Manufacturer Specific",
          "name": "manufacturer_specific",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "0",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 2
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "1",
              "value_type": ["0x30", "enum8", "Discrete"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 7
            },
            "0x0010": {
              "attribute_id": "0x0010",
              "attribute_name": "16",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0x0011": {
              "attribute_id": "0x0011",
              "attribute_name": "17",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0x0020": {
              "attribute_id": "0x0020",
              "attribute_name": "32",
              "value_type": ["0x20", "uint8_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 1
            },
            "0x0021": {
              "attribute_id": "0x0021",
              "attribute_name": "33",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {}
        }
      },
      "out_clusters": {
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify",
              "command_arguments": "<class 'zigpy.zcl.foundation.identify'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0004": {
          "cluster_id": "0x0004",
          "title": "Groups",
          "name": "groups",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_membership_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "4",
              "command_args": "'not_in_zcl'"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "5",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0005": {
          "cluster_id": "0x0005",
          "title": "Scenes",
          "name": "scenes",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_scene_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_scene_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all_scenes_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_all_scenes_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.store_scene_response'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "5",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_scene_membership_response'>"
            }
          }
        },
        "0x0006": {
          "cluster_id": "0x0006",
          "title": "On/Off",
          "name": "on_off",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "0",
              "command_args": "'not_in_zcl'"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "2",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0008": {
          "cluster_id": "0x0008",
          "title": "Level control",
          "name": "level",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "0",
              "command_args": "'not_in_zcl'"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "2",
              "command_args": "'not_in_zcl'"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "3",
              "command_args": "'not_in_zcl'"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "4",
              "command_args": "'not_in_zcl'"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "5",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "6",
              "command_args": "'not_in_zcl'"
            },
            "0x07": {
              "command_id": "0x07",
              "command_name": "7",
              "command_args": "'not_in_zcl'"
            }
          }
        },
        "0x0102": {
          "cluster_id": "0x0102",
          "title": "Window Covering",
          "name": "window_covering",
          "attributes": {
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": ["0x21", "uint16_t", "Analog"],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "0",
              "command_args": "'not_in_zcl'"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "2",
              "command_args": "'not_in_zcl'"
            }
          }
        }
      }
    },
    {
      "id": 242,
      "device_type": "0x0061",
      "profile": "0xa1e0"
    }
  ]
}
```

</details>

#### CH10AX/SWITCH/1 ❌

<details>
  <summary>Signature</summary>

```json
{
  "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
  "endpoints": {
    "1": {
      "profile_id": 260,
      "device_type": "0x0100",
      "in_clusters": [
        "0x0000",
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0b05"
      ],
      "out_clusters": [
        "0x0019"
      ]
    },
    "21": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0003",
        "0x0b05",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0102"
      ]
    },
    "242": {
      "profile_id": 41440,
      "device_type": "0x0061",
      "in_clusters": [],
      "out_clusters": [
        "0x0021"
      ]
    }
  },
  "manufacturer": "Schneider Electric",
  "model": "CH10AX/SWITCH/1",
  "class": "zigpy.device.Device"
}
```

</details>

<details>
  <summary>zha_toolkit.scan_device</summary>

```json
{
  "ieee": "8c:f6:81:00z:00:00:00:00",
  "nwk": "0x26ce",
  "model": "CH10AX/SWITCH/1",
  "manufacturer": "Schneider Electric",
  "manufacturer_id": "0x4190",
  "endpoints": [
    {
      "id": 1,
      "device_type": "0x0100",
      "profile": "0x0104",
      "in_clusters": {
        "0x0000": {
          "cluster_id": "0x0000",
          "title": "Basic",
          "name": "basic",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "zcl_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "app_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "stack_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 6
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "hw_version",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "manufacturer",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "Schneider Electric"
            },
            "0x0005": {
              "attribute_id": "0x0005",
              "attribute_name": "model",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "CH10AX/SWITCH/1"
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "date_code",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "power_source",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "generic_device_class",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0009": {
              "attribute_id": "0x0009",
              "attribute_name": "generic_device_type",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 225
            },
            "0x000a": {
              "attribute_id": "0x000a",
              "attribute_name": "product_code",
              "value_type": [
                "0x41",
                "LVBytes",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": ""
            },
            "0x000b": {
              "attribute_id": "0x000b",
              "attribute_name": "product_url",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "http://www.schneider-electric.com"
            },
            "0x4000": {
              "attribute_id": "0x4000",
              "attribute_name": "sw_build_id",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": "002.010.007 R"
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "002.010.007 R"
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "001.000.000"
            },
            "0xe004": {
              "attribute_id": "0xe004",
              "attribute_name": "57348",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "333033423500000"
            },
            "0xe007": {
              "attribute_id": "0xe007",
              "attribute_name": "57351",
              "value_type": [
                "0x31",
                "enum16",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": 17432
            },
            "0xe008": {
              "attribute_id": "0xe008",
              "attribute_name": "57352",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Light"
            },
            "0xe009": {
              "attribute_id": "0xe009",
              "attribute_name": "57353",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "CH10AX/SWITCH/1"
            },
            "0xe00a": {
              "attribute_id": "0xe00a",
              "attribute_name": "57354",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190,
              "attribute_value": "Wiser Home"
            },
            "0xe00b": {
              "attribute_id": "0xe00b",
              "attribute_name": "57355",
              "value_type": [
                "0x42",
                "CharacterString",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "manf_id": 4190
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "reset_fact_default",
              "command_arguments": "<class 'zigpy.zcl.foundation.reset_fact_default'>"
            }
          },
          "commands_generated": {}
        },
        "0x0003": {
          "cluster_id": "0x0003",
          "title": "Identify",
          "name": "identify",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "identify_time",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 1
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "identify_query_response",
              "command_args": "<class 'zigpy.zcl.foundation.identify_query_response'>"
            }
          }
        },
        "0x0004": {
          "cluster_id": "0x0004",
          "title": "Groups",
          "name": "groups",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "name_support",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add",
              "command_arguments": "<class 'zigpy.zcl.foundation.add'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view",
              "command_arguments": "<class 'zigpy.zcl.foundation.view'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership",
              "command_arguments": "<class 'zigpy.zcl.foundation.get_membership'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "remove_all",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove_all'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "add_if_identifying",
              "command_arguments": "<class 'zigpy.zcl.foundation.add_if_identifying'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "get_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_membership_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_response'>"
            }
          }
        },
        "0x0005": {
          "cluster_id": "0x0005",
          "title": "Scenes",
          "name": "scenes",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "count",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "current_scene",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "current_group",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0003": {
              "attribute_id": "0x0003",
              "attribute_name": "scene_valid",
              "value_type": [
                "0x10",
                "Bool",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0004": {
              "attribute_id": "0x0004",
              "attribute_name": "name_support",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add",
              "command_arguments": "<class 'zigpy.zcl.foundation.add'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view",
              "command_arguments": "<class 'zigpy.zcl.foundation.view'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all",
              "command_arguments": "<class 'zigpy.zcl.foundation.remove_all'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store",
              "command_arguments": "<class 'zigpy.zcl.foundation.store'>"
            },
            "0x05": {
              "command_id": "0x05",
              "command_name": "recall",
              "command_arguments": "<class 'zigpy.zcl.foundation.recall'>"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership",
              "command_arguments": "<class 'zigpy.zcl.foundation.get_scene_membership'>"
            }
          },
          "commands_generated": {
            "0x00": {
              "command_id": "0x00",
              "command_name": "add_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.add_scene_response'>"
            },
            "0x01": {
              "command_id": "0x01",
              "command_name": "view_response",
              "command_args": "<class 'zigpy.zcl.foundation.view_response'>"
            },
            "0x02": {
              "command_id": "0x02",
              "command_name": "remove_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_scene_response'>"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "remove_all_scenes_response",
              "command_args": "<class 'zigpy.zcl.foundation.remove_all_scenes_response'>"
            },
            "0x04": {
              "command_id": "0x04",
              "command_name": "store_scene_response",
              "command_args": "<class 'zigpy.zcl.foundation.store_scene_response'>"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "get_scene_membership_response",
              "command_args": "<class 'zigpy.zcl.foundation.get_scene_membership_response'>"
            }
          }
        },
        "0x0006": {
          "cluster_id": "0x0006",
          "title": "On/Off",
          "name": "on_off",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "on_off",
              "value_type": [
                "0x10",
                "Bool",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x4001": {
              "attribute_id": "0x4001",
              "attribute_name": "on_time",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0x4002": {
              "attribute_id": "0x4002",
              "attribute_name": "off_wait_time",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "attribute_value": 0
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            },
            "0xe000": {
              "attribute_id": "0xe000",
              "attribute_name": "57344",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xe001": {
              "attribute_id": "0xe001",
              "attribute_name": "57345",
              "value_type": [
                "0x23",
                "uint32_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            },
            "0xe002": {
              "attribute_id": "0xe002",
              "attribute_name": "57346",
              "value_type": [
                "0x18",
                "bitmap8",
                "Discrete"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 1
            },
            "0xe003": {
              "attribute_id": "0xe003",
              "attribute_name": "57347",
              "value_type": [
                "0x23",
                "uint32_t",
                "Analog"
              ],
              "access": "REPORT|WRITE|READ",
              "access_acl": 7,
              "manf_id": 4190,
              "attribute_value": 0
            }
          },
          "commands_received": {},
          "commands_generated": {}
        },
        "0x0b05": {
          "cluster_id": "0x0b05",
          "title": "Diagnostic",
          "name": "diagnostic",
          "attributes": {
            "0x011c": {
              "attribute_id": "0x011c",
              "attribute_name": "last_message_lqi",
              "value_type": [
                "0x20",
                "uint8_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 124
            },
            "0x011d": {
              "attribute_id": "0x011d",
              "attribute_name": "last_message_rssi",
              "value_type": [
                "0x28",
                "int8s",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": -69
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "65533",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 2
            }
          },
          "commands_received": {},
          "commands_generated": {}
        }
      },
      "out_clusters": {
        "0x0019": {
          "cluster_id": "0x0019",
          "title": "Ota",
          "name": "ota",
          "attributes": {
            "0x0000": {
              "attribute_id": "0x0000",
              "attribute_name": "upgrade_server_id",
              "value_type": [
                "0xf0",
                "EUI64",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": [
                138,
                55,
                9,
                255,
                255,
                46,
                33,
                0
              ]
            },
            "0x0001": {
              "attribute_id": "0x0001",
              "attribute_name": "file_offset",
              "value_type": [
                "0x23",
                "uint32_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 4294967295
            },
            "0x0002": {
              "attribute_id": "0x0002",
              "attribute_name": "current_file_version",
              "value_type": [
                "0x23",
                "uint32_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 34211839
            },
            "0x0006": {
              "attribute_id": "0x0006",
              "attribute_name": "image_upgrade_status",
              "value_type": [
                "0x30",
                "enum8",
                "Discrete"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 0
            },
            "0x0007": {
              "attribute_id": "0x0007",
              "attribute_name": "manufacturer_id",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 4190
            },
            "0x0008": {
              "attribute_id": "0x0008",
              "attribute_name": "image_type_id",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 65535
            },
            "0xfffd": {
              "attribute_id": "0xfffd",
              "attribute_name": "cluster_revision",
              "value_type": [
                "0x21",
                "uint16_t",
                "Analog"
              ],
              "access": "REPORT|READ",
              "access_acl": 5,
              "attribute_value": 3
            }
          },
          "commands_received": {},
          "commands_generated": {
            "0x01": {
              "command_id": "0x01",
              "command_name": "1",
              "command_args": "'not_in_zcl'"
            },
            "0x03": {
              "command_id": "0x03",
              "command_name": "3",
              "command_args": "'not_in_zcl'"
            },
            "0x06": {
              "command_id": "0x06",
              "command_name": "6",
              "command_args": "'not_in_zcl'"
            }
          }
        }
      }
    }
  ]
}
```

</details>

#### FLS/AIRLINK/4 ❌

<details>
  <summary>Signature</summary>

```json
{
  "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
  "endpoints": {
    "21": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0001",
        "0x0003",
        "0x0020",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0019",
        "0x0102"
      ]
    },
    "22": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0001",
        "0x0003",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0102"
      ]
    },
    "23": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0001",
        "0x0003",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0102"
      ]
    },
    "24": {
      "profile_id": 260,
      "device_type": "0x0104",
      "in_clusters": [
        "0x0000",
        "0x0001",
        "0x0003",
        "0xff17"
      ],
      "out_clusters": [
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x0008",
        "0x0102"
      ]
    }
  },
  "manufacturer": "Schneider Electric",
  "model": "FLS/AIRLINK/4",
  "class": "zigpy.device.Device"
}
```

</details>

#### FLS/SYSTEM-M/4 ❔

#### LK Switch

#### NHPB/SWITCH/1 ❔

#### PUCK/SWITCH/1 ❔

<details>
  <summary>Jeedom logs</summary>
From [Jeedom community](https://community.jeedom.com/t/plugin-zigbee-beta-blabla/53420/700)

> Équipement non reconnu, module Switch Schneider Electric Wiser CCT5011-0002W

```json
{
  "ieee": "00:0d:6f:ff:fe:8f:c8:b1",
  "nwk": 59911,
  "status": 2,
  "lqi": "167",
  "rssi": "-73",
  "last_seen": "1617385752.2766984",
  "node_descriptor": "01:40:8e:5e:10:52:52:00:00:2c:52:00:00",
  "endpoints": [
    {
      "id": 1,
      "status": 1,
      "device_type": 256,
      "profile_id": 260,
      "manufacturer": "Schneider Electric",
      "model": "PUCK\/SWITCH\/1",
      "output_clusters": [
        {
          "id": 25,
          "name": "Ota",
          "attributes": []
        }
      ],
      "input_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": [
            {
              "id": 0,
              "name": "zcl_version",
              "value": 3
            },
            {
              "id": 1,
              "name": "app_version",
              "value": 2
            },
            {
              "id": 2,
              "name": "stack_version",
              "value": 6
            },
            {
              "id": 3,
              "name": "hw_version",
              "value": 1
            },
            {
              "id": 4,
              "name": "manufacturer",
              "value": "Schneider Electric"
            },
            {
              "id": 5,
              "name": "model",
              "value": "PUCK\/SWITCH\/1"
            },
            {
              "id": 6,
              "name": "date_code",
              "value": ""
            },
            {
              "id": 7,
              "name": "power_source",
              "value": 1
            },
            {
              "id": 16384,
              "name": "sw_build_id",
              "value": "002.004.018 R"
            }
          ]
        },
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 4,
          "name": "Groups",
          "attributes": []
        },
        {
          "id": 5,
          "name": "Scenes",
          "attributes": []
        },
        {
          "id": 6,
          "name": "On\/Off",
          "attributes": []
        },
        {
          "id": 2821,
          "name": "Diagnostic",
          "attributes": []
        }
      ]
    },
    {
      "id": 242,
      "status": 1,
      "device_type": 97,
      "profile_id": 41440,
      "manufacturer": null,
      "model": null,
      "output_clusters": [
        {
          "id": 33,
          "name": "GreenPowerProxy",
          "attributes": []
        }
      ],
      "input_clusters": []
    }
  ],
  "signature": {
    "manufacturer": "Schneider Electric",
    "model": "PUCK\/SWITCH\/1",
    "node_desc": {
      "byte1": 1,
      "byte2": 64,
      "mac_capability_flags": 142,
      "manufacturer_code": 4190,
      "maximum_buffer_size": 82,
      "maximum_incoming_transfer_size": 82,
      "server_mask": 11264,
      "maximum_outgoing_transfer_size": 82,
      "descriptor_capability_field": 0
    },
    "endpoints": {
      "1": {
        "profile_id": 260,
        "device_type": 256,
        "input_clusters": [
          0,
          3,
          4,
          5,
          6,
          2821
        ],
        "output_clusters": [
          25
        ]
      },
      "242": {
        "profile_id": 41440,
        "device_type": 97,
        "input_clusters": [],
        "output_clusters": [
          33
        ]
      }
    }
  },
  "class": "zigpy.device"
}
```

</details>

#### U201SRY2KWZB ❔

#### U202SRY2KWZB ❔

### Dimmer

#### CH/DIMMER/1 ❔

#### PUCK/DIMMER/1 ❔

<details>
  <summary>Jeedom logs</summary>

From [Jeedom community](https://community.jeedom.com/t/plugin-zigbee-beta-blabla/53420/700)

> Equipement reconnu, lumières dimmable module Schneider Electric Wiser CCT5010-0002W

```json
{
  "ieee": "90:fd:9f:ff:fe:7f:a3:70",
  "nwk": 26895,
  "status": 2,
  "lqi": "239",
  "rssi": "-64",
  "last_seen": "1617383914.5459597",
  "node_descriptor": "01:40:8e:5e:10:52:52:00:00:2c:52:00:00",
  "endpoints": [
    {
      "id": 3,
      "status": 1,
      "device_type": 257,
      "profile_id": 260,
      "manufacturer": "Schneider Electric",
      "model": "PUCK\/DIMMER\/1",
      "output_clusters": [
        {
          "id": 25,
          "name": "Ota",
          "attributes": []
        }
      ],
      "input_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": [
            {
              "id": 0,
              "name": "zcl_version",
              "value": 3
            },
            {
              "id": 1,
              "name": "app_version",
              "value": 2
            },
            {
              "id": 2,
              "name": "stack_version",
              "value": 6
            },
            {
              "id": 3,
              "name": "hw_version",
              "value": 1
            },
            {
              "id": 4,
              "name": "manufacturer",
              "value": "Schneider Electric"
            },
            {
              "id": 5,
              "name": "model",
              "value": "PUCK\/DIMMER\/1"
            },
            {
              "id": 6,
              "name": "date_code",
              "value": ""
            },
            {
              "id": 7,
              "name": "power_source",
              "value": 1
            },
            {
              "id": 16384,
              "name": "sw_build_id",
              "value": "002.004.018 R"
            }
          ]
        },
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 4,
          "name": "Groups",
          "attributes": []
        },
        {
          "id": 5,
          "name": "Scenes",
          "attributes": []
        },
        {
          "id": 6,
          "name": "On\/Off",
          "attributes": [
            {
              "id": 0,
              "name": "on_off",
              "value": 0
            }
          ]
        },
        {
          "id": 8,
          "name": "Level control",
          "attributes": [
            {
              "id": 0,
              "name": "current_level",
              "value": 254
            }
          ]
        },
        {
          "id": 769,
          "name": "Ballast",
          "attributes": []
        },
        {
          "id": 2821,
          "name": "Diagnostic",
          "attributes": []
        }
      ]
    },
    {
      "id": 242,
      "status": 1,
      "device_type": 97,
      "profile_id": 41440,
      "manufacturer": null,
      "model": null,
      "output_clusters": [
        {
          "id": 33,
          "name": "GreenPowerProxy",
          "attributes": []
        }
      ],
      "input_clusters": []
    }
  ],
  "signature": {
    "manufacturer": "Schneider Electric",
    "model": "PUCK\/DIMMER\/1",
    "node_desc": {
      "byte1": 1,
      "byte2": 64,
      "mac_capability_flags": 142,
      "manufacturer_code": 4190,
      "maximum_buffer_size": 82,
      "maximum_incoming_transfer_size": 82,
      "server_mask": 11264,
      "maximum_outgoing_transfer_size": 82,
      "descriptor_capability_field": 0
    },
    "endpoints": {
      "3": {
        "profile_id": 260,
        "device_type": 257,
        "input_clusters": [
          0,
          3,
          4,
          5,
          6,
          8,
          769,
          2821
        ],
        "output_clusters": [
          25
        ]
      },
      "242": {
        "profile_id": 41440,
        "device_type": 97,
        "input_clusters": [],
        "output_clusters": [
          33
        ]
      }
    }
  },
  "class": "zigpy.device"
}
```

</details>

#### LK Dimmer

#### NHPB/DIMMER/1 ❔

<details>
  <summary>Jeedom log</summary>

From [Jeedom community](https://community.jeedom.com/t/ajout-bp-dimmer-schneider-wiser/62657)

```json
{
  "ieee": "68:0a:e2:ff:fe:0e:6c:35",
  "nwk": 41197,
  "status": 2,
  "lqi": "192",
  "rssi": "-52",
  "last_seen": "1622797736.8228328",
  "node_descriptor": "01:40:8e:5e:10:52:52:00:00:2c:52:00:00",
  "endpoints": [
    {
      "id": 3,
      "status": 1,
      "device_type": 257,
      "profile_id": 260,
      "manufacturer": "Schneider Electric",
      "model": "NHPB\/DIMMER\/1",
      "output_clusters": [
        {
          "id": 25,
          "name": "Ota",
          "attributes": []
        }
      ],
      "input_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": [
            {
              "id": 0,
              "name": "zcl_version",
              "value": 3
            },
            {
              "id": 1,
              "name": "app_version",
              "value": 2
            },
            {
              "id": 2,
              "name": "stack_version",
              "value": 6
            },
            {
              "id": 3,
              "name": "hw_version",
              "value": 1
            },
            {
              "id": 4,
              "name": "manufacturer",
              "value": "Schneider Electric"
            },
            {
              "id": 5,
              "name": "model",
              "value": "NHPB\/DIMMER\/1"
            },
            {
              "id": 6,
              "name": "date_code",
              "value": ""
            },
            {
              "id": 7,
              "name": "power_source",
              "value": 1
            },
            {
              "id": 16384,
              "name": "sw_build_id",
              "value": "002.004.015 R"
            }
          ]
        },
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 4,
          "name": "Groups",
          "attributes": []
        },
        {
          "id": 5,
          "name": "Scenes",
          "attributes": []
        },
        {
          "id": 6,
          "name": "On\/Off",
          "attributes": [
            {
              "id": 0,
              "name": "on_off",
              "value": 0
            }
          ]
        },
        {
          "id": 8,
          "name": "Level control",
          "attributes": [
            {
              "id": 0,
              "name": "current_level",
              "value": 146
            }
          ]
        },
        {
          "id": 769,
          "name": "Ballast",
          "attributes": []
        },
        {
          "id": 2821,
          "name": "Diagnostic",
          "attributes": []
        }
      ]
    },
    {
      "id": 21,
      "status": 1,
      "device_type": 260,
      "profile_id": 260,
      "manufacturer": "Schneider Electric",
      "model": "NHPB\/DIMMER\/1",
      "output_clusters": [
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 4,
          "name": "Groups",
          "attributes": []
        },
        {
          "id": 5,
          "name": "Scenes",
          "attributes": []
        },
        {
          "id": 6,
          "name": "On\/Off",
          "attributes": []
        },
        {
          "id": 8,
          "name": "Level control",
          "attributes": []
        },
        {
          "id": 258,
          "name": "Window Covering",
          "attributes": []
        }
      ],
      "input_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": [
            {
              "id": 0,
              "name": "zcl_version",
              "value": 3
            },
            {
              "id": 1,
              "name": "app_version",
              "value": 2
            },
            {
              "id": 2,
              "name": "stack_version",
              "value": 6
            },
            {
              "id": 3,
              "name": "hw_version",
              "value": 1
            },
            {
              "id": 4,
              "name": "manufacturer",
              "value": "Schneider Electric"
            },
            {
              "id": 5,
              "name": "model",
              "value": "NHPB\/DIMMER\/1"
            },
            {
              "id": 6,
              "name": "date_code",
              "value": ""
            },
            {
              "id": 7,
              "name": "power_source",
              "value": 1
            },
            {
              "id": 16384,
              "name": "sw_build_id",
              "value": "002.004.015 R"
            }
          ]
        },
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 2821,
          "name": "Diagnostic",
          "attributes": []
        },
        {
          "id": 65303,
          "name": "Manufacturer Specific",
          "attributes": []
        }
      ]
    },
    {
      "id": 242,
      "status": 1,
      "device_type": 97,
      "profile_id": 41440,
      "manufacturer": null,
      "model": null,
      "output_clusters": [
        {
          "id": 33,
          "name": "GreenPowerProxy",
          "attributes": []
        }
      ],
      "input_clusters": []
    }
  ],
  "signature": {
    "manufacturer": "Schneider Electric",
    "model": "NHPB\/DIMMER\/1",
    "node_desc": {
      "byte1": 1,
      "byte2": 64,
      "mac_capability_flags": 142,
      "manufacturer_code": 4190,
      "maximum_buffer_size": 82,
      "maximum_incoming_transfer_size": 82,
      "server_mask": 11264,
      "maximum_outgoing_transfer_size": 82,
      "descriptor_capability_field": 0
    },
    "endpoints": {
      "3": {
        "profile_id": 260,
        "device_type": 257,
        "input_clusters": [
          0,
          3,
          4,
          5,
          6,
          8,
          769,
          2821
        ],
        "output_clusters": [
          25
        ]
      },
      "21": {
        "profile_id": 260,
        "device_type": 260,
        "input_clusters": [
          0,
          3,
          2821,
          65303
        ],
        "output_clusters": [
          3,
          4,
          5,
          6,
          8,
          258
        ]
      },
      "242": {
        "profile_id": 41440,
        "device_type": 97,
        "input_clusters": [],
        "output_clusters": [
          33
        ]
      }
    }
  },
  "class": "zigpy.device"
}
```

</details>

#### NHROTARY/DIMMER/1 ❔

#### U201DST600ZB ❔

#### U202DST600ZB ❔

### Plug

#### CH/Socket/2 ❔

#### EH-ZB-SPD-V2 ❔

#### LK/OUTLET/1 ❔

#### SOCKET/OUTLET/1 ❔

#### SOCKET/OUTLET/2 ❔

#### SMARTPLUG/1 ❔

### Thermostat

#### CCTFR6700 ❔

From [Jeedom community](https://community.jeedom.com/t/plugin-zigbee-schneider-wiser-cctfr6700/582050)

#### EH-ZB-VACT ❔

#### EH-ZB-RTS ❔

#### EH-ZB-HACT ❔

#### Thermostat ❔

<details>
  <summary>Jeedom logs</summary>

From [Jeedom community](https://community.jeedom.com/t/plugin-zigbee-beta-blabla/53420/700)

> Thermostat schneider modèle CCTFR6400 reconnu mais l’humidité ne remonte pas en valeur.
> En modifiant la valeur du LogicalID en 1::1029::0 j’ai bien le retour de la valeur.

> (c’est bien le 38:: qu’il faut passer en 1:: )

```json
{
  "ieee": "68:0a:e2:ff:fe:f0:3d:ec",
  "nwk": 4006,
  "status": 2,
  "lqi": "255",
  "rssi": "-61",
  "last_seen": "1617387095.1353316",
  "node_descriptor": "02:40:80:5e:10:52:52:00:00:00:52:00:00",
  "endpoints": [
    {
      "id": 1,
      "status": 1,
      "device_type": 770,
      "profile_id": 260,
      "manufacturer": "Schneider Electric",
      "model": "Thermostat",
      "output_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": []
        },
        {
          "id": 25,
          "name": "Ota",
          "attributes": []
        },
        {
          "id": 513,
          "name": "Thermostat",
          "attributes": []
        }
      ],
      "input_clusters": [
        {
          "id": 0,
          "name": "Basic",
          "attributes": [
            {
              "id": 0,
              "name": "zcl_version",
              "value": 2
            },
            {
              "id": 1,
              "name": "app_version",
              "value": 0
            },
            {
              "id": 3,
              "name": "hw_version",
              "value": 1
            },
            {
              "id": 4,
              "name": "manufacturer",
              "value": "Schneider Electric"
            },
            {
              "id": 5,
              "name": "model",
              "value": "Thermostat"
            },
            {
              "id": 7,
              "name": "power_source",
              "value": 3
            },
            {
              "id": 16384,
              "name": "sw_build_id",
              "value": "bc271cf"
            }
          ]
        },
        {
          "id": 1,
          "name": "Power Configuration",
          "attributes": []
        },
        {
          "id": 3,
          "name": "Identify",
          "attributes": []
        },
        {
          "id": 32,
          "name": "Poll Control",
          "attributes": [
            {
              "id": 0,
              "name": "checkin_interval",
              "value": 14400
            }
          ]
        },
        {
          "id": 516,
          "name": "Thermostat User Interface Configuration",
          "attributes": []
        },
        {
          "id": 1026,
          "name": "Temperature Measurement",
          "attributes": [
            {
              "id": 0,
              "name": "measured_value",
              "value": 2628
            }
          ]
        },
        {
          "id": 1029,
          "name": "Relative Humidity Measurement",
          "attributes": [
            {
              "id": 0,
              "name": "measured_value",
              "value": 3780
            }
          ]
        },
        {
          "id": 2821,
          "name": "Diagnostic",
          "attributes": [
            {
              "id": 284,
              "name": "last_message_lqi",
              "value": 208
            },
            {
              "id": 285,
              "name": "last_message_rssi",
              "value": -48
            }
          ]
        },
        {
          "id": 65027,
          "name": "Manufacturer Specific",
          "attributes": []
        }
      ]
    }
  ],
  "signature": {
    "manufacturer": "Schneider Electric",
    "model": "Thermostat",
    "node_desc": {
      "byte1": 2,
      "byte2": 64,
      "mac_capability_flags": 128,
      "manufacturer_code": 4190,
      "maximum_buffer_size": 82,
      "maximum_incoming_transfer_size": 82,
      "server_mask": 0,
      "maximum_outgoing_transfer_size": 82,
      "descriptor_capability_field": 0
    },
    "endpoints": {
      "1": {
        "profile_id": 260,
        "device_type": 770,
        "input_clusters": [
          0,
          1,
          3,
          32,
          516,
          1026,
          1029,
          2821,
          65027
        ],
        "output_clusters": [
          0,
          25,
          513
        ]
      }
    }
  },
  "class": "zigpy.device"
}
```

</details>

#### iTRV ❔

### Motion

#### CCT595011_AS ❔

#### NHMOTION/SWITCH/1 ❔

### MISC

#### CCT592011_AS ❔

#### EH-ZB-LMACT ❔
