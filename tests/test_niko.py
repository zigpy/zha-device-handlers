"""Tests for Niko quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

import zhaquirks

zhaquirks.setup()


SWITCH_SINGLE = (
    ["NIKO NV", "Single connectable switch,10A"],
    {"endpoint_ids": [0, 1, 242]},
)

SWITCH_DOUBLE = (
    ["NIKO NV", "Double connectable switch,10A"],
    {"endpoint_ids": [0, 1, 2, 242]},
)


# pylint: disable=R0903
class TestNikoSwitch:
    """Tests for Niko Connected Switches (552-721X1 and 552-721X2)."""

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    class TestClusters:
        """Test whether all clusters are present and complete."""

        def test_config_cluster(self, zigpy_device_from_v2_quirk, switch):
            """Test the configuration cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            cluster = device.endpoints[1].niko_config

            assert {attr.id: attr.access for attr in cluster.AttributeDefs} == {
                0x0000: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0100: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0104: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0105: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0107: foundation.ZCLAttributeAccess.from_str("rw"),
            }

        def test_state_cluster(self, zigpy_device_from_v2_quirk, switch):
            """Test the state cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            cluster = device.endpoints[1].niko_state

            assert {attr.id: attr.access for attr in cluster.AttributeDefs} == {
                0x0001: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0002: foundation.ZCLAttributeAccess.from_str("p"),
            }

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    # pylint: disable=R0903
    class TestConfiguration:
        """Test device configuration."""

        async def test_apply_custom_configuration(
            self, zigpy_device_from_v2_quirk, switch
        ):
            """Test whether attributes are set correctly."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            config_cluster = device.endpoints[1].niko_config
            state_cluster = device.endpoints[1].niko_state

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                await config_cluster.apply_custom_configuration()
                calls = request.mock_calls

                assert len(calls) == 1
                assert calls[0].kwargs["cluster"] == config_cluster.cluster_id
                assert (
                    calls[0].kwargs["command_id"]
                    == foundation.GeneralCommand.Write_Attributes
                )
                assert (
                    calls[0].kwargs["data"] == b"\x04\x5f\x12\x01\x02\x04\x01\x20\x01"
                )

            with mock.patch.object(
                state_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                await state_cluster.apply_custom_configuration()
                calls = request.mock_calls

                assert len(calls) == 1
                assert calls[0].kwargs["cluster"] == state_cluster.cluster_id
                assert (
                    calls[0].kwargs["command_id"]
                    == foundation.GeneralCommand.Write_Attributes
                )
                assert (
                    calls[0].kwargs["data"] == b"\x04\x5f\x12\x02\x02\x01\x00\x18\x1e"
                )
