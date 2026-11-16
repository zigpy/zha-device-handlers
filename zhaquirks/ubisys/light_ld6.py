"""Ubisys LED Controller LD6 quirk."""

import logging
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ubisys import UbisysCluster
from zhaquirks.ubisys.dimmer_d1 import UbisysD1InputConfigCluster

_LOGGER = logging.getLogger(__name__)


class LD6OutputConfiguration(t.enum8):
    """Reference output configurations from the LD6 technical reference (6.13.3.4).

    The suffix gives the number of light sources, each on its own endpoint
    (EP1, then EP5 to EP9).
    """

    Dimmable = 0x00
    Tunable_white = 0x01
    RGB = 0x02
    RGBW = 0x03
    RGBCCT = 0x04
    Extended_color_gamut = 0x05
    Dimmable_x2 = 0x06
    Tunable_white_x2 = 0x07
    RGBW_and_tunable_white = 0x08
    RGB_and_tunable_white = 0x09
    RGB_and_dimmable = 0x0A
    RGBW_and_dimmable = 0x0B
    RGBCCT_and_dimmable = 0x0C
    RGB_x2 = 0x0D
    Dimmable_x3 = 0x0E
    Tunable_white_x3 = 0x0F
    RGB_and_dimmable_x2 = 0x10
    RGB_and_tunable_white_and_dimmable = 0x11
    RGBW_and_dimmable_x2 = 0x12
    Dimmable_x4 = 0x13
    RGB_and_dimmable_x3 = 0x14
    Dimmable_x5 = 0x15
    Dimmable_x6 = 0x16


def _entries(hex_entries: str) -> list[bytes]:
    """Convert space separated hex OutputConfigurations entries to bytes."""
    return [bytes.fromhex(entry) for entry in hex_entries.split()]


# Reference configurations, one 6-byte entry per output channel:
# endpoint (high nibble) and function (low nibble), flux, CIE 1931 x and y
OUTPUT_CONFIGURATIONS: dict[LD6OutputConfiguration, list[bytes]] = {
    LD6OutputConfiguration.Dimmable: _entries(
        "10ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.Tunable_white: _entries(
        "11fe4250d952 12feb9751d69 00ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGB: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 00ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGBW: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 11fe64617260 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGBCCT: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 11fe4250d952 12feb9751d69 00ffffffffff"
    ),
    LD6OutputConfiguration.Extended_color_gamut: _entries(
        "134586b1ef4e 16c6599a8065 14fe391d82d3 17b49e0b834b 154dc61fcc0e 186c2d2c3a01"
    ),
    LD6OutputConfiguration.Dimmable_x2: _entries(
        "10ffffffffff 50ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.Tunable_white_x2: _entries(
        "11fe4250d952 12feb9751d69 51fe4250d952 52feb9751d69 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGBW_and_tunable_white: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 11fe64617260 51fe4250d952 52feb9751d69"
    ),
    LD6OutputConfiguration.RGB_and_tunable_white: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 00ffffffffff 51fe4250d952 52feb9751d69"
    ),
    LD6OutputConfiguration.RGB_and_dimmable: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 50ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGBW_and_dimmable: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 11fe64617260 50ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGBCCT_and_dimmable: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 11fe4250d952 12feb9751d69 50ffffffffff"
    ),
    LD6OutputConfiguration.RGB_x2: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 534706b1ef4e 54a0391d82d3 5542c61fcc0e"
    ),
    LD6OutputConfiguration.Dimmable_x3: _entries(
        "10ffffffffff 50ffffffffff 60ffffffffff 00ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.Tunable_white_x3: _entries(
        "11fe4250d952 12feb9751d69 51fe4250d952 52feb9751d69 61fe4250d952 62feb9751d69"
    ),
    LD6OutputConfiguration.RGB_and_dimmable_x2: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 50ffffffffff 60ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGB_and_tunable_white_and_dimmable: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 60ffffffffff 51fe4250d952 52feb9751d69"
    ),
    LD6OutputConfiguration.RGBW_and_dimmable_x2: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 11fe64617260 50ffffffffff 60ffffffffff"
    ),
    LD6OutputConfiguration.Dimmable_x4: _entries(
        "10ffffffffff 50ffffffffff 60ffffffffff 70ffffffffff 00ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.RGB_and_dimmable_x3: _entries(
        "134706b1ef4e 14a0391d82d3 1542c61fcc0e 50ffffffffff 60ffffffffff 70ffffffffff"
    ),
    LD6OutputConfiguration.Dimmable_x5: _entries(
        "10ffffffffff 50ffffffffff 60ffffffffff 70ffffffffff 80ffffffffff 00ffffffffff"
    ),
    LD6OutputConfiguration.Dimmable_x6: _entries(
        "10ffffffffff 50ffffffffff 60ffffffffff 70ffffffffff 80ffffffffff 90ffffffffff"
    ),
}


