"""Module for Legrand Contactor, Drivia with Netatmo 20AX - 230V~ - 50Hz.

PN: 412171 - 412191 - 199122

Documentation (en): https://assets.legrand.com/pim/NP-FT-GT/F03037EN-05%20(Connected%20contactor).pdf
Documentation (fr): https://assets.legrand.com/pim/NP-FT-GT/F03037FR-05%20(Contacteur%20Connect%C3%A9).pdf

Tested with PN: 199122
FW version: 0x005a45ff

signature:
{
  "node_descriptor": {
    "logical_type": 1,
    "complex_descriptor_available": 0,
    "user_descriptor_available": 1,
    "reserved": 0,
    "aps_flags": 0,
    "frequency_band": 8,
    "mac_capability_flags": 142,
    "manufacturer_code": 4129,
    "maximum_buffer_size": 89,
    "maximum_incoming_transfer_size": 63,
    "server_mask": 11264,
    "maximum_outgoing_transfer_size": 63,
    "descriptor_capability_field": 0
  },
  "endpoints": {
    "1": {
      "profile_id": "0x0104",
      "device_type": "0x010a",
      "input_clusters": [
        "0x0000",
        "0x0003",
        "0x0004",
        "0x0005",
        "0x0006",
        "0x000f",
        "0x0b04",
        "0xfc01",
        "0xfc41"
      ],
      "output_clusters": [
        "0x0000",
        "0x0005",
        "0x0006",
        "0x0019",
        "0xfc01"
      ]
    },
    "242": {
      "profile_id": "0xa1e0",
      "device_type": "0x0066",
      "input_clusters": [
        "0x0021"
      ],
      "output_clusters": [
        "0x0021"
      ]
    }
  },
  "manufacturer": " Legrand",
  "model": " Contactor",
  "class": "contactor.LegrandContactor"
}
"""

from enum import Enum
import logging

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    CustomDeviceV2,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    Status,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks import Bus
from zhaquirks.legrand import (  # decimal = 64513
    LEGRAND,
    MANUFACTURER_SPECIFIC_CLUSTER_ID,
)

_LOGGER = logging.getLogger(__name__)

MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC41  # decimal = 64577


class DeviceMode(t.enum16):
    """Device mode."""

    MODE_SWITCH = 30
    MODE_AUTO = 40


class LegrandMode(Enum):
    """Device readable mode."""

    Switch = [3, 0]
    Auto = [4, 0]


class LegrandContactorMode(CustomCluster):
    """Legrand Mode cluster.

    ZHA Toolkit scan result:
          cluster_id: "0xfc01"            # decimal = 64513
          title: LegrandContactorMode
          name: legrand_contactor_mode
          attributes:
            "0x0000":
              attribute_id: "0x0000"
              attribute_name: mode
              value_type:
                - "0x09"
                - data16
                - Discrete
              access: READ|WRITE
              access_acl: 3
              manf_id: 4129
              attribute_value:
                - 4
                - 0
            "0x0001":
              attribute_id: "0x0001"
              attribute_name: led_dark
              value_type:
                - "0x10"
                - Bool
                - Discrete
              access: READ|WRITE
              access_acl: 3
              manf_id: 4129
              attribute_value: 0
            "0x0002":
              attribute_id: "0x0002"
              attribute_name: led_on
              value_type:
                - "0x10"
                - Bool
                - Discrete
              access: READ|WRITE
              access_acl: 3
              manf_id: 4129
              attribute_value: 0
          commands_received:
            "0x03":                        # NOTE: no action identified. One mandatory parameter: arg[0]=2
              command_id: "0x03"
              command_name: "3"
              command_arguments: not_in_zcl
            "0x0e":                        # NOTE: no action identified. Accept any parameter.
              command_id: "0x0e"
              command_name: "14"
              command_arguments: not_in_zcl
            "0x11":                        # NOTE: no action identified. Accept any parameter.
              command_id: "0x11"
              command_name: "17"
              command_arguments: not_in_zcl
            "0x14":                        # NOTE: acts as a pairing reset. No parameter needed.
              command_id: "0x14"
              command_name: "20"
              command_arguments: not_in_zcl
          commands_generated:
            "0x04":
              command_id: "0x04"
              command_name: "4"
              command_args: not_in_zcl
            "0x0c":
              command_id: "0x0c"
              command_name: "12"
              command_args: not_in_zcl
            "0x10":
              command_id: "0x10"
              command_name: "16"
              command_args: not_in_zcl
    """

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandContactorMode"
    ep_attribute = "legrand_contactor_mode"

    CONTACTOR_IS_SWITCH_REPORTED = "contactor_is_switch_reported"
    MODE_ID = 0x0000
    MODES = [DeviceMode.MODE_SWITCH, DeviceMode.MODE_AUTO]

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        mode = ZCLAttributeDef(
            id=0x0000,
            type=t.data16,  # DeviceMode
            is_manufacturer_specific=True,
        )
        led_dark = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,  # LedDarkSwitch
            is_manufacturer_specific=True,
        )
        led_on = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,  # LedOnSwitch
            is_manufacturer_specific=True,
        )

    async def write_attributes(self, attributes, manufacturer=None):
        """Write attributes."""

        new_attributes = attributes.copy()
        for k in new_attributes:
            if k in [0, "mode"]:
                v = new_attributes[k]
                if isinstance(v, LegrandMode):
                    if v == LegrandMode.Switch:
                        new_v = [3, 0]
                    elif v == LegrandMode.Auto:
                        new_v = [4, 0]
                    new_attributes[k] = new_v
        return await super().write_attributes(new_attributes, manufacturer)

    def _update_attribute(self, attrid, value):
        """Attribute update."""

        _LOGGER.debug(
            "LegrandContactorMode._update_attribute: attrid=%s, value=%s",
            str(attrid),
            str(value),
        )

        super()._update_attribute(attrid, value)
        if attrid == self.MODE_ID and value is not None:
            mode = (int(value[0]) * 10) + int(value[1])
            if mode in self.MODES:
                self.endpoint.device.reporting_bus.listener_event(
                    self.CONTACTOR_IS_SWITCH_REPORTED, mode == DeviceMode.MODE_SWITCH
                )

    async def _read_mode(self):
        """Read  mode."""
        result = await self.read_attributes([self.MODE_ID], allow_cache=False)
        if not result[0]:
            return None

        return result[0][self.MODE_ID]


