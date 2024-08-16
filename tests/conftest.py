"""Fixtures for all tests."""

from unittest.mock import AsyncMock, Mock

import pytest
import zigpy.application
import zigpy.device
import zigpy.quirks
import zigpy.types
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class MockApp(zigpy.application.ControllerApplication):
    """App Controller."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._ieee = zigpy.types.EUI64(b"Zigbee78")
        self._nwk = zigpy.types.NWK(0x0000)

    async def probe(self, *args):
        """Probe method."""
        return True

    async def startup(self, *args):
        """Mock startup."""

    async def shutdown(self, *args):
        """Mock shutdown."""

    async def permit_ncp(self, *args):
        """Mock permit ncp."""

    async def broadcast(self, *args, **kwargs):
        """Mock broadcast."""

    async def connect(self, *args, **kwargs):
        """Mock connect."""

    async def disconnect(self, *args, **kwargs):
        """Mock disconnect."""

    async def force_remove(self, *args, **kwargs):
        """Mock force_remove."""

    async def load_network_info(self, *args, **kwargs):
        """Mock load_network_info."""

    async def permit_with_key(self, *args, **kwargs):
        """Mock permit_with_key."""

    async def reset_network_info(self, *args, **kwargs):
        """Mock reset_network_info."""

    async def send_packet(self, *args, **kwargs):
        """Mock send_packet."""

    async def start_network(self, *args, **kwargs):
        """Mock start_network."""

    async def permit_with_link_key(self, *args, **kwargs):
        """Mock permit_with_link_key."""

    async def write_network_info(self, *args, **kwargs):
        """Mock write_network_info."""

    async def add_endpoint(self, descriptor):
        """Mock add_endpoint."""

    mrequest = AsyncMock()
    request = AsyncMock(return_value=(foundation.Status.SUCCESS, None))


@pytest.fixture(name="MockAppController")
def app_controller_mock():
    """App controller mock."""
    config = {"device": {"path": "/dev/ttyUSB0"}, "database": None}
    app = MockApp(config)
    return app


@pytest.fixture
def ieee_mock():
    """Return a static ieee."""
    return zigpy.types.EUI64([1, 2, 3, 4, 5, 6, 7, 8])


@pytest.fixture
def zigpy_device_mock(MockAppController, ieee_mock):
    """Zigpy device mock."""

    def _dev(ieee=None, nwk=zigpy.types.NWK(0x1234)):
        if ieee is None:
            ieee = ieee_mock
        device = MockAppController.add_device(ieee, nwk)
        return device

    return _dev


@pytest.fixture
def zigpy_device_from_quirk(MockAppController, ieee_mock):
    """Create zigpy device from Quirk's signature."""

    def _dev(quirk, ieee=None, nwk=zigpy.types.NWK(0x1234), apply_quirk=True):
        if ieee is None:
            ieee = ieee_mock
        models_info = quirk.signature.get(
            MODELS_INFO,
            (
                (
                    quirk.signature.get(MANUFACTURER, "Mock Manufacturer"),
                    quirk.signature.get(MODEL, "Mock Model"),
                ),
            ),
        )
        manufacturer, model = models_info[0]

        raw_device = zigpy.device.Device(MockAppController, ieee, nwk)
        raw_device.manufacturer = manufacturer
        raw_device.model = model

        endpoints = quirk.signature.get(ENDPOINTS, {})
        for ep_id, ep_data in endpoints.items():
            ep = raw_device.add_endpoint(ep_id)
            ep.profile_id = ep_data.get(PROFILE_ID, 0x0260)
            ep.device_type = ep_data.get(DEVICE_TYPE, 0xFEDB)
            in_clusters = ep_data.get(INPUT_CLUSTERS, [])
            for cluster_id in in_clusters:
                ep.add_input_cluster(cluster_id)
            out_clusters = ep_data.get(OUTPUT_CLUSTERS, [])
            for cluster_id in out_clusters:
                ep.add_output_cluster(cluster_id)

        if not apply_quirk:
            return raw_device

        device = quirk(MockAppController, ieee, nwk, raw_device)
        MockAppController.devices[ieee] = device

        return device

    return _dev


@pytest.fixture
def zigpy_device_from_v2_quirk(MockAppController, ieee_mock):
    """Create zigpy device from Quirk's signature."""

    def _dev(
        manufacturer: str,
        model: str,
        endpoint_ids: list[int] = [1],
        ieee=None,
        nwk=zigpy.types.NWK(0x1234),
        apply_quirk=True,
    ):
        if ieee is None:
            ieee = ieee_mock

        raw_device = zigpy.device.Device(MockAppController, ieee, nwk)
        raw_device.manufacturer = manufacturer
        raw_device.model = model

        for endpoint_id in endpoint_ids:
            ep = raw_device.add_endpoint(endpoint_id)
            # basic is mandatory
            if endpoint_id == 1:
                ep.add_input_cluster(Basic.cluster_id)

        quirked = zigpy.quirks.get_device(raw_device)

        if not apply_quirk:
            for ep_id, ep_data in quirked.endpoints.items():
                if ep_id != 0:
                    ep = raw_device.add_endpoint(ep_id)
                    ep.profile_id = ep_data.get(PROFILE_ID, 0x0260)
                    ep.device_type = ep_data.get(DEVICE_TYPE, 0xFEDB)
                    in_clusters = ep_data.get(INPUT_CLUSTERS, [])
                    for cluster_id in in_clusters:
                        ep.add_input_cluster(cluster_id)
                    out_clusters = ep_data.get(OUTPUT_CLUSTERS, [])
                    for cluster_id in out_clusters:
                        ep.add_output_cluster(cluster_id)
            return raw_device

        MockAppController.devices[ieee] = quirked

        return quirked

    return _dev


@pytest.fixture
def assert_signature_matches_quirk():
    """Return a function that can be used to check if a given quirk matches a signature."""

    def _check(quirk, signature):
        # Check device signature as copied from Zigbee device signature window for the device
        class FakeDevEndpoint:
            def __init__(self, endpoint):
                self.endpoint = endpoint

            def __getattr__(self, key):
                if key == "device_type":
                    return int(self.endpoint[key], 16)
                elif key in ("in_clusters", "out_clusters"):
                    return [int(cluster_id, 16) for cluster_id in self.endpoint[key]]
                else:
                    return self.endpoint[key]

        class FakeDevice:
            nwk = 0

            def __init__(self, signature):
                self.endpoints = {
                    int(id): FakeDevEndpoint(ep)
                    for id, ep in signature["endpoints"].items()
                }
                for attr in ("manufacturer", "model", "ieee"):
                    setattr(self, attr, signature.get(attr))

            def __getitem__(self, key):
                # Return item from signature, or None if not given
                return self.endpoints.get(key)

            def __getattr__(self, key):
                # Return item from signature, or None if not given
                return self.endpoints.get(key)

        test_dev = FakeDevice(signature)
        test_dev._application = Mock()
        test_dev._application._dblistener = None

        device = zigpy.quirks.get_device(test_dev)
        assert isinstance(device, quirk)

    return _check
