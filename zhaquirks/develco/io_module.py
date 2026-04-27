"""Develco IO Module."""

import asyncio
from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import BinaryInput, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zdo import types as zdo_t


class LinkedOutput(t.enum8):
    """Configured output endpoint for an input."""

    none = 0x00
    output_1 = 0x01
    output_2 = 0x02


class FrientBinaryInput(CustomCluster, BinaryInput):
    """Binary input with configurable device-side output linking."""

    INPUT_ENDPOINT_IDS: set[int] = {112, 113, 114, 115}
    OUTPUT_ENDPOINT_IDS: set[int] = {116, 117}
    OUTPUT_ENDPOINT_BY_LINK: dict[LinkedOutput, int] = {
        LinkedOutput.output_1: 116,
        LinkedOutput.output_2: 117,
    }

    def _local_attr_defaults_for_endpoint(self, endpoint_id: int) -> dict[int, Any]:
        """Return endpoint-specific local attributes managed by the quirk."""
        local_defaults: dict[int, Any] = {}
        if endpoint_id in self.INPUT_ENDPOINT_IDS:
            local_defaults[self.AttributeDefs.linked_output.id] = LinkedOutput.none
        if endpoint_id in self.OUTPUT_ENDPOINT_IDS:
            local_defaults[self.AttributeDefs.on_with_timed_off_on_time.id] = 0
            local_defaults[self.AttributeDefs.on_with_timed_off_off_wait_time.id] = 0
        return local_defaults

    class AttributeDefs(BinaryInput.AttributeDefs):
        """Attribute definitions."""

        linked_output = ZCLAttributeDef(
            id=0xFFF0,
            type=LinkedOutput,
            access="rw",
        )
        on_with_timed_off_on_time = ZCLAttributeDef(
            id=0x8000,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        on_with_timed_off_off_wait_time = ZCLAttributeDef(
            id=0x8001,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )
        # Device uses Binary Input polarity (0x0054, enum8) where 0=normal, 1=reversed.
        polarity = ZCLAttributeDef(
            id=BinaryInput.AttributeDefs.polarity.id,
            type=t.enum8,
            access="rw",
        )

    def _resolve_attr_id(
        self, attr: str | int | foundation.ZCLAttributeDef
    ) -> int | None:
        """Resolve supported attribute key variants to integer attribute id."""
        if isinstance(attr, str):
            attr_def = self.attributes_by_name.get(attr)
            return attr_def.id if attr_def is not None else None
        if isinstance(attr, foundation.ZCLAttributeDef):
            return attr.id
        if isinstance(attr, int):
            return attr
        return None

    async def read_attributes_raw(
        self,
        attributes: list[str | int | foundation.ZCLAttributeDef],
        manufacturer: int | None = None,
        **kwargs,
    ) -> tuple[list[foundation.ReadAttributeRecord], ...]:
        """Handle local config reads while delegating remote reads."""
        local_attr_defaults = self._local_attr_defaults_for_endpoint(
            self.endpoint.endpoint_id
        )
        local_records: list[foundation.ReadAttributeRecord] = []
        remote_attrs: list[str | int | foundation.ZCLAttributeDef] = []

        for attr in attributes:
            attr_id = self._resolve_attr_id(attr)
            attr_def = self.attributes.get(attr_id) if attr_id is not None else None
            if attr_id in local_attr_defaults and attr_def is not None:
                value = self.get(attr_id, local_attr_defaults[attr_id])
                local_records.append(
                    foundation.ReadAttributeRecord(
                        attrid=attr_id,
                        status=foundation.Status.SUCCESS,
                        value=foundation.TypeValue(value=attr_def.type(value)),
                    )
                )
            else:
                remote_attrs.append(attr)

        if not remote_attrs:
            return (local_records,)

        remote_result = await super().read_attributes_raw(
            remote_attrs,
            manufacturer=manufacturer,
            **kwargs,
        )
        remote_records = list(remote_result[0])
        return (remote_records + local_records, *remote_result[1:])

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Handle local config writes while delegating remote writes."""
        local_attr_ids = set(
            self._local_attr_defaults_for_endpoint(self.endpoint.endpoint_id).keys()
        )
        remote_attrs: dict[str | int | foundation.ZCLAttributeDef, Any] = {}
        local_write = False

        for attr, value in attributes.items():
            attr_id = self._resolve_attr_id(attr)
            if attr_id is None:
                raise KeyError(f"Unknown attribute: {attr!r}")

            attr_def = self.attributes.get(attr_id)
            if attr_id in local_attr_ids and attr_def is not None:
                self._update_attribute(attr_id, attr_def.type(value))
                local_write = True
            else:
                remote_attrs[attr] = value

        if remote_attrs:
            return await super().write_attributes(
                remote_attrs,
                manufacturer=manufacturer,
                **kwargs,
            )

        if local_write:
            return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Handle input updates, including link binding sync."""
        previous_value = self.get(attrid)
        super()._update_attribute(attrid, value)
        endpoint_id = self.endpoint.endpoint_id

        if (
            endpoint_id in self.INPUT_ENDPOINT_IDS
            and attrid == self.AttributeDefs.linked_output.id
        ):
            previous_link = self._normalize_linked_output(previous_value)
            new_link = self._normalize_linked_output(
                self.get(self.AttributeDefs.linked_output.id, LinkedOutput.none)
            )
            if previous_link != new_link:
                self.create_catching_task(
                    self._sync_link_binding(previous_link, new_link)
                )
            return

        if (
            endpoint_id in self.INPUT_ENDPOINT_IDS
            and attrid == self.AttributeDefs.present_value.id
        ):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # Some sync tests call _update_attribute without a running event loop.
                return
            self.create_catching_task(self._dispatch_output_command(bool(value)))

    async def _dispatch_output_command(self, is_active: bool) -> None:
        """Dispatch output command based on linked output and timed-off settings."""
        linked_output = self._normalize_linked_output(
            self.get(self.AttributeDefs.linked_output.id, LinkedOutput.none)
        )
        output_endpoint_id = self.OUTPUT_ENDPOINT_BY_LINK.get(linked_output)
        if output_endpoint_id is None:
            return

        output_endpoint = self.endpoint.device.endpoints.get(output_endpoint_id)
        if output_endpoint is None:
            return

        output_cluster = output_endpoint.in_clusters.get(OnOff.cluster_id)
        if output_cluster is None:
            return

        output_settings_cluster = output_endpoint.in_clusters.get(
            BinaryInput.cluster_id
        )
        on_time = 0
        off_wait_time = 0
        if output_settings_cluster is not None:
            on_time = int(
                output_settings_cluster.get(
                    self.AttributeDefs.on_with_timed_off_on_time.id,
                    0,
                )
                or 0
            )
            off_wait_time = int(
                output_settings_cluster.get(
                    self.AttributeDefs.on_with_timed_off_off_wait_time.id,
                    0,
                )
                or 0
            )

        if on_time > 0:
            if not is_active:
                return

            await output_cluster.command(
                OnOff.ServerCommandDefs.on_with_timed_off.id,
                on_off_control=0,
                on_time=on_time,
                off_wait_time=off_wait_time,
            )
            return

        command_id = (
            OnOff.ServerCommandDefs.on.id
            if is_active
            else OnOff.ServerCommandDefs.off.id
        )
        await output_cluster.command(command_id)

    def _normalize_linked_output(self, value: Any) -> LinkedOutput:
        """Normalize value to a supported linked-output enum value."""
        try:
            return LinkedOutput(value)
        except (ValueError, TypeError):
            return LinkedOutput.none

    def _make_bind_destination(self, endpoint_id: int) -> zdo_t.MultiAddress:
        """Create mode 0x03 IEEE+endpoint destination for bind/unbind requests."""
        return zdo_t.MultiAddress(
            addrmode=0x03,
            ieee=self.endpoint.device.ieee,
            endpoint=endpoint_id,
        )

    async def _sync_link_binding(
        self,
        previous_link: LinkedOutput,
        new_link: LinkedOutput,
    ) -> None:
        """Synchronize device-side input/output binding with current selector value."""
        try:
            previous_endpoint = self.OUTPUT_ENDPOINT_BY_LINK.get(previous_link)
            if previous_endpoint is not None:
                await self.endpoint.device.zdo.Unbind_req(
                    self.endpoint.device.ieee,
                    self.endpoint.endpoint_id,
                    self.cluster_id,
                    self._make_bind_destination(previous_endpoint),
                )

            new_endpoint = self.OUTPUT_ENDPOINT_BY_LINK.get(new_link)
            if new_endpoint is not None:
                await self.endpoint.device.zdo.Bind_req(
                    self.endpoint.device.ieee,
                    self.endpoint.endpoint_id,
                    self.cluster_id,
                    self._make_bind_destination(new_endpoint),
                )
        except asyncio.CancelledError:
            # Cancellation during shutdown/teardown is expected.
            return


class FrientOnOffOutput(CustomCluster, OnOff):
    """OnOff cluster that applies output timed settings to manual ON commands."""

    async def command(self, command_id, *args, **kwargs):
        """Map ON to OnWithTimedOff when output OnTime is configured."""
        try:
            resolved_command_id = self.server_commands[command_id].id
        except (KeyError, TypeError):
            resolved_command_id = int(command_id)

        if resolved_command_id != OnOff.ServerCommandDefs.on.id:
            return await super().command(command_id, *args, **kwargs)

        settings_cluster = self.endpoint.in_clusters.get(BinaryInput.cluster_id)
        if settings_cluster is None:
            return await super().command(command_id, *args, **kwargs)

        on_time = int(
            settings_cluster.get(
                FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.id,
                0,
            )
            or 0
        )
        off_wait_time = int(
            settings_cluster.get(
                FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.id,
                0,
            )
            or 0
        )

        if on_time <= 0:
            return await super().command(command_id, *args, **kwargs)

        return await super().command(
            OnOff.ServerCommandDefs.on_with_timed_off.id,
            on_off_control=OnOff.OnOffControl(0),
            on_time=on_time,
            off_wait_time=off_wait_time,
            **kwargs,
        )


(
    QuirkBuilder("frient A/S", "IOMZB-110")
    # Replace all input and output BinaryInput clusters with custom behavior/attributes.
    .replaces(FrientBinaryInput, endpoint_id=112)
    .replaces(FrientBinaryInput, endpoint_id=113)
    .replaces(FrientBinaryInput, endpoint_id=114)
    .replaces(FrientBinaryInput, endpoint_id=115)
    .replaces(FrientBinaryInput, endpoint_id=116)
    .replaces(FrientBinaryInput, endpoint_id=117)
    .replaces(FrientOnOffOutput, endpoint_id=116)
    .replaces(FrientOnOffOutput, endpoint_id=117)
    .prevent_default_entity_creation(
        endpoint_id=116,
        cluster_id=BinaryInput.cluster_id,
        function=lambda entity: entity.translation_key == "binary_input",
    )
    .prevent_default_entity_creation(
        endpoint_id=117,
        cluster_id=BinaryInput.cluster_id,
        function=lambda entity: entity.translation_key == "binary_input",
    )
    # Name the two outputs
    .change_entity_metadata(
        endpoint_id=116,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="116-6",
        new_fallback_name="Output 1",
        new_translation_key="frient_output_1",
    )
    .change_entity_metadata(
        endpoint_id=117,
        cluster_id=OnOff.cluster_id,
        unique_id_suffix="117-6",
        new_fallback_name="Output 2",
        new_translation_key="frient_output_2",
    )
    # And the two inputs
    .change_entity_metadata(
        endpoint_id=112,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="112-15",
        new_fallback_name="Input 1",
        new_translation_key="frient_input_1",
    )
    .change_entity_metadata(
        endpoint_id=113,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="113-15",
        new_fallback_name="Input 2",
        new_translation_key="frient_input_2",
    )
    .change_entity_metadata(
        endpoint_id=114,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="114-15",
        new_fallback_name="Input 3",
        new_translation_key="frient_input_3",
    )
    .change_entity_metadata(
        endpoint_id=115,
        cluster_id=BinaryInput.cluster_id,
        unique_id_suffix="115-15",
        new_fallback_name="Input 4",
        new_translation_key="frient_input_4",
    )
    # Per-input output link configuration.
    .enum(
        attribute_name=FrientBinaryInput.AttributeDefs.linked_output.name,
        enum_class=LinkedOutput,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=112,
        unique_id_suffix="in1_linked_output",
        translation_key="frient_in_1_linked_output",
        fallback_name="Input 1 control output",
    )
    .enum(
        attribute_name=FrientBinaryInput.AttributeDefs.linked_output.name,
        enum_class=LinkedOutput,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=113,
        unique_id_suffix="in2_linked_output",
        translation_key="frient_in_2_linked_output",
        fallback_name="Input 2 control output",
    )
    .enum(
        attribute_name=FrientBinaryInput.AttributeDefs.linked_output.name,
        enum_class=LinkedOutput,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=114,
        unique_id_suffix="in3_linked_output",
        translation_key="frient_in_3_linked_output",
        fallback_name="Input 3 control output",
    )
    .enum(
        attribute_name=FrientBinaryInput.AttributeDefs.linked_output.name,
        enum_class=LinkedOutput,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=115,
        unique_id_suffix="in4_linked_output",
        translation_key="frient_in_4_linked_output",
        fallback_name="Input 4 control output",
    )
    .switch(
        attribute_name=FrientBinaryInput.AttributeDefs.polarity.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=112,
        unique_id_suffix="in1_reverse_polarity",
        translation_key="frient_in_1_reverse_polarity",
        fallback_name="Input 1 reverse polarity",
    )
    .switch(
        attribute_name=FrientBinaryInput.AttributeDefs.polarity.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=113,
        unique_id_suffix="in2_reverse_polarity",
        translation_key="frient_in_2_reverse_polarity",
        fallback_name="Input 2 reverse polarity",
    )
    .switch(
        attribute_name=FrientBinaryInput.AttributeDefs.polarity.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=114,
        unique_id_suffix="in3_reverse_polarity",
        translation_key="frient_in_3_reverse_polarity",
        fallback_name="Input 3 reverse polarity",
    )
    .switch(
        attribute_name=FrientBinaryInput.AttributeDefs.polarity.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=115,
        unique_id_suffix="in4_reverse_polarity",
        translation_key="frient_in_4_reverse_polarity",
        fallback_name="Input 4 reverse polarity",
    )
    .number(
        attribute_name=FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=116,
        multiplier=0.1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unique_id_suffix="out1_on_with_timed_off_on_time",
        translation_key="frient_out_1_on_with_timed_off_on_time",
        fallback_name="Config Output 1 On Time",
    )
    .number(
        attribute_name=FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=116,
        multiplier=0.1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unique_id_suffix="out1_on_with_timed_off_off_wait_time",
        translation_key="frient_out_1_on_with_timed_off_off_wait_time",
        fallback_name="Config Output 1 Off Wait Time",
    )
    .number(
        attribute_name=FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=117,
        multiplier=0.1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unique_id_suffix="out2_on_with_timed_off_on_time",
        translation_key="frient_out_2_on_with_timed_off_on_time",
        fallback_name="Config Output 2 On Time",
    )
    .number(
        attribute_name=FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.name,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=117,
        multiplier=0.1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unique_id_suffix="out2_on_with_timed_off_off_wait_time",
        translation_key="frient_out_2_on_with_timed_off_off_wait_time",
        fallback_name="Config Output 2 Off Wait Time",
    )
    .add_to_registry()
)