class AutoStatus(t.enum8):
    """Auto mode status values.

    NOTE: Oddly enough this status does not seem to reflect all the states.

    One may had expected the following states:
    Zigby Forced Off
    Manually Forced Off
    Auto Off
    Auto On
    Manually Forced On
    Zigby Forced On

    or:
    Forced Off
    Auto Off
    Auto On
    Forced On
    """

    ForcedOff = 0x00
    ForcedOn = 0x01
    Auto = 0x02
    ManualOn = 0x03


class AutoOverride(t.enum8):
    """Auto override arguments values."""

    ForceOff = 0x00
    ForceOn = 0x01
    Automatic = 0x02  # no override


class LegrandContactorAutoStatus(Enum):
    """Auto mode status values for UI display."""

    ForcedOff = 0x00
    ForcedOn = 0x01
    Auto = 0x02
    ManualOn = 0x03


class LegrandContactorSwitchStatus(Enum):
    """Switch status values for UI display."""

    Off = 0x00
    On = 0x01


class LegrandContactorAutoOnOff(CustomCluster):
    """Legrand Auto OnOff cluster.

    ZHA Toolkit scan result:
          cluster_id: "0xfc41"        # decimal = 64577
          title: LegrandContactorAutoOnOff
          name: legrand_contactor_auto_on_off
          attributes:
            "0x0000":
              attribute_id: "0x0000"
              attribute_name: status
              value_type:
                - "0x30"
                - enum8
                - Discrete
              access: READ|REPORT
              access_acl: 5
              manf_id: 4129
              attribute_value: 3
            "0x0001":
              attribute_id: "0x0001"
              attribute_name: on_off
              value_type:
                - "0x10"
                - Bool
                - Discrete
              access: READ|REPORT
              access_acl: 5
              manf_id: 4129
              attribute_value: 1
            "0xfffd":
              attribute_id: "0xfffd"
              attribute_name: "65533"
              value_type:
                - "0x21"
                - uint16_t
                - Analog
              access: READ
              access_acl: 1
              manf_id: 4129
              attribute_value: 1
          commands_received:
            "0x00":
              command_id: "0x00"
              command_name: override
              command_arguments: <class 'zigpy.zcl.foundation.override'>
          commands_generated:
            "0x0a":
              command_id: "0x0a"
              command_name: "10"
    """

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID_2
    name = "LegrandContactorAutoOnOff"
    ep_attribute = "legrand_contactor_auto_on_off"

    AUTO_ON_OFF_REPORTED = "auto_on_off_reported"
    STATUS_ID = 0
    ON_OFF_ID = 1
    OVERRIDE_CMD_ID = 0x00
    TOGGLE_MAP = {
        AutoStatus.ForcedOn: AutoOverride.ForceOff,
        AutoStatus.ForcedOff: AutoOverride.ForceOn,
    }

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        status = ZCLAttributeDef(
            id=0x0000,
            type=AutoStatus,  # t.enum8
            is_manufacturer_specific=True,
        )
        on_off = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,  # on_off in AUTO mode
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server Command Definitions."""

        override = ZCLCommandDef(
            id=0x00,
            schema={
                "mode": AutoOverride,
            },
            is_manufacturer_specific=True,
        )

    async def turn_off(self, manufacturer=None, expect_reply=False, tsn=None):
        """Force Off."""
        _LOGGER.debug("LegrandContactorAutoOnOff.turn_off")

        status = await self._read_status()

        if status == AutoStatus.ForcedOff:
            _LOGGER.debug("LegrandContactorAutoOnOff.toggle is in forcedOff state.")
            return (None, Status.SUCCESS)

        return await self.command(
            self.OVERRIDE_CMD_ID,
            AutoOverride.ForceOff,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def turn_on(self, manufacturer=None, expect_reply=False, tsn=None):
        """Force On."""
        _LOGGER.debug("LegrandContactorAutoOnOff.turn_on")

        status = await self._read_status()

        if status == AutoStatus.ForcedOn:
            _LOGGER.debug("LegrandContactorAutoOnOff.toggle is in forcedOn state.")
            return (None, Status.SUCCESS)

        return await self.command(
            self.OVERRIDE_CMD_ID,
            AutoOverride.ForceOn,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def toggle(self, manufacturer=None, expect_reply=False, tsn=None):
        """Toggle ForcedOff/ForcedOn."""
        _LOGGER.debug("LegrandContactorAutoOnOff.toggle")

        status = await self._read_status()

        if status not in self.TOGGLE_MAP:
            _LOGGER.debug("LegrandContactorAutoOnOff.toggle is not in forced state.")
            return (None, Status.SUCCESS)

        auto_override = self.TOGGLE_MAP[status]

        return await self.command(
            self.OVERRIDE_CMD_ID,
            auto_override,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    async def _read_status(self):
        """Read status."""
        result = await self.read_attributes([self.STATUS_ID], allow_cache=False)
        if not result[0]:
            return None

        return result[0][self.STATUS_ID]

    async def _read_states(self):
        """Read states."""
        await self.read_attributes([self.STATUS_ID, self.ON_OFF_ID], allow_cache=False)

    def _update_attribute(self, attrid, value):
        """Attribute update."""

        _LOGGER.debug(
            "LegrandContactorAutoOnOff._update_attribute: attrid=%s, value=%s",
            str(attrid),
            str(value),
        )

        super()._update_attribute(attrid, value)

        if attrid == self.ON_OFF_ID and value is not None:
            self.endpoint.device.reporting_bus.listener_event(
                self.AUTO_ON_OFF_REPORTED, value
            )

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Command."""

        _LOGGER.debug("LegrandContactorAutoOnOff.command: id=%s", str(command_id))

        result = await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

        await self._read_states()

        return result


