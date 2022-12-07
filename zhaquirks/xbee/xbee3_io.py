"""Class to control Xbee3 device."""

from zigpy.profiles import zha

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xbee import (
    XBEE_PROFILE_ID,
    XBeeAnalogInput,
    XBeeCommon,
    XBeeOnOff,
    XBeePWM,
)


class XBee3Sensor(XBeeCommon):
    """XBee3 Sensor."""

    replacement = XBeeCommon.replacement.copy()
    replacement["model"] = "XBee3"
    replacement[ENDPOINTS] = XBeeCommon.replacement[ENDPOINTS].copy()
    replacement[ENDPOINTS].update(
        {
            0xD0: {
                # AD0/DIO0/Commissioning
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeeAnalogInput],
                OUTPUT_CLUSTERS: [],
            },
            0xD1: {
                # AD1/DIO1/SPI_nATTN
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeeAnalogInput],
                OUTPUT_CLUSTERS: [],
            },
            0xD2: {
                # AD2/DIO2/SPI_CLK
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeeAnalogInput],
                OUTPUT_CLUSTERS: [],
            },
            0xD3: {
                # AD3/DIO3
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeeAnalogInput],
                OUTPUT_CLUSTERS: [],
            },
            0xD4: {
                # DIO4/SPI_MOSI
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xD5: {
                # DIO5/Assoc
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xD6: {
                # DIO6/RTS
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xD7: {
                # DIO7/CTS
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeeAnalogInput],
                OUTPUT_CLUSTERS: [],
            },
            0xD8: {
                # DIO8
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xD9: {
                # DIO9
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xDA: {
                # DIO10/PWM0
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeePWM],
                OUTPUT_CLUSTERS: [],
            },
            0xDB: {
                # DIO11/PWM1
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff, XBeePWM],
                OUTPUT_CLUSTERS: [],
            },
            0xDC: {
                # DIO12/SPI_MISO
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xDD: {
                # DIO13/DOUT
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
            0xDE: {
                # DIO14/DIN
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                PROFILE_ID: XBEE_PROFILE_ID,
                INPUT_CLUSTERS: [XBeeOnOff],
                OUTPUT_CLUSTERS: [],
            },
        }
    )

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
