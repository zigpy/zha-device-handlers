"""Fixtures for all tests."""

from asynctest import CoroutineMock
import pytest
import zigpy.application
import zigpy.types


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
