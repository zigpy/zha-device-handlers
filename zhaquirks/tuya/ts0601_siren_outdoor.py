"""Map from manufacturer to standard clusters for the NEO Siren device."""
import logging
from typing import Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, Ota, Scenes, Time

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaManufCluster, TuyaManufClusterAttributes
from zhaquirks.tuya.mcu import (
    TUYA_MCU_COMMAND,
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaClusterData,
    TuyaMCUCluster,
)

# TUYA_SET_DATA = 0x00
# TUYA_GET_DATA = 0x01
# TUYA_SET_DATA_RESPONSE = 0x02
# TUYA_SEND_DATA = 0x04

TUYA_BATTERY_ATTR = 0x020F  # [0, 0, 0, 100] battery percentage
TUYA_ALARM_ATTR = 0x0168  # [0]/[1] Alarm!
TUYA_ALARM_DURATION_ATTR = 0x0267  # [0,0,0,10] alarm duration in seconds: 0-1800
TUYA_MELODY_ATTR = 0x0466  # [5] Melody
TUYA_VOLUME_ATTR = 0x0474  # [0]/[1]/[2] Volume 0-low, 2-high
TUYA_TAMPER_ATTR = 0x0000
TUYA_TAMPER_ALARM_ATTR = 0x0000
TUYA_ALARM_MODE_ATTR = 0x0000
TUYA_CHARGE_STATE_ATTR = 0x0000
TUYA_ALARM_STATE_ATTR = 0x0000

_LOGGER = logging.getLogger(__name__)


class NeoAlarmVolume(t.enum8):
    """Neo alarm volume enum."""

    low = 0x00
    medium = 0x01
    high = 0x02


class NeoAlarmMelody(t.enum8):
    """Neo Outdoor alarm melody enum."""

    melody_01 = 0x00
    melody_02 = 0x01
    melody_03 = 0x02


class NeoAlarmMode(t.enum8):
    """Neo alarm Mode enum."""

    alarm_sound = 0x00
    alarm_light = 0x01
    alarm_both = 0x02


class NeoAlarmState(t.enum8):
    """Neo alarm Mode enum."""

    alarm_sound = 0x00
    alarm_light = 0x01
    alarm_both = 0x02
    normal = 0x03


class TuyaManufClusterSiren(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the NEO Siren device."""

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            TUYA_ALARM_ATTR: ("alarm", t.uint8_t, True),
            TUYA_ALARM_STATE_ATTR: ("alarm_state", t.uint8_t, True),
            TUYA_ALARM_DURATION_ATTR: ("alarm_duration", t.uint32_t, True),
            TUYA_MELODY_ATTR: ("melody", t.uint8_t, True),
            TUYA_VOLUME_ATTR: ("volume", t.uint8_t, True),
            TUYA_TAMPER_ATTR: ("tamper", t.uint8_t, True),
            TUYA_TAMPER_ALARM_ATTR: ("tamper_alarm", t.uint8_t, True),
            TUYA_ALARM_MODE_ATTR: ("mode", t.uint8_t, True),
        }
    )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_CHARGE_STATE_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                "switch_event", value  # boolean 1=on / 0=off
            )
        elif attrid == TUYA_TAMPER_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                "switch_event", value  # boolean 1=on / 0=off
            )

        elif attrid == TUYA_ALARM_ATTR:
            self.endpoint.device.switch_bus.listener_event(
                "switch_event", value  # boolean 1=on / 0=off
            )


class TuyaSirenOnOff(LocalDataCluster, OnOff):
    """Tuya On/Off cluster for siren device."""

    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.switch_bus.add_listener(self)

    def switch_event(self, state):
        """Switch event."""
        self._update_attribute(self.ATTR_ID, state)

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default command and defer to the alarm attribute."""

        if command_id in (0x0000, 0x0001):
            (res,) = await self.endpoint.tuya_manufacturer.write_attributes(
                {TUYA_ALARM_ATTR: command_id}, manufacturer=manufacturer
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res[0].status)

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class TuyaMCUSiren(OnOff, TuyaAttributesCluster):
    """Tuya MCU cluster for siren device."""

    attributes = OnOff.attributes.copy()
    attributes.update(
        {
            TUYA_BATTERY_ATTR: ("battery", t.uint32_t, True),
            TUYA_ALARM_ATTR: ("alarm", t.uint8_t, True),
            TUYA_ALARM_DURATION_ATTR: ("alarm_duration", t.uint32_t, True),
            TUYA_MELODY_ATTR: ("melody", NeoAlarmMelody, True),
            TUYA_VOLUME_ATTR: ("volume", NeoAlarmVolume, True),
            TUYA_ALARM_STATE_ATTR: ("alarm_state", NeoAlarmState, True),
            TUYA_TAMPER_ATTR: ("tamper", t.uint8_t, True),
            TUYA_TAMPER_ALARM_ATTR: ("tamper_alarm", t.uint8_t, True),
            TUYA_ALARM_MODE_ATTR: ("mode", NeoAlarmMode, True),
            TUYA_CHARGE_STATE_ATTR: ("charge_state", t.uint8_t, True),
        }
    )

    async def write_attributes(self, attributes, manufacturer=None):
        """Overwrite to force manufacturer code."""

        return await super().write_attributes(
            attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
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

        # (off, on)
        if command_id in (0x0000, 0x0001):
            cluster_data = TuyaClusterData(
                endpoint_id=self.endpoint.endpoint_id,
                cluster_name=self.ep_attribute,
                cluster_attr="on_off",
                attr_value=bool(command_id),
                expect_reply=expect_reply,
                manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID,
            )
            self.endpoint.device.command_bus.listener_event(
                TUYA_MCU_COMMAND,
                cluster_data,
            )
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=foundation.Status.SUCCESS)

        self.warning("Unsupported command_id: %s", command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.UNSUP_CLUSTER_COMMAND)


class NeoSirenManufCluster(TuyaMCUCluster):
    """Tuya with NEO Siren data points."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "alarm_state",
            converter=lambda x: NeoAlarmState(x),
        ),
        7: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "alarm_duration",
        ),
        13: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "on_off",
        ),
        15: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "battery",
        ),
        6: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "charge_state",
        ),
        21: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "melody",
            converter=lambda x: NeoAlarmMelody(x),
        ),
        101: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "tamper_alarm_switch",
        ),
        102: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "mode",
            converter=lambda x: NeoAlarmMode(x),
        ),
        20: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "tamper_alarm",
        ),
    }

    data_point_handlers = {
        13: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
        21: "_dp_2_attr_update",
    }


class TuyaSirenOutdoor_NoSensors(CustomDevice):
    """NEO Tuya Siren without sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[25, 10]>
        MODELS_INFO: [
            ("_TZE200_nlrfgpny", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoSirenManufCluster,
                    TuyaMCUSiren,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            }
        }
    }
