"""Device handler for the Cigol Electronics CIGOL_CONNECT."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import attrs
import zigpy.device
import zigpy.exceptions
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import MultistateInput, OnOff
from zigpy.zcl.foundation import Status

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.builder.metadata import QuirkDefinition
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.device import CustomZigpyDevice

if TYPE_CHECKING:
    from zigpy.application import ControllerApplication


_LOGGER = logging.getLogger(__name__)

MANUFACTURER = "Cigol Electronics"
MODEL = "CIGOL_CONNECT"

ACTION_TYPE = {
    0: COMMAND_RELEASE,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    4: COMMAND_HOLD,
}

PRESS_TYPES = {
    SHORT_PRESS: COMMAND_SINGLE,
    DOUBLE_PRESS: COMMAND_DOUBLE,
    LONG_PRESS: COMMAND_HOLD,
    LONG_RELEASE: COMMAND_RELEASE,
}

# An IHC input module has channels 1-8 and 11-18 on each Connect port.
PORT_A_INPUT_ENDPOINT_NAMES = {
    **{endpoint: f"input_a_{endpoint}" for endpoint in range(1, 9)},
    **{endpoint: f"input_a_{endpoint}" for endpoint in range(11, 19)},
}
PORT_B_INPUT_ENDPOINT_NAMES = {
    **{endpoint: f"input_b_{endpoint - 30}" for endpoint in range(31, 39)},
    **{endpoint: f"input_b_{endpoint - 30}" for endpoint in range(41, 49)},
}
INPUT_ENDPOINT_NAMES = {
    **PORT_A_INPUT_ENDPOINT_NAMES,
    **PORT_B_INPUT_ENDPOINT_NAMES,
}

# An IHC output module has eight channels on each Connect port.
PORT_A_OUTPUT_ENDPOINT_NAMES = {
    endpoint: f"Output A.{endpoint - 20}" for endpoint in range(21, 29)
}
PORT_B_OUTPUT_ENDPOINT_NAMES = {
    endpoint: f"Output B.{endpoint - 50}" for endpoint in range(51, 59)
}
OUTPUT_ENDPOINT_NAMES = {
    **PORT_A_OUTPUT_ENDPOINT_NAMES,
    **PORT_B_OUTPUT_ENDPOINT_NAMES,
}

INPUT_REPORTING_MIN_INTERVAL = 0
INPUT_REPORTING_MAX_INTERVAL = 3600
INPUT_REPORTING_CHANGE = 1


def present_value_to_action(value: int) -> str:
    """Convert a Multistate Input value to a readable sensor state."""
    return ACTION_TYPE.get(value, f"unknown_{value}")


def _build_device_automation_triggers(
    device: zigpy.device.Device,
) -> dict[tuple[str, str], dict[str, str | int]]:
    """Build triggers only for input endpoints exposed by this device."""
    return {
        (press_type, input_name): {
            COMMAND: command,
            ENDPOINT_ID: endpoint,
        }
        for endpoint, input_name in INPUT_ENDPOINT_NAMES.items()
        if endpoint in device.endpoints
        and MultistateInput.cluster_id in device.endpoints[endpoint].in_clusters
        for press_type, command in PRESS_TYPES.items()
    }


class CigolConnectDevice(CustomZigpyDevice):
    """Clone a Connect device and classify its controllable outputs as switches."""

    def __init__(
        self,
        application: ControllerApplication,
        ieee: t.EUI64,
        nwk: t.NWK,
        replaces: zigpy.device.Device,
    ) -> None:
        """Clone the interviewed device and normalize variable output endpoints."""
        super().__init__(application, ieee, nwk, replaces)

        self.device_automation_triggers = _build_device_automation_triggers(self)

        for endpoint in self.non_zdo_endpoints:
            if OnOff.cluster_id in endpoint.in_clusters:
                endpoint.profile_id = zha.PROFILE_ID
                endpoint.device_type = zha.DeviceType.ON_OFF_OUTPUT


class CigolConnectZHADevice(QuirkV2Device):
    """Expose only entity metadata backed by clusters on this device profile."""

    @property
    def quirk_metadata(self) -> QuirkDefinition:
        """Filter potential input entities against the interviewed endpoints."""
        definition = super().quirk_metadata
        entity_metadata = tuple(
            metadata
            for metadata in definition.entity_metadata
            if metadata.endpoint_id in self.endpoints
            and metadata.cluster_id
            in (
                self.endpoints[metadata.endpoint_id].zigpy_endpoint.in_clusters
                if metadata.cluster_type is ClusterType.Server
                else self.endpoints[metadata.endpoint_id].zigpy_endpoint.out_clusters
            )
        )
        return attrs.evolve(definition, entity_metadata=entity_metadata)


class CigolMultistateInputCluster(CustomCluster, MultistateInput):
    """Translate Connect input reports into ZHA button events."""

    async def apply_custom_configuration(self, *args, **kwargs) -> None:
        """Explicitly bind this input cluster and configure present-value reports."""
        endpoint_id = self.endpoint.endpoint_id

        try:
            bind_response = await self.bind()
        except (zigpy.exceptions.ZigbeeException, TimeoutError) as ex:
            _LOGGER.warning(
                "Cigol Connect endpoint %s: failed to bind Multistate Input: %s",
                endpoint_id,
                ex,
            )
        else:
            if bind_response and bind_response[0] == Status.SUCCESS:
                _LOGGER.debug(
                    "Cigol Connect endpoint %s: bound Multistate Input",
                    endpoint_id,
                )
            else:
                _LOGGER.warning(
                    "Cigol Connect endpoint %s: Multistate Input bind returned %s",
                    endpoint_id,
                    bind_response,
                )

        try:
            reporting_response = await self.configure_reporting(
                MultistateInput.AttributeDefs.present_value,
                INPUT_REPORTING_MIN_INTERVAL,
                INPUT_REPORTING_MAX_INTERVAL,
                INPUT_REPORTING_CHANGE,
            )
        except (zigpy.exceptions.ZigbeeException, TimeoutError) as ex:
            _LOGGER.warning(
                "Cigol Connect endpoint %s: failed to configure present_value "
                "reporting: %s",
                endpoint_id,
                ex,
            )
        else:
            _LOGGER.debug(
                "Cigol Connect endpoint %s: configured present_value reporting: %s",
                endpoint_id,
                reporting_response,
            )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if (
            attrid == MultistateInput.AttributeDefs.present_value.id
            and (action := ACTION_TYPE.get(value)) is not None
        ):
            self.listener_event(ZHA_SEND_EVENT, action, {VALUE: value})


def build_quirk():
    """Build and register the dynamic Connect quirk."""
    builder = (
        QuirkBuilder(MANUFACTURER, MODEL)
        .zha_device_class(CigolConnectZHADevice)
        .zigpy_device_class(CigolConnectDevice)
        .replace_cluster_occurrences(
            CigolMultistateInputCluster,
            replace_server_instances=True,
            replace_client_instances=False,
        )
    )

    for endpoint, output_name in OUTPUT_ENDPOINT_NAMES.items():
        builder.change_entity_metadata(
            endpoint_id=endpoint,
            cluster_id=OnOff.cluster_id,
            new_translation_key=(
                f"cigol_{output_name.lower().replace(' ', '_').replace('.', '_')}"
            ),
            new_fallback_name=output_name,
        )

    for endpoint, input_name in INPUT_ENDPOINT_NAMES.items():
        port = "A" if endpoint < 20 else "B"
        channel = endpoint if endpoint < 20 else endpoint - 30
        builder.sensor(
            attribute_name=MultistateInput.AttributeDefs.present_value.name,
            cluster_id=MultistateInput.cluster_id,
            endpoint_id=endpoint,
            suggested_display_precision=0,
            attribute_converter=present_value_to_action,
            unique_id_suffix="action",
            translation_key=f"cigol_{input_name}_action",
            fallback_name=f"Input {port}.{channel} action",
        )

    return builder.add_to_registry()


CIGOL_CONNECT_QUIRK = build_quirk()
