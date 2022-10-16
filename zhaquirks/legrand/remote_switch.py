"""Device handler for Legrand Remote switch."""
# import logging
from typing import Any, List, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks import Bus, PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legrand import LEGRAND

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513

VOLTAGE_REPORTED = "voltage_reported"


class LegrandRemoteSwitchCluster(CustomCluster, ManufacturerSpecificCluster):
    """LegrandRemoteSwitchCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandRemoteSwitchCluster"
    ep_attribute = "legrand_cluster"


class LegrandRemoteSwitchLevelControl(CustomCluster, LevelControl):
    """LegrandRemoteSwitchLevelControl."""

    def bind(self):
        """Disable binding to SwitchLevelControl cluster of the coordinator."""

        pass


class LegrandRemoteSwitchOnOff(CustomCluster, OnOff):
    """Legrand Wireless Remote Switch On/Off custom cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """handle_cluster_request."""

        if hdr.command_id in (0x0000, 0x0001, 0x0002):
            # Send default response
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

            self.endpoint.device.voltage_bus.listener_event(VOLTAGE_REPORTED)
        else:
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )


class LegrandRemoteSwitchPowerConfiguration(PowerConfigurationCluster):
    """Legrand Wireless Remote Switch On/Off custom cluster."""

    _CONSTANT_ATTRIBUTES = {
        0x0031: 10,  # battery_size = CR2032
        0x0033: 1,  # battery_quantity
        0x0034: 30,  # battery_rated_voltage = 3000 mV
    }

    def __init__(self, *args, **kwargs):
        """Init."""

        super().__init__(*args, **kwargs)
        self.endpoint.device.voltage_bus.add_listener(self)

    async def _configure_reporting(self, *args, **kwargs):  # pylint: disable=W0221
        """Prevent remote configure reporting."""

        return (foundation.ConfigureReportingResponse.deserialize(b"\x00")[0],)

    def voltage_reported(self):
        """Voltage reported."""

        self.create_catching_task(
            super().read_attributes(
                [
                    self.BATTERY_VOLTAGE_ATTR,
                ],
                manufacturer=0x1021,
            )
        )


class LegrandRemoteSwitchPollControl(CustomCluster, PollControl):
    """Legrand Wireless Remote Switch PollControl cluster.

    Read PowerConfiguration attributes during check-in.
    """

    cluster_id = 0x0020
    name = "PollControl"

    def __init__(self, *args, **kwargs):
        """Init."""

        self._current_state = {}
        super().__init__(*args, **kwargs)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """handle_cluster_request."""

        if hdr.command_id == 0x0000:
            self.endpoint.device.voltage_bus.listener_event(VOLTAGE_REPORTED)
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )


class RemoteSwitch(CustomDevice):
    """Wireless Remote switch 067773 (NLT type device)."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voltage_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=260
        # device_version=1
        # input_clusters=[0, 1, 3, 15, 32, 64513]
        # output_clusters=[0, 3, 6, 8, 25, 64513]>
        MODELS_INFO: [(f" {LEGRAND}", " Remote switch")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LegrandRemoteSwitchPowerConfiguration,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    LegrandRemoteSwitchPollControl,
                    LegrandRemoteSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    LegrandRemoteSwitchOnOff,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LegrandRemoteSwitchCluster,
                ],
            },
        },
    }
