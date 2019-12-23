"""Class to control Xbee3 device."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import AnalogInput

from . import XBEE_PROFILE_ID, XBeeCommon, XBeeOnOff
from ..const import DEVICE_TYPE, ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS, PROFILE_ID


class XBee3Sensor(XBeeCommon):
    """XBee3 Sensor."""

    def __init__(self, application, ieee, nwk, replaces):
        """Initialize device-specific properties."""
        self.replacement[ENDPOINTS].update(
            {
                0xD0: {
                    "manufacturer": "XBEE",
                    "model": "AD0/DIO0/Commissioning",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff, AnalogInput],
                    OUTPUT_CLUSTERS: [],
                },
                0xD1: {
                    "manufacturer": "XBEE",
                    "model": "AD1/DIO1/SPI_nATTN",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff, AnalogInput],
                    OUTPUT_CLUSTERS: [],
                },
                0xD2: {
                    "manufacturer": "XBEE",
                    "model": "AD2/DIO2/SPI_CLK",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff, AnalogInput],
                    OUTPUT_CLUSTERS: [],
                },
                0xD3: {
                    "manufacturer": "XBEE",
                    "model": "AD3/DIO3",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff, AnalogInput],
                    OUTPUT_CLUSTERS: [],
                },
                0xD4: {
                    "manufacturer": "XBEE",
                    "model": "DIO4/SPI_MOSI",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
                0xD5: {
                    "manufacturer": "XBEE",
                    "model": "DIO5/Assoc",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
                0xD7: {
                    "manufacturer": "XBEE",
                    "model": "SupplyVoltage",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [AnalogInput],
                    OUTPUT_CLUSTERS: [],
                },
                0xD8: {
                    "manufacturer": "XBEE",
                    "model": "DIO8",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
                0xD9: {
                    "manufacturer": "XBEE",
                    "model": "DIO9",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
                0xDA: {
                    "manufacturer": "XBEE",
                    "model": "DIO10/PWM0",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
                0xDB: {
                    "manufacturer": "XBEE",
                    "model": "DIO11/PWM1",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
                0xDC: {
                    "manufacturer": "XBEE",
                    "model": "DIO12/SPI_MISO",
                    DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    PROFILE_ID: XBEE_PROFILE_ID,
                    INPUT_CLUSTERS: [XBeeOnOff],
                    OUTPUT_CLUSTERS: [],
                },
            }
        )

        super().__init__(application, ieee, nwk, replaces)

    signature = {
        ENDPOINTS: {
            232: {
                PROFILE_ID: XBEE_PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
            230: {
                PROFILE_ID: XBEE_PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
