"""Device handler for Sonoff TRVZB"""
import logging
from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.typing import EndpointType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    Basic,
    Identify,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    StartUpOnOff,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeAccess, ZCLAttributeDef

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

LOGGER = logging.getLogger(f"zhaquirks.{__name__}")

SONOFF_CLUSTER_ID: Final = 0xFC11
SONOFF_CLUSTER_ID_FC57: Final = 0xFC57
SONOFF_ATTR_CHILD_LOCK: Final = 0x0000
SONOFF_ATTR_OPEN_WINDOW: Final = 0x6000
SONOFF_ATTR_FROST_PROTECTION_TEMP: Final = 0x6002
SONOFF_ATTR_IDLE_STEPS: Final = 0x6003
SONOFF_ATTR_CLOSING_STEPS: Final = 0x6004
SONOFF_ATTR_VALVE_OPENING_LIMIT_VOLTAGE: Final = 0x6005
SONOFF_ATTR_VALVE_CLOSING_LIMIT_VOLTAGE: Final = 0x6006
SONOFF_ATTR_VALVE_MOTOR_RUNNING_VOLTAGE: Final = 0x6007


class SonoffManufCluster(CustomCluster):
    """Sonoff manufacturer specific cluster."""

    name: str = "Sonoff Manufacturer Specific"
    cluster_id: t.uint16_t = SONOFF_CLUSTER_ID
    ep_attribute: str = "sonoff_manufacturer"

    def __init__(self, endpoint: EndpointType, is_server: bool = True) -> None:
        super().__init__(endpoint, is_server)
        self.endpoint.device.child_lock_bus.add_listener(self)
        self.endpoint.device.open_window_bus.add_listener(self)
        self.endpoint.device.frost_protection_temp_bus.add_listener(self)

    class AttributeDefs(BaseAttributeDefs):
        child_lock: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_CHILD_LOCK,
            type=t.Bool,
            mandatory=True,
            is_manufacturer_specific=False,
        )
        open_window: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_OPEN_WINDOW,
            type=t.Bool,
            mandatory=True,
            is_manufacturer_specific=False,
        )
        frost_protection_temperature: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_FROST_PROTECTION_TEMP,
            type=t.int16s,
            mandatory=True,
            is_manufacturer_specific=False,
        )
        idle_steps: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_IDLE_STEPS,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=False,
        )
        closing_steps: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_CLOSING_STEPS,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=False,
        )
        valve_opening_limit_voltage: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_VALVE_OPENING_LIMIT_VOLTAGE,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=False,
        )
        valve_closing_limit_voltage: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_VALVE_CLOSING_LIMIT_VOLTAGE,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=False,
        )
        valve_motor_running_voltage: Final = ZCLAttributeDef(
            id=SONOFF_ATTR_VALVE_MOTOR_RUNNING_VOLTAGE,
            type=t.uint16_t,
            access=ZCLAttributeAccess.Read,
            is_manufacturer_specific=False,
        )

    @property
    def _is_manuf_specific(self) -> bool:
        """Pretend this is not manufacturer specific as the device will always
        return Status.UNSUPPORTED_ATTRIBUTE if the manufacturer id is set
        """
        return False

    def _update_attribute(self, attrid, value):
        if attrid == SONOFF_ATTR_CHILD_LOCK:
            self.endpoint.device.child_lock_bus.listener_event(
                "attribute_change", value
            )
        elif attrid == SONOFF_ATTR_OPEN_WINDOW:
            self.endpoint.device.open_window_bus.listener_event(
                "attribute_change", value
            )
        elif attrid == SONOFF_ATTR_FROST_PROTECTION_TEMP:
            self.endpoint.device.frost_protection_temp_bus.listener_event(
                "attribute_change", value / 100.0
            )

        super()._update_attribute(attrid, value)

    async def write_on_off(
        self, attribute_name: str, mode: StartUpOnOff
    ) -> foundation.Status:
        if mode == StartUpOnOff.Off:
            value = False
        elif mode == StartUpOnOff.On:
            value = True
        elif mode == StartUpOnOff.Toggle:
            success, _ = await self.read_attributes(
                (attribute_name,), manufacturer=None
            )
            try:
                value = success[attribute_name]
            except KeyError:
                return foundation.Status.FAILURE
            value = not value
        elif mode == StartUpOnOff.PreviousValue:
            return foundation.Status.SUCCESS
        else:
            return foundation.Status.INVALID_VALUE

        (res,) = await self.write_attributes({attribute_name: value}, manufacturer=None)
        return res[0].status

    async def write_frost_protection_temperature(self, value) -> foundation.Status:
        value = value * 100.0
        (res,) = await self.write_attributes(
            {SONOFF_ATTR_FROST_PROTECTION_TEMP: value}, manufacturer=None
        )
        LOGGER.debug("write_frost_protection_temperature(%s): %s", value, res)
        return res[0].status


