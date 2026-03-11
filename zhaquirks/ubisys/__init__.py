"""Ubisys device support.

Shared classes for ubisys device quirks:
- UbisysCluster: Custom cluster 0xFC00 on EP232 for device setup configuration
- InputMode: Enum for input mode selection (toggle, toggle switch, on/off switch)
- build_onoff_actions: Build OnOff input action descriptors per mode
- UbisysInputConfigCluster: Base local cluster for input mode and detached mode
"""

from typing import Any, Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, Status, ZCLAttributeDef
from zigpy.zdo.types import MultiAddress

from zhaquirks import LocalDataCluster


class UbisysCluster(CustomCluster):
    """Ubisys custom cluster 0xFC00.

    Present on endpoint 232 of all ubisys devices. Contains the input_actions
    array attribute that controls how physical inputs map to ZCL commands.
    """

    cluster_id = 0xFC00
    name = "Ubisys Cluster 0xFC00"
    ep_attribute = "ubisys_cluster"

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
        arr = foundation.Array(
            type=foundation.DataTypeId.octstr,
            value=t.LVList[t.LVBytes, t.uint16_t](actions),
        )
        return await self.write_attributes_structured_raw(
            [
                foundation.WriteAttributeStructured(
                    attrid=self.AttributeDefs.input_actions.id,
                    selector=foundation.Selector(depth=0),
                    value=foundation.TypeValue(
                        type=foundation.DataTypeId.array, value=arr
                    ),
                )
            ]
        )


class InputMode(t.enum8):
    """Input mode for ubisys devices."""

    Toggle = 0x00
    Toggle_switch = 0x01
    On_off_switch = 0x02


def build_onoff_actions(
    input_index: int, source_ep: int, mode: InputMode
) -> list[bytes]:
    """Build OnOff input action descriptors for a given input and mode.

    Format: [input_index, transition, source_endpoint, cluster_id_lo, cluster_id_hi,
             command]
    Transitions: 0x0D = any->pressed, 0x03 = any->released
    OnOff cluster 0x0006: 0x00=Off, 0x01=On, 0x02=Toggle
    """
    if mode == InputMode.Toggle:
        return [
            bytes([input_index, 0x0D, source_ep, 0x06, 0x00, 0x02]),
        ]
    if mode == InputMode.Toggle_switch:
        return [
            bytes([input_index, 0x0D, source_ep, 0x06, 0x00, 0x02]),
            bytes([input_index, 0x03, source_ep, 0x06, 0x00, 0x02]),
        ]
    if mode == InputMode.On_off_switch:
        return [
            bytes([input_index, 0x0D, source_ep, 0x06, 0x00, 0x01]),
            bytes([input_index, 0x03, source_ep, 0x06, 0x00, 0x00]),
        ]
    return []


class UbisysInputConfigCluster(LocalDataCluster):
    """Local cluster to configure ubisys input mode and decoupling.

    Subclass and override class constants to customize for different devices:
    - BIND_CLUSTERS: Cluster IDs to bind/unbind for detached mode
    - _ATTRIBUTE_DEFAULTS: {attr_id: default_value} for init cache population
    - _INPUT_MODE_CONFIG: (attr_name, input_index, source_ep) per input
    - _DETACHED_CONFIG: (attr_name, input_ep, output_ep) per input
    """

    cluster_id = 0xFBFF
    name = "Ubisys Input Configuration"
    ep_attribute = "ubisys_input_config"

    BIND_CLUSTERS: list[int] = [OnOff.cluster_id]

    class AttributeDefs(BaseAttributeDefs):
        """Ubisys input configuration attribute definitions."""

        input_mode: Final = ZCLAttributeDef(id=0x0000, type=InputMode)
        detached: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)

    _ATTRIBUTE_DEFAULTS: dict[int, Any] = {
        AttributeDefs.input_mode.id: InputMode.Toggle,
        AttributeDefs.detached.id: t.Bool.false,
    }

    # (attr_name, input_index, source_ep) per input
    _INPUT_MODE_CONFIG: tuple[tuple[str, int, int], ...] = (("input_mode", 0, 2),)

    # (attr_name, input_ep, output_ep) per input — empty tuple to disable
    _DETACHED_CONFIG: tuple[tuple[str, int, int], ...] = (("detached", 2, 1),)

    def __init__(self, *args, **kwargs):
        """Init with defaults from _ATTRIBUTE_DEFAULTS."""
        super().__init__(*args, **kwargs)
        for attr_id, default in self._ATTRIBUTE_DEFAULTS.items():
            if attr_id not in self._attr_cache:
                self._update_attribute(attr_id, default)

    def _build_all_actions(
        self, override_attr_name: str, override_mode: InputMode
    ) -> list[bytes]:
        """Build complete action list from all inputs.

        When one input's mode changes, we rebuild the full list since
        write_input_actions replaces the entire array on the device.
        """
        actions: list[bytes] = []
        for attr_name, input_index, source_ep in self._INPUT_MODE_CONFIG:
            if attr_name == override_attr_name:
                mode = override_mode
            else:
                attr_def = self.find_attribute(attr_name)
                mode = InputMode(self._attr_cache.get(attr_def.id, InputMode.Toggle))
            actions.extend(build_onoff_actions(input_index, source_ep, mode))
        return actions

    async def _set_detached(self, det_attr_name: str, detach: bool) -> None:
        """Bind or unbind an input endpoint for the given detached attribute."""
        input_ep = next(
            ep for name, ep, _ in self._DETACHED_CONFIG if name == det_attr_name
        )
        output_ep = next(
            ep for name, _, ep in self._DETACHED_CONFIG if name == det_attr_name
        )
        zdo = self.endpoint.device.zdo
        dst = MultiAddress(
            addrmode=0x03,
            ieee=self.endpoint.device.ieee,
            endpoint=output_ep,
        )
        for cluster_id in self.BIND_CLUSTERS:
            if detach:
                await zdo.Unbind_req(
                    self.endpoint.device.ieee, input_ep, cluster_id, dst
                )
            else:
                await zdo.Bind_req(self.endpoint.device.ieee, input_ep, cluster_id, dst)
        self._update_attribute(self.find_attribute(det_attr_name), t.Bool(detach))

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer=None,
        **kwargs,
    ) -> list:
        """Handle writes to input_mode and detached attributes."""
        for attr, value in attributes.items():
            attr_name = self.find_attribute(attr).name

            for mode_attr_name, _, _ in self._INPUT_MODE_CONFIG:
                if attr_name == mode_attr_name:
                    mode = InputMode(value)
                    actions = self._build_all_actions(mode_attr_name, mode)
                    device_setup = self.endpoint.device.endpoints[232].ubisys_cluster
                    result = await device_setup.write_input_actions(actions)
                    self._update_attribute(self.find_attribute(attr_name), mode)
                    return result

            for det_attr_name, _, _ in self._DETACHED_CONFIG:
                if attr_name == det_attr_name:
                    await self._set_detached(det_attr_name, bool(value))
                    return [[foundation.WriteAttributesStatusRecord(Status.SUCCESS)]]

        # All defined attributes are handled above; find_attribute raises KeyError
        # for undefined ones, so this line is unreachable in practice.
        raise KeyError(attributes)  # pragma: no cover
