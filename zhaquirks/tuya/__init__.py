"""Tuya devices."""

from zigpy.quirks import CustomCluster
import zigpy.types as t

TUYA_CLUSTER_ID = 0xEF00


class Data(t.List, item_type=t.uint8_t):
    """list of uint8_t."""


class TuyaManufCluster(CustomCluster):
    """Tuya manufacturer specific cluster."""

    name = "Tuya Manufacturer Specicific"
    cluster_id = TUYA_CLUSTER_ID
    ep_attribute = "tuya_manufacturer"

    class Command(t.Struct):
        """Tuya manufacturer cluster command."""

        status: t.uint8_t
        tsn: t.uint8_t
        command_id: t.uint16_t
        function: t.uint8_t
        data: Data

    manufacturer_server_commands = {0x0000: ("set_data", (Command,), False)}

    manufacturer_client_commands = {
        0x0001: ("get_data", (Command,), True),
        0x0002: ("set_data_response", (Command,), True),
    }