class FrostProtectionTemperature(LocalDataCluster, AnalogOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.attributes_by_name["description"].id, "Frost protection temperature"
        )
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 4)
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 35)
        self._update_attribute(self.attributes_by_name["resolution"].id, 0.5)
        # 0x0007: Zone Temperature Setpoint AO
        self._update_attribute(self.attributes_by_name["application_type"].id, 0x0007)
        self._update_attribute(self.attributes_by_name["engineering_units"].id, 62)

        self.endpoint.device.frost_protection_temp_bus.add_listener(self)

    def attribute_change(self, value):
        LOGGER.debug("frost_protection_temperature attribute change to: %s", value)
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    async def write_attributes(self, attributes, manufacturer=None):
        res = foundation.Status.SUCCESS
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            elif attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            self._update_attribute(attrid, value)

            if attrid == self.attributes_by_name["present_value"].id:
                res = (
                    await self.endpoint.device.frost_protection_temp_bus.listener_event(
                        "write_frost_protection_temperature", value
                    )[0]
                )
        return ([foundation.WriteAttributesStatusRecord(res)],)


class SonoffTRVZBOnOff(LocalDataCluster, OnOff):
    """Local OnOff cluster that is used to write manufacturer specific (bool) attributes
    via SonoffManufCluster.write_on_off()
    """

    # Overridden in subclasses with the manufacturer specific attribute to write
    on_off_attribute = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bus = getattr(self.endpoint.device, self.on_off_attribute + "_bus")
        self._bus.add_listener(self)

    def attribute_change(self, mode):
        LOGGER.debug("%s attribute change to: %s", self.on_off_attribute, mode)
        self._update_attribute(self.attributes_by_name["on_off"].id, mode)

    async def command(
        self,
        command_id,
        *args,
        manufacturer,
        expect_reply: bool = True,
        tsn,
        **kwargs,
    ):
        if command_id in (
            self.commands_by_name["on"].id,
            self.commands_by_name["off"].id,
            self.commands_by_name["toggle"].id,
        ):
            LOGGER.debug("%s write_on_off to: %s", self.on_off_attribute, command_id)
            res = await self._bus.listener_event(
                "write_on_off", self.on_off_attribute, command_id
            )[0]
            return foundation.GENERAL_COMMANDS[
                foundation.GeneralCommand.Default_Response
            ].schema(command_id=command_id, status=res)

        return super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
            **kwargs,
        )


class ChildLockCluster(SonoffTRVZBOnOff):
    on_off_attribute = "child_lock"


class OpenWindowCluster(SonoffTRVZBOnOff):
    on_off_attribute = "open_window"


class SonoffTRVZB(CustomDevice):
    """Custom device representing Sonoff TRVZB."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.child_lock_bus = Bus()
        self.open_window_bus = Bus()
        self.frost_protection_temp_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=769, device_version=1,
        #   input_clusters=[0, 1, 3, 6, 32, 513, 64599, 64529], output_clusters=[10, 25])
        MODELS_INFO: [("SONOFF", "TRVZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    SONOFF_CLUSTER_ID_FC57,
                    SonoffManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    PollControl.cluster_id,
                    Thermostat.cluster_id,
                    SONOFF_CLUSTER_ID_FC57,
                    SonoffManufCluster,
                    FrostProtectionTemperature,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    ChildLockCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    OpenWindowCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
