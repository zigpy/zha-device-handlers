"""Tests for MOES Tuya SOS button quirk."""
import pytest
from unittest.mock import MagicMock, patch
from zhaquirks.const import BUTTON, COMMAND, DOUBLE_PRESS, LONG_PRESS, SHORT_PRESS

# Adjust this import to match your actual file path in the repo
from zhaquirks.tuya.ts0601_sos import (
    HEARTBEAT_EVENT,
    TuyaSOSButton,
    TuyaSOSButtonCluster,
)


@pytest.fixture
def cluster():
    """Create a TuyaSOSButtonCluster instance with a mocked endpoint."""
    endpoint = MagicMock()
    c = TuyaSOSButtonCluster(endpoint)
    c.listener_event = MagicMock()
    return c


def make_payload(command_id):
    """Helper to build a mock payload with a command_id."""
    payload = MagicMock()
    payload.command_id = command_id
    return payload


# --- Signature / replacement sanity checks ---

def test_signature_model():
    assert ("_TZE200_vrcfo4i0", "TS0601") in TuyaSOSButton.signature["models_info"]


def test_device_automation_triggers():
    triggers = TuyaSOSButton.device_automation_triggers
    assert (SHORT_PRESS, BUTTON) in triggers
    assert (DOUBLE_PRESS, BUTTON) in triggers
    assert (LONG_PRESS, BUTTON) in triggers


# --- handle_cluster_request: happy-path press types ---

def test_short_press_fires_event(cluster):
    hdr = MagicMock()
    cluster.handle_cluster_request(hdr, [make_payload(1050)])
    cluster.listener_event.assert_called_once_with(
        "zha_send_event", SHORT_PRESS, {"unique_id": 1050}
    )


def test_double_press_fires_event(cluster):
    hdr = MagicMock()
    cluster.handle_cluster_request(hdr, [make_payload(1051)])
    cluster.listener_event.assert_called_once_with(
        "zha_send_event", DOUBLE_PRESS, {"unique_id": 1051}
    )


def test_long_press_fires_event(cluster):
    hdr = MagicMock()
    cluster.handle_cluster_request(hdr, [make_payload(1053)])
    cluster.listener_event.assert_called_once_with(
        "zha_send_event", LONG_PRESS, {"unique_id": 1053}
    )


# --- Heartbeat: must NOT fire a ZHA event ---

def test_heartbeat_does_not_fire_event(cluster):
    hdr = MagicMock()
    cluster.handle_cluster_request(hdr, [make_payload(515)])
    cluster.listener_event.assert_not_called()


def test_heartbeat_logs_debug(cluster):
    hdr = MagicMock()
    with patch("zhaquirks.tuya.ts0601_sos._LOGGER") as mock_log:
        cluster.handle_cluster_request(hdr, [make_payload(515)])
        mock_log.debug.assert_called_once()
        assert "515" in mock_log.debug.call_args[0][0] or \
               "Heartbeat" in mock_log.debug.call_args[0][0]


# --- Unknown dp_id: fallback action ---

def test_unknown_dp_id_fires_fallback_event(cluster):
    hdr = MagicMock()
    cluster.handle_cluster_request(hdr, [make_payload(9999)])
    cluster.listener_event.assert_called_once_with(
        "zha_send_event", "button_9999", {"unique_id": 9999}
    )


# --- Exception path: empty args should not raise ---

def test_empty_args_does_not_raise(cluster):
    hdr = MagicMock()
    with patch("zhaquirks.tuya.ts0601_sos._LOGGER") as mock_log:
        cluster.handle_cluster_request(hdr, [])  # IndexError internally
        mock_log.error.assert_called_once()
        assert "Error" in mock_log.error.call_args[0][0]


# --- getattr fallback: payload missing command_id ---

def test_missing_command_id_fires_fallback_event(cluster):
    hdr = MagicMock()
    payload = MagicMock(spec=[])  # no attributes at all → getattr returns "unknown"
    cluster.handle_cluster_request(hdr, [payload])
    cluster.listener_event.assert_called_once_with(
        "zha_send_event", "button_unknown", {"unique_id": "unknown"}
    )