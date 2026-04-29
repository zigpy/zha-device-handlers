"""Quirks for CTM Lyng products."""

from typing import Final

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

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


class CTMDiagnosticsCluster(CustomCluster):
    """CTM Lyng custom diagnostics cluster."""

    name = "CTMDiagnostics"
    cluster_id = 0xFEED
    ep_attribute = "ctm_diagnostics"

    class AttributeDefs(BaseAttributeDefs):
        """CTM Lyng custom diagnostics cluster attribute definitions."""

        ctm_last_reset_info: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_last_extended_reset_info: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_reboot_counter: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_last_hop_lqi: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_last_hop_rssi: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.int8s,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_tx_power: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.int8s,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_parent_node_id: Final = ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_button_0_click_counter: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_button_0_ms_click_duration: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_debug_int: Final = ZCLAttributeDef(
            id=0x0401,
            type=t.uint32_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )


class CTMCooktopGuardCluster(CustomCluster):
    """CTM Lyng custom cooktop guard cluster."""

    name = "CTMCooktopGuard"
    cluster_id = 0xFFC9
    ep_attribute = "ctm_cooktop_guard"

    class AttributeDefs(BaseAttributeDefs):
        """CTM Lyng cooktop guard cluster attribute definitions."""

        ctm_alarm_status: Final = ZCLAttributeDef(
            id=0x0001,
            type=AlarmStatus,
            zcl_type=DataTypeId.uint8,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_battery_alarm: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_cooktop_temperature: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_ambient_temperature: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_cooktop_active: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_runtime: Final = ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_runtime_timeout: Final = ZCLAttributeDef(
            id=0x0007,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_reset_reason: Final = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_dip_switch: Final = ZCLAttributeDef(
            id=0x0009,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_software_version: Final = ZCLAttributeDef(
            id=0x000A,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_hardware_version: Final = ZCLAttributeDef(
            id=0x000B,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_bootloader_version: Final = ZCLAttributeDef(
            id=0x000C,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_model: Final = ZCLAttributeDef(
            id=0x000D,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_paired_with_address: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.EUI64,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_relay_current_flag: Final = ZCLAttributeDef(
            id=0x0100,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_relay_current: Final = ZCLAttributeDef(
            id=0x0101,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_relay_status: Final = ZCLAttributeDef(
            id=0x0102,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_relay_ext_button: Final = ZCLAttributeDef(
            id=0x0103,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_relay_alarm: Final = ZCLAttributeDef(
            id=0x0104,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_relay_sensor_alarm: Final = ZCLAttributeDef(
            id=0x0105,
            type=AlarmStatus,
            zcl_type=DataTypeId.uint8,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
        ctm_cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions (commands received by the server)."""

        ctm_pair_with_sensor: Final = ZCLCommandDef(
            id=0x1,
            schema={
                "relayAddress": t.EUI64,
            },
            is_manufacturer_specific=True,
        )
        ctm_relay_status: Final = ZCLCommandDef(
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

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions (commands generated by the server)."""

        ctm_pair_with_relay: Final = ZCLCommandDef(
            id=0x0,
            schema={
                "sensorAddress": t.EUI64,
            },
            is_manufacturer_specific=True,
        )
        ctm_relay_status_request: Final = ZCLCommandDef(
            id=0x2,
            schema={},
            is_manufacturer_specific=True,
        )
        ctm_on_command: Final = ZCLCommandDef(
            id=0x4,
            schema={},
            is_manufacturer_specific=True,
        )
        ctm_alarm_command: Final = ZCLCommandDef(
            id=0x6,
            schema={
                "alarmCode": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )


class CTMOnOffCluster(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    class AttributeDefs(OnOff.AttributeDefs):
        """CTM Lyng custom on/off cluster attribute definitions."""

        ctm_current_flag: Final = ZCLAttributeDef(
            id=0x5000,
            type=t.uint8_t,
            access="r",
            manufacturer_code=CTM_MANUF_CODE,
        )
