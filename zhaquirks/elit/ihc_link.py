"""Device handler for ELIT Scandinavia IHC Link, require firmware version 1.1.14 or later."""

import logging

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.zcl.clusters.general import MultistateInput, OnOff
from zigpy.zdo import ZDO

from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

ELIT = "ELIT Scandinavia"

ACTION_TYPE = {
    0: COMMAND_RELEASE,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    3: COMMAND_TRIPLE,
    4: COMMAND_HOLD,
}

_LOGGER = logging.getLogger(__name__)


async def do_binding(cluster):
    await cluster.bind()


class EHCLinkDevice(CustomDeviceV2):
    """Quirk for ELIT Scandinavia EHC DIM Zigbee device."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def apply_custom_configuration(self, *args, **kwargs):
        for endpoint in self.endpoints.values():
            if isinstance(endpoint, ZDO):
                continue
            cluster = endpoint.in_clusters.get(MultistateInput.cluster_id)
            if cluster:
                await cluster.bind()
                await cluster.configure_reporting(
                    MultistateInput.AttributeDefs.present_value.id, 0, 0, 0
                )

            cluster = endpoint.in_clusters.get(OnOff.cluster_id)
            if cluster:
                await cluster.bind()

        # also apply custom configuration to clusters if defined
        await super().apply_custom_configuration(*args, **kwargs)


class CustomMultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if (
            attrid == MultistateInput.AttributeDefs.present_value.id
            and (action := ACTION_TYPE.get(value)) is not None
        ):
            event_args = {VALUE: value}
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


(
    QuirkBuilder(ELIT, "IHC Link")
    .device_class(EHCLinkDevice)
    .skip_configuration()
    .replace_cluster_occurrences(
        CustomMultistateInputCluster, replace_client_instances=False
    )
    .device_automation_triggers(
        {
            **{
                (press_type, f"Button A.{i}"): {
                    COMMAND: command,
                    ENDPOINT_ID: i,
                }
                for i in list(range(1, 9)) + list(range(11, 19))
                for press_type, command in {
                    (SHORT_PRESS, COMMAND_SINGLE),
                    (DOUBLE_PRESS, COMMAND_DOUBLE),
                    (TRIPLE_PRESS, COMMAND_TRIPLE),
                    (LONG_PRESS, COMMAND_HOLD),
                    (LONG_RELEASE, COMMAND_RELEASE),
                }
            },
            **{
                (press_type, f"Button B.{i}"): {
                    COMMAND: command,
                    ENDPOINT_ID: i + 30,
                }
                for i in list(range(1, 9)) + list(range(11, 19))
                for press_type, command in {
                    (SHORT_PRESS, COMMAND_SINGLE),
                    (DOUBLE_PRESS, COMMAND_DOUBLE),
                    (TRIPLE_PRESS, COMMAND_TRIPLE),
                    (LONG_PRESS, COMMAND_HOLD),
                    (LONG_RELEASE, COMMAND_RELEASE),
                }
            },
        }
    )
    .add_to_registry()
)
