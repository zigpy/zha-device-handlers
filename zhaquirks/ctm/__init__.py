"""Quirks for CTM Lyng products."""

from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff

CTM_MANUF_NAME = "CTM Lyng"
CTM_MANUF_CODE = 0x1337


class AlarmStatus(t.enum8):
    """Alarm status of the cooktop guard."""

    OK = 0x00
    Tamper = 0x01
    HighTemperature = 0x02
    Timer = 0x03
    BatteryAlarm = 0x07
    Error = 0x08


class BatteryStatus(t.enum8):
    """Battery alarm status of the cooktop guard."""

    OK = 0x00
    BatteryAlarm = 0x01


class ActiveStatus(t.enum8):
    """Active status of the cooktop guard (In use)."""

    Inactive = 0x00
    Active = 0x01


class CTMDiagnosticsCluster(CustomCluster):
    """CTM Lyng custom diagnostics cluster."""

    name = "CTMDiagnostics"
    cluster_id = 0xFEED

    class AttributeDefs(CustomCluster.AttributeDefs):
        """CTM Lyng custom diagnostics cluster attribute definitions."""

        ctm_last_reset_info: Final = foundation.ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_last_extended_reset_info: Final = foundation.ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_reboot_counter: Final = foundation.ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_last_hop_lqi: Final = foundation.ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_last_hop_rssi: Final = foundation.ZCLAttributeDef(
            id=0x0004,
            type=t.int8s,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_tx_power: Final = foundation.ZCLAttributeDef(
            id=0x0005,
            type=t.int8s,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_parent_node_id: Final = foundation.ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_button_0_click_counter: Final = foundation.ZCLAttributeDef(
            id=0x0010,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_button_0_ms_click_duration: Final = foundation.ZCLAttributeDef(
            id=0x0020,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_debug_int: Final = foundation.ZCLAttributeDef(
            id=0x0401,
            type=t.uint32_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_cluster_revision: Final = foundation.ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )


class CTMCooktopGuardCluster(CustomCluster):
    """CTM Lyng custom cooktop guard cluster."""

    name = "CtmCooktopGuard"
    cluster_id = 0xFFC9

    class AttributeDefs(CustomCluster.AttributeDefs):
        """CTM Lyng cooktop guard cluster attribute definitions."""

        ctm_alarm_status: Final = foundation.ZCLAttributeDef(
            id=0x0001,
            type=AlarmStatus,
            zcl_type=foundation.DataTypeId.uint8,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_battery_status: Final = foundation.ZCLAttributeDef(
            id=0x0002,
            type=BatteryStatus,
            zcl_type=foundation.DataTypeId.uint8,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_temperature: Final = foundation.ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_ambient_temperature: Final = foundation.ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_active_status: Final = foundation.ZCLAttributeDef(
            id=0x0005,
            type=ActiveStatus,
            zcl_type=foundation.DataTypeId.uint8,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_runtime: Final = foundation.ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_runtime_timeout: Final = foundation.ZCLAttributeDef(
            id=0x0007,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_reset_reason: Final = foundation.ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_dip_switch: Final = foundation.ZCLAttributeDef(
            id=0x0009,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_software_version: Final = foundation.ZCLAttributeDef(
            id=0x000A,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_hardware_version: Final = foundation.ZCLAttributeDef(
            id=0x000B,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_bootloader_version: Final = foundation.ZCLAttributeDef(
            id=0x000C,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_model: Final = foundation.ZCLAttributeDef(
            id=0x000D,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_paired_with_address: Final = foundation.ZCLAttributeDef(
            id=0x0010,
            type=t.EUI64,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_relay_current_flag: Final = foundation.ZCLAttributeDef(
            id=0x0100,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_relay_current: Final = foundation.ZCLAttributeDef(
            id=0x0101,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_relay_status: Final = foundation.ZCLAttributeDef(
            id=0x0102,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_relay_ext_button: Final = foundation.ZCLAttributeDef(
            id=0x0103,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_relay_alarm: Final = foundation.ZCLAttributeDef(
            id=0x0104,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_relay_sensor_alarm: Final = foundation.ZCLAttributeDef(
            id=0x0105,
            type=AlarmStatus,
            access="r",
            is_manufacturer_specific=True,
        )
        ctm_cluster_revision: Final = foundation.ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(CustomCluster.ServerCommandDefs):
        """Server command definitions."""

        ctm_pair_with_relay: Final = foundation.ZCLCommandDef(
            id=0x0,
            schema={
                "sensorAddress": t.EUI64,
            },
            is_manufacturer_specific=True,
        )
        ctm_relay_status_request: Final = foundation.ZCLCommandDef(
            id=0x2,
            schema={},
            is_manufacturer_specific=True,
        )
        ctm_on_command: Final = foundation.ZCLCommandDef(
            id=0x4,
            schema={},
            is_manufacturer_specific=True,
        )
        ctm_alarm_command: Final = foundation.ZCLCommandDef(
            id=0x6,
            schema={
                "alarmCode": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )

    class ClientCommandDefs(CustomCluster.ClientCommandDefs):
        """Client command definitions."""

        ctm_pair_with_sensor: Final = foundation.ZCLCommandDef(
            id=0x1,
            schema={
                "relayAddress": t.EUI64,
            },
            is_manufacturer_specific=True,
        )
        ctm_relay_status: Final = foundation.ZCLCommandDef(
            id=0x3,
            schema={
                "relayStatus": t.uint8_t,
                "currentFlag": t.uint8_t,
                "current": t.uint8_t,
                "externalButton": t.uint8_t,
                "sensorAlarm": t.uint8_t,
                "relayAlarm": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )


class CTMOnOffCluster(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    class AttributeDefs(OnOff.AttributeDefs):
        """CTM Lyng custom on/off cluster attribute definitions."""

        ctm_current_flag: Final = foundation.ZCLAttributeDef(
            id=0x5000,
            type=t.uint8_t,
            access="r",
            is_manufacturer_specific=True,
        )
