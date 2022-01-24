"""Aqara Roller Shade Driver E1 device."""

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
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

PRESENT_VALUE = 0x0055
CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008
GO_TO_LIFT_PERCENTAGE = 0x0005


class XiaomiAqaraRollerE1(XiaomiCluster, ManufacturerSpecificCluster):
    """Xiaomi mfg cluster implementation specific for E1 Roller ."""

    cluster_id = 0xFCC0

    manufacturer_attributes = {
        0x0400: ("Reverse Direction", t.Bool),
        0x0402: ("Positions Stored", t.Bool),
        0x0407: ("Store Position", t.uint8_t),
        0x0408: ("Speed", t.uint8_t),
        0x0409: ("Charging", t.uint8_t),
        0x00F7: ("Aqara Attributes", t.LVBytes),
    }


class AnalogOutputRollerE1(LocalDataCluster, AnalogOutput):
    """Analog output cluster, only used to relay current_value to WindowCovering."""

    cluster_id = AnalogOutput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid is not None and attrid == PRESENT_VALUE:
            self.endpoint.device.roller_bus.listener_event(
                "current_position_lift_percentage", value
            )


class WindowCoveringRollerE1(CustomCluster, WindowCovering):
    """Window covering cluster to receive reports that are sent to the AnalogOutput cluster."""

    cluster_id = WindowCovering.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.roller_bus.add_listener(self)

    def current_position_lift_percentage(self, value):
        """Update current_position_lift_percentage and invert value."""
        value = 100 - value
        self._update_attribute(CURRENT_POSITION_LIFT_PERCENTAGE, value)

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Override default command to invert percent lift value."""
        if command_id == GO_TO_LIFT_PERCENTAGE:
            percent = args[0]
            percent = 100 - percent
            v = (percent,)
            return await super().command(command_id, *v)
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn
        )


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
        self.roller_bus = Bus()
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
                    MultistateOutput.cluster_id,
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