class LegrandContactorSwitchOnOff(CustomCluster, OnOff):
    """Legrand Switch OnOff cluster.

    When the device is in Switch mode, it operates normally the OnOff cluster.

    However, when the device is in Auto mode, on, off and toggle OnOff custer's
    commands are not supported.

    This class redirects them to the AutoOnOff cluster (id: 0xfc41).

    Similarly, it redirects on_off attribute reads.

    NOTE: The name and ep_attribute class attributes are NOT changed to benefit
    of generic OnOff cluster's entities creation:
    - switch
    - startup behavior select
    """

    cluster_id = OnOff.cluster_id

    ON_OFF_ID = 0x0000
    OFF_CMD_ID = 0x00
    ON_CMD_ID = 0x01
    TOGGLE_CMD_ID = 0x02

    def __init__(self, *args, **kwargs):
        """Init."""

        super().__init__(*args, **kwargs)
        self.endpoint.device.reporting_bus.add_listener(self)
        self._contactor_is_switch = None

    def contactor_is_switch_reported(self, value):
        """Contactor is switch reported."""

        _LOGGER.debug(
            "LegrandContactorSwitchOnOff.contactor_is_switch_reported: value=%s",
            str(value),
        )

        self._contactor_is_switch = value

    def auto_on_off_reported(self, value):
        """Auto mode on_off status reported."""

        _LOGGER.debug(
            "LegrandContactorSwitchOnOff.on_off_reported: value=%s", str(value)
        )

        if self._contactor_is_switch:
            _LOGGER.debug(
                "LegrandContactorSwitchOnOff.on_off_reported: update switch ignored in switch mode."
            )
            return

        super()._update_attribute(self.ON_OFF_ID, value)

        _LOGGER.debug("LegrandContactorSwitchOnOff.on_off_reported done.")

    async def _read_attributes(self, attr_ids, *args, **kwargs):
        """Read attributes.

        Redirects on_off attribute reads to the AutoOnOff cluster (id: 0xfc41) when the device is in Auto mode.
        """
        _LOGGER.debug("LegrandContactorSwitchOnOff._read_attributes")

        attr_ids = [
            self.ON_OFF_ID if attr_id == "on_off" else attr_id for attr_id in attr_ids
        ]

        if self.ON_OFF_ID not in attr_ids:
            _LOGGER.debug(
                "LegrandContactorSwitchOnOff.read_attributes not reading on_off attribute."
            )

            return await super()._read_attributes(attr_ids, *args, **kwargs)

        await self._update_contactor_mode()

        if not self._contactor_is_switch:
            await self._update_auto_states()

        return await super()._read_attributes(attr_ids, *args, **kwargs)

    async def _update_contactor_mode(self):
        """Update contactor mode for _contactor_is_switch."""

        _LOGGER.debug("LegrandContactorSwitchOnOff._update_contactor_mode.")

        mode_cluster = self.endpoint.device.endpoints[1].in_clusters[
            LegrandContactorMode.cluster_id
        ]

        await mode_cluster._read_mode()

    async def _update_auto_states(self):
        """Update contactor auto mode status."""

        _LOGGER.debug("LegrandContactorSwitchOnOff._update_auto_states.")

        auto_cluster = self.endpoint.device.endpoints[1].in_clusters[
            LegrandContactorAutoOnOff.cluster_id
        ]

        await auto_cluster._read_states()

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Legrand switch OnOff command.

        Redirects on, off and toggle commands to AutoOnOff cluster (id: 0xfc41) when the device is Auto mode.
        The on and off commands FORCE the corresponding states.
        The toggle command is only operationnal if the AutoOnOff cluster is in a FORCED state.
        It toggles the ForcedOff (resp. ForcedOn) state to the FocedOn (resp. ForcedOff) state.

        When the device is in Switch mode, operates as a normal OnOff cluster.

        FIXME: UI representation of the Automatic operation should exist.
        => workaround with quirks-v2: 'Auto Status' diagnostic enum

        FIXME: something should execute the LegrandContactorAutoOnOff.override(AutoOverride.Automatic)
        to restore automatic operation after switch UI use.
        => done with quirks-v2: 'Reset Auto' control button

        FIXME: something should disable 'Reset Auto' and 'Auto Status' when Switch mode is active.
        """
        _LOGGER.debug("LegrandContactorSwitchOnOff.command")

        if command_id not in [self.ON_CMD_ID, self.OFF_CMD_ID, self.TOGGLE_CMD_ID]:
            _LOGGER.debug(
                "LegrandContactorSwitchOnOff.command is neither on, off nor toggle."
            )
            return await super().command(
                command_id,
                *args,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )

        await self._update_contactor_mode()

        if self._contactor_is_switch:
            _LOGGER.debug("LegrandContactorSwitchOnOff.command in switch mode.")
            return await super().command(
                command_id,
                *args,
                manufacturer=manufacturer,
                expect_reply=expect_reply,
                tsn=tsn,
            )

        auto_cluster = self.endpoint.device.endpoints[1].in_clusters[
            LegrandContactorAutoOnOff.cluster_id
        ]

        if command_id == self.ON_CMD_ID:
            return await auto_cluster.turn_on(
                manufacturer=manufacturer, expect_reply=expect_reply, tsn=tsn
            )

        if command_id == self.OFF_CMD_ID:
            return await auto_cluster.turn_off(
                manufacturer=manufacturer, expect_reply=expect_reply, tsn=tsn
            )

        if command_id == self.TOGGLE_CMD_ID:
            return await auto_cluster.toggle(
                manufacturer=manufacturer, expect_reply=expect_reply, tsn=tsn
            )

        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn,
        )

    def _update_attribute(self, attrid, value):
        """Legrand switch OnOff attribute update.

        Ignores on_off  attribute update when the device is Auto mode.
        """

        _LOGGER.debug(
            "LegrandContactorSwitchOnOff._update_attribute: attrid=%s, value=%s",
            str(attrid),
            str(value),
        )

        # await self._update_contactor_mode()

        if not self._contactor_is_switch:
            _LOGGER.debug(
                "LegrandContactorSwitchOnOff._update_attribute ignored in auto mode."
            )
            return

        super()._update_attribute(attrid, value)


class LegrandContactorV2(CustomDeviceV2):
    """Legrand Contactor device.

    The device offers two modes of operation:
    - the, factory default, Auto mode where an external input can control the output.
    - and a Switch mode where normal operations of a controlled switch are supported.

    When the device is in Auto mode, its operation button selects three modes of operation:
    - a ForcedOff mode where the switch output is opened,
    - an Automatic mode where the switch output is controlled by the external input,
    - and a ForcedOn mode where the switch output is closed.

    When the device is in Switch mode, its operation button toggles the OnOff modes of operation:
    - the Off mode where the switch output is opened,
    - and the On mode where the switch output is closed.

    Two leds reflect the states of the device.

    The LED on the operation button reflects the device's state. It is:
    - OFF when the device is (forced) OFF
    - slow dark blinking with OFF/BLUE colors when the device is OFF, in Auto mode with external input not active,
    - slow bright blinking with BLUE/GREEN colors when the device is ON, in Auto mode with external input active,
    - and ON with e bright GREEN color when the device is (forced) ON.

    The LED on the reset button reflects the association states of the device. It is:
    - RED when the device is not paired,
    - GREEN when it is in paired , while the network is still open (controller still searching devices)
    - OFF when the device is paired.
    - PURPLE when the device pairing failed (is it on timed out? not documented...)

    The reset button controls the pairing.

    1- A long press (approx. 10s) on the reset button resets the device's pairing and is reflected by a RED led.

    2- When the device pairing is reset, another long press on the reset button followed by some (a few)
    short presses (approx 1 every 1s) starts, and maintains, the pairing process.

    3- Success of the pairing is reflected by a GREEN led.
    If the pairing fails, retry at step 1.

    4- the led turns OFF when the controller stops the pairing process.

    It instantiates, in replacement, three custom clusters classes:
    - The LegrandContactorMode cluster (id: 0xfc01) controls the operation mode of the device.
    - The LegrandContactorAutoOnOff cluster (id: 0xfc41) controls the device in Auto mode.
    - The LegrandContactorSwitchOnOff cluster (id: OnOff cluster id) controls the device in Switch mode and
    acts as a proxy to LegrandContactorAutoOnOff in Auto mode.
    """

    def __init__(self, application, ieee, nwk, replaces, quirk_metadata):
        """Init."""

        self.reporting_bus = Bus()
        super().__init__(application, ieee, nwk, replaces, quirk_metadata)


REPORTING_WHEN_CHANGED = ReportingConfig(
    min_interval=0, max_interval=0, reportable_change=1
)

(
    QuirkBuilder(f" {LEGRAND}", " Contactor")
    .device_class(LegrandContactorV2)
    .replaces(LegrandContactorMode)
    .replaces(LegrandContactorAutoOnOff)
    .replaces(LegrandContactorSwitchOnOff)
    .enum(
        attribute_name="mode",
        enum_class=LegrandMode,
        cluster_id=LegrandContactorMode.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        initially_disabled=False,
        attribute_initialized_from_cache=True,
        reporting_config=REPORTING_WHEN_CHANGED,
        translation_key="operating_mode",
        fallback_name="Mode",
    )
    .command_button(
        command_name="override",
        cluster_id=LegrandContactorAutoOnOff.cluster_id,
        command_args=(AutoOverride.Automatic,),
        command_kwargs=None,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        entity_type=EntityType.STANDARD,
        initially_disabled=False,
        translation_key="reset_auto",
        fallback_name="Reset Auto",
    )
    .enum(
        attribute_name="status",
        enum_class=LegrandContactorAutoStatus,
        cluster_id=LegrandContactorAutoOnOff.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=False,
        attribute_initialized_from_cache=True,
        reporting_config=REPORTING_WHEN_CHANGED,
        translation_key="auto_status",
        fallback_name="Auto Status",
    )
    # .switch("led_dark", LegrandContactorMode.cluster_id,
    #        ClusterType.Server, 1, False, None, 0, 1, EntityPlatform.SWITCH, False, True, 'led_dark')
    # .switch("led_on", LegrandContactorMode.cluster_id,
    #        ClusterType.Server, 1, False, None, 0, 1, EntityPlatform.SWITCH, False, True, 'led_on')
    .add_to_registry()
)
