"""Module for Xiaomi Aqara quirks implementations."""
from zigpy import types
from zigpy.zcl.clusters.general import OnOff, MultistateInput

from ... import EventableCluster
from .. import BasicCluster


class BasicClusterDecoupled(BasicCluster):
    """Adds attributes for decoupled mode."""

    # Known Options for 'decoupled_mode_<button>':
    # * 254 (decoupled)
    # * 18 (relay controlled)
    manufacturer_attributes = {
        0xFF22: ("decoupled_mode_left", types.uint8_t),
        0xFF23: ("decoupled_mode_right", types.uint8_t),
    }


class WallSwitchMultistateInputCluster(EventableCluster, MultistateInput):
    """WallSwitchMultistateInputCluster: fire events corresponding to press type."""


class WallSwitchOnOffCluster(EventableCluster, OnOff):
    """WallSwitchOnOffCluster: fire events corresponding to press type."""
