"""Run quirked devices through a ZHA gateway, adapted from ZHA's test helpers."""

from collections.abc import AsyncIterator
import contextlib
from datetime import datetime
import json
import pathlib
from typing import Any
from unittest.mock import AsyncMock, patch

from zha.application.gateway import Gateway
from zha.application.helpers import (
    CoordinatorConfiguration,
    QuirksConfiguration,
    ZHAConfiguration,
    ZHAData,
)
from zha.quirks import DeviceRegistry
from zha.zigbee.device import Device
import zigpy.application
import zigpy.config
import zigpy.device
from zigpy.profiles.zha import PROFILE_ID as ZHA_PROFILE_ID
import zigpy.state
import zigpy.types as t
import zigpy.zcl
from zigpy.zcl.clusters.general import Basic, Groups
import zigpy.zcl.foundation as zcl_f
import zigpy.zdo.types as zdo_t

DEVICES_DIR = pathlib.Path(__file__).parent / "data" / "devices"


class FakeApp(zigpy.application.ControllerApplication):
    """Controller application that sends nothing."""

    async def add_endpoint(self, descriptor):
        """Add an endpoint."""

    async def connect(self):
        """Connect."""

    async def disconnect(self):
        """Disconnect."""

    async def force_remove(self, dev):
        """Remove a device."""

    async def load_network_info(self, *, load_devices=False):
        """Load network info."""

    async def permit_ncp(self, time_s=60):
        """Permit joins."""

    async def permit_with_link_key(self, node, link_key, time_s=60):
        """Permit joins with a link key."""

    async def reset_network_info(self):
        """Reset network info."""

    async def send_packet(self, packet):
        """Send a packet."""

    async def start_network(self):
        """Start the network."""

    async def write_network_info(self, *, network_info, node_info):
        """Write network info."""

    async def request(self, *args: Any, **kwargs: Any):
        """Send a request."""

    async def move_network_to_channel(self, new_channel, *, num_broadcasts=5):
        """Change the channel."""


def make_app() -> FakeApp:
    """Create a controller application with a coordinator device."""
    app = FakeApp(
        {
            zigpy.config.CONF_DATABASE: None,
            zigpy.config.CONF_DEVICE: {zigpy.config.CONF_DEVICE_PATH: "/dev/null"},
            zigpy.config.CONF_NWK_BACKUP_ENABLED: False,
            zigpy.config.CONF_TOPO_SCAN_ENABLED: False,
            zigpy.config.CONF_OTA: {zigpy.config.CONF_OTA_ENABLED: False},
        }
    )

    app.state.node_info.nwk = 0x0000
    app.state.node_info.ieee = t.EUI64.convert("00:15:8d:00:02:32:4f:32")
    app.state.network_info.pan_id = 0x1234
    app.state.network_info.extended_pan_id = app.state.node_info.ieee
    app.state.network_info.channel = 15
    app.state.network_info.network_key.key = t.KeyData(range(16))
    app.state.counters = zigpy.state.CounterGroups()

    coordinator = app.add_device(
        nwk=app.state.node_info.nwk, ieee=app.state.node_info.ieee
    )
    coordinator.node_desc = zdo_t.NodeDescriptor(
        logical_type=zdo_t.LogicalType.Coordinator
    )
    coordinator.manufacturer = "Coordinator Manufacturer"
    coordinator.model = "Coordinator Model"

    ep = coordinator.add_endpoint(1)
    ep.add_input_cluster(Basic.cluster_id)
    ep.add_input_cluster(Groups.cluster_id)
    ep.profile_id = ZHA_PROFILE_ID

    return app


@contextlib.asynccontextmanager
async def zha_gateway() -> AsyncIterator[Gateway]:
    """Start a ZHA gateway on a fake controller application."""
    app = make_app()
    zha_data = ZHAData(
        config=ZHAConfiguration(
            coordinator_configuration=CoordinatorConfiguration(
                radio_type="ezsp", path="/dev/null"
            ),
            quirks_configuration=QuirksConfiguration(enabled=False),
        )
    )

    with (
        patch("zigpy.device.Device.request", return_value=[zcl_f.Status.SUCCESS]),
        patch("bellows.zigbee.application.ControllerApplication.new", return_value=app),
        patch("bellows.zigbee.application.ControllerApplication", return_value=app),
    ):
        gateway = await Gateway.async_from_config(zha_data)
        await gateway.async_initialize()
        await gateway.async_block_till_done()
        await gateway.async_initialize_devices_and_entities()

        try:
            yield gateway
        finally:
            await gateway.shutdown()


def _patch_cluster(cluster: zigpy.zcl.Cluster, values: dict[int, Any]) -> None:
    """Answer reads from `values` and accept every other request."""

    async def read_attributes_raw(attributes, *args, **kwargs):
        return (
            [
                zcl_f.ReadAttributeRecord(
                    attr_id,
                    zcl_f.Status.SUCCESS,
                    zcl_f.TypeValue(value=values[attr_id]),
                )
                if attr_id in values
                else zcl_f.ReadAttributeRecord(attr_id, zcl_f.Status.FAILURE)
                for attr_id in attributes
            ],
        )

    cluster.read_attributes_raw = AsyncMock(side_effect=read_attributes_raw)
    cluster.bind = AsyncMock(return_value=[0])
    cluster.unbind = AsyncMock(return_value=[0])
    cluster.configure_reporting_multiple = AsyncMock(
        side_effect=lambda config: dict.fromkeys(config, zcl_f.Status.SUCCESS)
    )


async def join_device_from_diagnostics(
    gateway: Gateway, name: str, registry: DeviceRegistry
) -> Device:
    """Join the device from a diagnostics file, quirked by `registry`."""
    data = json.loads((DEVICES_DIR / name).read_text())

    device = zigpy.device.Device(
        application=gateway.application_controller,
        ieee=t.EUI64.convert(data["ieee"]),
        nwk=t.NWK.convert(data["nwk"][2:]),
    )
    device.manufacturer = data["manufacturer"]
    device.model = data["model"]
    device.last_seen = datetime.fromisoformat(data["last_seen"])
    device.node_desc = zdo_t.NodeDescriptor(**data["node_descriptor"])

    for ep_id, ep_data in data["original_signature"]["endpoints"].items():
        ep = device.add_endpoint(int(ep_id))
        ep.profile_id = int(ep_data["profile_id"], 16)
        ep.device_type = int(ep_data["device_type"], 16)

        for cluster_id in ep_data["input_clusters"]:
            ep.add_input_cluster(int(cluster_id, 16))

        for cluster_id in ep_data["output_clusters"]:
            ep.add_output_cluster(int(cluster_id, 16))

    device = registry.resolve(device)

    for ep_id, ep_data in data["endpoints"].items():
        ep = device.endpoints[int(ep_id)]
        ep.request = AsyncMock(return_value=[0])

        for direction in ("in_clusters", "out_clusters"):
            for cluster_data in ep_data[direction]:
                cluster = getattr(ep, direction)[int(cluster_data["cluster_id"], 16)]
                values = {
                    int(attr["id"], 16): attr["value"]
                    for attr in cluster_data["attributes"]
                    if attr.get("value") is not None
                }

                for attr_id, value in values.items():
                    if attr_id in cluster.attributes:
                        cluster.update_attribute(attr_id, value)

                _patch_cluster(cluster, values)

    gateway.application_controller.devices[device.ieee] = device
    await gateway.async_device_initialized(device)
    await gateway.async_block_till_done()

    return gateway.get_device(device.ieee)
