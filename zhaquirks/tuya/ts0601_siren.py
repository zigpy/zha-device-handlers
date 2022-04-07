"""Map from manufacturer to standard clusters for the NEO Siren device."""
import logging
from typing import Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from zhaquirks import Bus, LocalDataCluster
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
    TuyaDPType,
    TuyaMCUCluster,
)

TUYA_BATTERY_ATTR = 0x020F  # [0, 0, 0, 100] battery percentage
TUYA_ALARM_ATTR = 0x0168  # [0]/[1] Alarm!
TUYA_TEMP_ALARM_ATTR = 0x0171  # [0]/[1] Disable/Enable alarm by temperature
TUYA_HUMID_ALARM_ATTR = 0x0172  # [0]/[1] Disable/Enable alarm by humidity
TUYA_ALARM_DURATION_ATTR = 0x0267  # [0,0,0,10] alarm duration in seconds: 0-1800
TUYA_TEMPERATURE_ATTR = 0x0269  # [0,0,0,240] temperature in decidegree
TUYA_HUMIDITY_ATTR = 0x026A  # [0,0,0,36] humidity
TUYA_ALARM_MIN_TEMP_ATTR = 0x026B  # [0,0,0,18] min alarm temperature threshold
TUYA_ALARM_MAX_TEMP_ATTR = 0x026C  # [0,0,0,18] max alarm temperature threshold
TUYA_ALARM_MIN_HUMID_ATTR = 0x026D  # [0,0,0,18] min alarm humidity threshold
TUYA_ALARM_MAX_HUMID_ATTR = 0x026E  # [0,0,0,18] max alarm humidity threshold
TUYA_MELODY_ATTR = 0x0466  # [5] Melody
TUYA_VOLUME_ATTR = 0x0474  # [0]/[1]/[2] Volume 0-low, 2-high

_LOGGER = logging.getLogger(__name__)


class NeoAlarmVolume(t.enum8):
    """Neo alarm volume enum."""

    low = 0x00
    medium = 0x01
    high = 0x02


class NeoAlarmMelody(t.enum8):
    """Neo alarm melody enum."""

    melody_01 = 0x01
    melody_02 = 0x02
    melody_03 = 0x03
    melody_04 = 0x04
    melody_05 = 0x05
    melody_06 = 0x06
    melody_07 = 0x07
    melody_08 = 0x08
    melody_09 = 0x09
    melody_10 = 0x0A
    melody_11 = 0x0B
    melody_12 = 0x0C
    melody_13 = 0x0D
    melody_14 = 0x0E
    melody_15 = 0x0F
    melody_16 = 0x10
    melody_17 = 0x11
    melody_18 = 0x12


class TuyaManufClusterSiren(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the NEO Siren device."""

    attributes = TuyaManufClusterAttributes.attributes.copy()
    attributes.update(
        {
            TUYA_ALARM_ATTR: ("alarm", t.uint8_t, True),
            TUYA_TEMP_ALARM_ATTR: ("enable_temperature_alarm", t.uint8_t, True),
            TUYA_HUMID_ALARM_ATTR: ("enable_humidity_alarm", t.uint8_t, True),
            TUYA_ALARM_DURATION_ATTR: ("alarm_duration", t.uint32_t, True),
            TUYA_TEMPERATURE_ATTR: ("temperature", t.uint32_t, True),
            TUYA_HUMIDITY_ATTR: ("humidity", t.uint32_t, True),
            TUYA_ALARM_MIN_TEMP_ATTR: ("alarm_temperature_min", t.uint32_t, True),
            TUYA_ALARM_MAX_TEMP_ATTR: ("alarm_temperature_max", t.uint32_t, True),
            TUYA_ALARM_MIN_HUMID_ATTR: ("alarm_humidity_min", t.uint32_t, True),
            TUYA_ALARM_MAX_HUMID_ATTR: ("alarm_humidity_max", t.uint32_t, True),
            TUYA_MELODY_ATTR: ("melody", t.uint8_t, True),
            TUYA_VOLUME_ATTR: ("volume", t.uint8_t, True),
        }
    )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_TEMPERATURE_ATTR:
            self.endpoint.device.temperature_bus.listener_event(
                "temperature_reported", value * 10  # decidegree to centidegree
            )
        elif attrid == TUYA_HUMIDITY_ATTR:
            self.endpoint.device.humidity_bus.listener_event(
                "humidity_reported", value * 100  # whole percentage to 1/1000th
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


class TuyaTemperatureMeasurement(LocalDataCluster, TemperatureMeasurement):
    """Temperature cluster acting from events from temperature bus."""

    cluster_id = TemperatureMeasurement.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.temperature_bus.add_listener(self)

    def temperature_reported(self, value):
        """Temperature reported."""
        self._update_attribute(self.ATTR_ID, value)


class TuyaRelativeHumidity(LocalDataCluster, RelativeHumidity):
    """Humidity cluster acting from events from humidity bus."""

    cluster_id = RelativeHumidity.cluster_id
    ATTR_ID = 0

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.humidity_bus.add_listener(self)

    def humidity_reported(self, value):
        """Humidity reported."""
        self._update_attribute(self.ATTR_ID, value)


class TuyaSiren(CustomDevice):
    """NEO Tuya Siren and humidity/temperature sensor."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.temperature_bus = Bus()
        self.humidity_bus = Bus()
        self.switch_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_d0yu2xgi", "0yu2xgi")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    TuyaManufClusterSiren,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                    TuyaSirenOnOff,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaSiren2(TuyaSiren):
    """NEO Tuya Siren and humidity/temperature sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[25, 10]>
        MODELS_INFO: [("_TZE200_d0yu2xgi", "TS0601")],
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
            }
        },
    }


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
                cluster_attr="on_off",
                attr_value=command_id,
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
        5: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "volume",
            dp_type=TuyaDPType.ENUM,
            converter=lambda x: NeoAlarmVolume(x),
        ),
        7: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "alarm_duration",
            dp_type=TuyaDPType.VALUE,
        ),
        13: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
        ),
        15: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "battery",
            dp_type=TuyaDPType.VALUE,
        ),
        21: DPToAttributeMapping(
            TuyaMCUSiren.ep_attribute,
            "melody",
            dp_type=TuyaDPType.ENUM,
            converter=lambda x: NeoAlarmMelody(x),
        ),
    }

    data_point_handlers = {
        13: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
        21: "_dp_2_attr_update",
    }


class TuyaSirenGPP_NoSensors(CustomDevice):
    """NEO Tuya Siren without sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=1 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[25, 10]>
        MODELS_INFO: [("_TZE200_t1blo2bj", "TS0601")],
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
                DEVICE_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoSirenManufCluster,
                    TuyaMCUSiren,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
