"""Ubisys Switching Actuator S1 quirk."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.const import BUTTON, CLUSTER_ID, COMMAND, COMMAND_CLICK, ENDPOINT_ID
from zhaquirks.quirk_ids import SE_POLL_SUMMATION


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysCluster(CustomCluster):
    """Ubisys custom cluster 0xFC00."""

    cluster_id = 0xFC00
    name = "Ubisys Cluster 0xFC00"
    ep_attribute = "ubisys_cluster_0xfc00"

    # ZCL Write Attributes Structured command ID (not supported by zigpy natively)
    WRITE_ATTRIBUTES_STRUCTURED = 0x0F

    class AttributeDefs(BaseAttributeDefs):
        """Ubisys attribute definitions."""

        input_configurations: Final = ZCLAttributeDef(
            id=0x0000, type=t.LVList[t.uint8_t, t.uint16_t], manufacturer_code=None
        )
        input_actions: Final = ZCLAttributeDef(
            id=0x0001, type=t.LVList[t.LVBytes, t.uint16_t], manufacturer_code=None
        )
        cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD, type=t.uint16_t, manufacturer_code=None
        )

    async def write_input_actions(self, actions: list[bytes]) -> list:
        """Write input_actions using ZCL Write Attributes Structured.

        ubisys devices require the structured write command (0x0F) for array
        attributes. Regular write_attributes sends an invalid ZCL type.
        """
        tsn = self.endpoint.device.application.get_sequence()

        # Build raw ZCL frame
        frame = bytearray()
        # ZCL Header
        frame.append(0x00)  # Frame control: global, no manufacturer, client->server
        frame.append(tsn)
        frame.append(self.WRITE_ATTRIBUTES_STRUCTURED)

        # Payload: write whole input_actions attribute as array
        # Attribute ID (uint16 LE)
        frame.extend(
            self.AttributeDefs.input_actions.id.to_bytes(2, byteorder="little")
        )
        # Selector indicator: 0x00 (whole attribute, no indexes)
        frame.append(0x00)
        # Data Type: 0x48 (Array)
        frame.append(0x48)
        # Element Type: 0x41 (OCTET_STR)
        frame.append(0x41)
        # Element Count (uint16 LE)
        frame.extend(len(actions).to_bytes(2, byteorder="little"))
        # Each element as length-prefixed octet string
        for action in actions:
            frame.append(len(action))
            frame.extend(action)

        await self.endpoint.request(
            cluster=self.cluster_id,
            sequence=tsn,
            data=bytes(frame),
            command_id=self.WRITE_ATTRIBUTES_STRUCTURED,
        )

        # Return format expected by write_attributes_safe
        return [[foundation.WriteAttributesStatusRecord(Status.SUCCESS)]]


class InputMode(t.enum8):
    """Input mode for ubisys S1."""

    Toggle = 0x00
    Toggle_switch = 0x01
    On_off_switch = 0x02


# Input action descriptors per mode.
# Format: [input_index, transition, source_endpoint, cluster_id_lo, cluster_id_hi, command, ...]
# Transitions: 0x0D = any->pressed, 0x03 = any->released
# OnOff cluster 0x0006: 0x00=Off, 0x01=On, 0x02=Toggle
_INPUT_ACTION_TEMPLATES: dict[InputMode, list[bytes]] = {
    InputMode.Toggle: [
        bytes([0x00, 0x0D, 0x02, 0x06, 0x00, 0x02]),
    ],
    InputMode.Toggle_switch: [
        bytes([0x00, 0x0D, 0x02, 0x06, 0x00, 0x02]),
        bytes([0x00, 0x03, 0x02, 0x06, 0x00, 0x02]),
    ],
    InputMode.On_off_switch: [
        bytes([0x00, 0x0D, 0x02, 0x06, 0x00, 0x01]),
        bytes([0x00, 0x03, 0x02, 0x06, 0x00, 0x00]),
    ],
}


class UbisysInputConfigCluster(LocalDataCluster):
    """Local cluster to configure ubisys S1 input mode."""

    cluster_id = 0xFBFF
    name = "Ubisys Input Configuration"
    ep_attribute = "ubisys_input_config"

    class AttributeDefs(BaseAttributeDefs):
        """Ubisys input configuration attribute definitions."""

        input_mode: Final = ZCLAttributeDef(id=0x0000, type=InputMode)

    def __init__(self, *args, **kwargs):
        """Init with default input mode."""
        super().__init__(*args, **kwargs)
        if self.AttributeDefs.input_mode.id not in self._attr_cache:
            self._update_attribute(self.AttributeDefs.input_mode.id, InputMode.Toggle)

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer=None,
        **kwargs,
    ) -> list:
        """Write input_mode locally and send input_actions to device."""
        for attr, value in attributes.items():
            attr_name = attr if isinstance(attr, str) else self.attributes[attr].name
            if attr_name == self.AttributeDefs.input_mode.name:
                mode = InputMode(value)
                actions = _INPUT_ACTION_TEMPLATES[mode]

                # Write input_actions to the real UbisysCluster on endpoint 232
                device_setup = self.endpoint.device.endpoints[232].ubisys_cluster_0xfc00
                result = await device_setup.write_input_actions(actions)

                # Update local cache on success
                self._update_attribute(self.AttributeDefs.input_mode.id, mode)
                return result

        return await super().write_attributes(attributes, manufacturer, **kwargs)


(
    QuirkBuilder(manufacturer="ubisys", model="S1 (5501)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysInputConfigCluster)
    .enum(
        attribute_name=UbisysInputConfigCluster.AttributeDefs.input_mode.name,
        enum_class=InputMode,
        cluster_id=UbisysInputConfigCluster.cluster_id,
        translation_key="input_mode",
        fallback_name="Input mode",
    )
    .replaces(UbisysElectricalMeasurement, endpoint_id=3)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="3-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .device_automation_triggers(
        {
            # this also toggles light by default, but on up + down, so normal switch
            (COMMAND_CLICK, BUTTON): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
        }
    )
    .add_to_registry()
)
