"""Fixtures for all tests."""

from asynctest import CoroutineMock
import pytest
import zigpy.application
import zigpy.device
import zigpy.types

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
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

    async def shutdown(self):
        """Mock shutdown."""

    async def startup(self, *args):
        """Mock startup."""

    async def permit_ncp(self, *args):
        """Mock permit ncp."""

    mrequest = CoroutineMock()
    request = CoroutineMock()


@pytest.fixture(name="MockAppController")
def app_controller_mock():
    """App controller mock."""
    config = {"device": {"path": "/dev/ttyUSB0"}, "database": None}
    config = MockApp.SCHEMA(config)
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

    def _dev(quirk, ieee=None, nwk=zigpy.types.NWK(0x1234)):
        if ieee is None:
            ieee = ieee_mock
        models_info = quirk.signature.get(
            MODELS_INFO, (("Mock Manufacturer", "Mock Model"),)
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
        device = quirk(MockAppController, ieee, nwk, raw_device)
        MockAppController.devices[ieee] = device

        return device

    return _dev
