"""Aqara Roller Shade Driver E1 device."""

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, BasicCluster, XiaomiCluster, XiaomiCustomDevice
from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogOutput,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    MultistateOutput,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

PRESENT_VALUE = 0x0055
CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008
GO_TO_LIFT_PERCENTAGE = 0x0005
DOWN_CLOSE = 0x0001
UP_OPEN = 0x0000
STOP = 0x0002


class XiaomiAqaraRollerE1(XiaomiCluster, ManufacturerSpecificCluster):
    """Xiaomi mfg cluster implementation specific for E1 Roller."""

    cluster_id = 0xFCC0

    manufacturer_attributes = {
        0x0400: ("Reverse Direction", t.Bool),
        0x0402: ("Positions Stored", t.Bool),
        0x0407: ("Store Position", t.uint8_t),
        0x0408: ("Speed", t.uint8_t),
        0x0409: ("Charging", t.uint8_t),
        0x00F7: ("Aqara Attributes", t.LVBytes),
    }


class AnalogOutputRollerE1(AnalogOutput):
    """Analog output cluster, only used to relay current_value to WindowCovering."""

    cluster_id = AnalogOutput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

        self._update_attribute(0x0041, float(0x064))  # max_present_value
        self._update_attribute(0x0045, 0.0)  # min_present_value
        self._update_attribute(0x0051, 0)  # out_of_service
        self._update_attribute(0x006A, 1.0)  # resolution
        self._update_attribute(0x006F, 0x00)  # status_flags

    def _update_attribute(self, attrid, value):

        super()._update_attribute(attrid, value)

        if attrid == PRESENT_VALUE:
            self.endpoint.window_covering._update_attribute(
                CURRENT_POSITION_LIFT_PERCENTAGE, (100 - value)
            )


class WindowCoveringRollerE1(WindowCovering):
    """Window covering cluster to receive commands that are sent to the AnalogOutput's present_value to move the motor."""

    cluster_id = WindowCovering.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Overwrite the commands to make it work for both firmware 1425 and 1427. We either overwrite analog_output's current_value or multistate_output's current value to make the roller work."""
        if command_id == UP_OPEN:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 1}
            )
            return res[0].status
        elif command_id == DOWN_CLOSE:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 0}
            )
            return res[0].status
        elif command_id == GO_TO_LIFT_PERCENTAGE:
            (res,) = await self.endpoint.analog_output.write_attributes(
                {"present_value": (100 - args[0])}
            )
            return res[0].status
        elif command_id == STOP:
            (res,) = await self.endpoint.multistate_output.write_attributes(
                {"present_value": 2}
            )
            return res[0].status


class MultistateOutputRollerE1(MultistateOutput):
    """Multistate Output cluster which overwrites present_value because else it gives errors of wrong datatype when using it in the commands."""

    cluster_id = MultistateOutput.cluster_id

    manufacturer_attributes = {
        0x0055: ("present_value", t.uint16_t),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)


class PowerConfigurationRollerE1(PowerConfiguration, LocalDataCluster):
    """Xiaomi power configuration cluster implementation."""

    cluster_id = PowerConfiguration.cluster_id

    BATTERY_PERCENTAGE_REMAINING = 0x0021

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.power_bus_percentage.add_listener(self)

    def update_battery_percentage(self, value):
        """We'll receive a raw percentage value here, no need to calculate any voltages or such. Only thing we do is times 2 the value because Zigbee expects percentage 200%."""
        super()._update_attribute(
            self.BATTERY_PERCENTAGE_REMAINING,
            (value * 2),
        )


class RollerE1AQ(XiaomiCustomDevice):
    """Aqara Roller Shade Driver E1 device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.power_bus_percentage = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.curtain.acn002")],
        ENDPOINTS: {
            # <SizePrefixedSimpleDescriptor endpoint=1 profile=260 device_type=256
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 64704, 13, 19, 258]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutput.cluster_id,
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraRollerE1.cluster_id,
                    MultistateOutput.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            # <SizePrefixedSimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0,
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Alarms.cluster_id,
                    AnalogOutputRollerE1,
                    BasicCluster,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraRollerE1,
                    MultistateOutputRollerE1,
                    Scenes.cluster_id,
                    WindowCoveringRollerE1,
                    PowerConfigurationRollerE1,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