class UbisysLD6Cluster(UbisysCluster):
    """Ubisys device setup cluster with the LD6 output configurations."""

    class AttributeDefs(UbisysCluster.AttributeDefs):
        """LD6 device setup attribute definitions."""

        output_configurations: Final = ZCLAttributeDef(
            id=0x0010, type=t.LVList[t.LVBytes, t.uint16_t], manufacturer_code=None
        )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read the output configuration on (re)configuration for its select."""
        success, _ = await self.read_attributes(
            [self.AttributeDefs.output_configurations.name]
        )
        entries = success.get(self.AttributeDefs.output_configurations.name)
        if entries is not None:
            output_config = self.endpoint.device.endpoints[1].ubisys_output_config
            output_config.update_from_device([bytes(entry) for entry in entries])

    async def write_output_configurations(self, entries: list[bytes]) -> list:
        """Write output_configurations using ZCL Write Attributes Structured."""
        arr = foundation.Array(
            type=foundation.DataTypeId.octstr,
            value=t.LVList[t.LVBytes, t.uint16_t](entries),
        )
        return await self.write_attributes_structured_raw(
            [
                foundation.WriteAttributeStructured(
                    attrid=self.AttributeDefs.output_configurations.id,
                    selector=foundation.Selector(depth=0),
                    value=foundation.TypeValue(
                        type=foundation.DataTypeId.array, value=arr
                    ),
                )
            ]
        )


class UbisysLD6OutputConfigCluster(LocalDataCluster):
    """Local cluster to select one of the reference output configurations.

    There is no default value: until the configuration is read from the device,
    the select shows an unknown state. Same for configurations that do not match
    any of the reference ones.

    reconfigure_required is set after writing a configuration: the LD6 then
    changes its light endpoints, which ZHA picks up when the device is
    reconfigured. Reconfiguring reads the configuration and resets the attribute.
    """

    cluster_id = 0xFBFE
    name = "Ubisys Output Configuration"
    ep_attribute = "ubisys_output_config"

    class AttributeDefs(BaseAttributeDefs):
        """Ubisys output configuration attribute definitions."""

        output_configuration: Final = ZCLAttributeDef(
            id=0x0000, type=LD6OutputConfiguration
        )
        reconfigure_required: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)

    _DEFAULT_VALUES: dict[int, Any] = {
        AttributeDefs.reconfigure_required.id: t.Bool.false,
    }

    def update_from_device(self, entries: list[bytes]) -> None:
        """Set the selected configuration from the device's OutputConfigurations."""
        self._update_attribute(self.AttributeDefs.reconfigure_required, t.Bool.false)
        for output_config, reference in OUTPUT_CONFIGURATIONS.items():
            if entries == reference:
                self._update_attribute(
                    self.AttributeDefs.output_configuration, output_config
                )
                return
        _LOGGER.info(
            "%s: output configuration does not match any reference configuration: %s",
            self.endpoint.device.ieee,
            [entry.hex() for entry in entries],
        )

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer=None,
        **kwargs,
    ) -> list:
        """Write the selected reference configuration to the device."""
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            output_config = LD6OutputConfiguration(value)
            device_setup = self.endpoint.device.endpoints[232].ubisys_cluster
            result = await device_setup.write_output_configurations(
                OUTPUT_CONFIGURATIONS[output_config]
            )
            self._update_attribute(attr_def, output_config)
            self._update_attribute(self.AttributeDefs.reconfigure_required, t.Bool.true)
            _LOGGER.info(
                "%s: output configuration changed to %s, the device has to be"
                " reconfigured for the new light endpoints to be used",
                self.endpoint.device.ieee,
                output_config.name,
            )
            return result

        # find_attribute raises KeyError for undefined attributes, so this line
        # is unreachable in practice.
        raise KeyError(attributes)  # pragma: no cover


class LD6InputMode(t.enum8):
    """Input mode for the LD6.

    Same values as DimmerInputMode, without Dimmer_double, which pairs exactly
    two inputs and does not fit the three LD6 inputs.
    """

    Toggle = 0x00
    Toggle_switch = 0x01
    On_off_switch = 0x02
    Dimmer_single = 0x03


class UbisysLD6InputConfigCluster(UbisysD1InputConfigCluster):
    """Input configuration for the LD6 with three inputs.

    Input 1: EP2 -> EP1 (OnOff + LevelControl)
    Input 2: EP3 -> EP1 (OnOff + LevelControl)
    Input 3: EP4 -> EP1 (OnOff + LevelControl)
    Only input 1 is bound to the local light EP1 by default.
    """

    BIND_CLUSTERS: list[int] = [OnOff.cluster_id, LevelControl.cluster_id]

    class AttributeDefs(BaseAttributeDefs):
        """LD6 input configuration attributes for all three inputs."""

        input_mode_1: Final = ZCLAttributeDef(id=0x0000, type=LD6InputMode)
        detached_1: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        input_mode_2: Final = ZCLAttributeDef(id=0x0002, type=LD6InputMode)
        detached_2: Final = ZCLAttributeDef(id=0x0003, type=t.Bool)
        input_mode_3: Final = ZCLAttributeDef(id=0x0004, type=LD6InputMode)
        detached_3: Final = ZCLAttributeDef(id=0x0005, type=t.Bool)

    _DEFAULT_VALUES: dict[int, Any] = {
        AttributeDefs.input_mode_1.id: LD6InputMode.Dimmer_single,
        AttributeDefs.detached_1.id: t.Bool.false,
        AttributeDefs.input_mode_2.id: LD6InputMode.Dimmer_single,
        AttributeDefs.detached_2.id: t.Bool.true,
        AttributeDefs.input_mode_3.id: LD6InputMode.Dimmer_single,
        AttributeDefs.detached_3.id: t.Bool.true,
    }

    _INPUT_MODE_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("input_mode_1", 0, 2),  # Input 1: index 0, source EP2
        ("input_mode_2", 1, 3),  # Input 2: index 1, source EP3
        ("input_mode_3", 2, 4),  # Input 3: index 2, source EP4
    )

    _DETACHED_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("detached_1", 2, 1),  # EP2 -> EP1
        ("detached_2", 3, 1),  # EP3 -> EP1
        ("detached_3", 4, 1),  # EP4 -> EP1
    )


(
    QuirkBuilder(manufacturer="ubisys", model="LD6")
    .replaces(UbisysLD6Cluster, endpoint_id=232)
    .adds(UbisysLD6InputConfigCluster)
    .adds(UbisysLD6OutputConfigCluster)
    .enum(
        attribute_name=UbisysLD6OutputConfigCluster.AttributeDefs.output_configuration.name,
        enum_class=LD6OutputConfiguration,
        cluster_id=UbisysLD6OutputConfigCluster.cluster_id,
        translation_key="output_configuration",
        fallback_name="Output configuration",
    )
    .binary_sensor(
        attribute_name=UbisysLD6OutputConfigCluster.AttributeDefs.reconfigure_required.name,
        cluster_id=UbisysLD6OutputConfigCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="reconfigure_required",
        fallback_name="Reconfigure required",
    )
    .enum(
        attribute_name=UbisysLD6InputConfigCluster.AttributeDefs.input_mode_1.name,
        enum_class=LD6InputMode,
        cluster_id=UbisysLD6InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .switch(
        attribute_name=UbisysLD6InputConfigCluster.AttributeDefs.detached_1.name,
        cluster_id=UbisysLD6InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .enum(
        attribute_name=UbisysLD6InputConfigCluster.AttributeDefs.input_mode_2.name,
        enum_class=LD6InputMode,
        cluster_id=UbisysLD6InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .switch(
        attribute_name=UbisysLD6InputConfigCluster.AttributeDefs.detached_2.name,
        cluster_id=UbisysLD6InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .enum(
        attribute_name=UbisysLD6InputConfigCluster.AttributeDefs.input_mode_3.name,
        enum_class=LD6InputMode,
        cluster_id=UbisysLD6InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 3",
        translation_placeholders={"input_id": "3"},
    )
    .switch(
        attribute_name=UbisysLD6InputConfigCluster.AttributeDefs.detached_3.name,
        cluster_id=UbisysLD6InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 3",
        translation_placeholders={"input_id": "3"},
    )
    .device_automation_triggers(
        {
            # XXX: move_with_on_off + stop_with_on_off are also fired when holding down
            #  move_with_on_off with move_mode 0 and 1
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
        }
    )
    .add_to_registry()
)
