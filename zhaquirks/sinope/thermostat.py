"""
This module handles quirks of the  Sinopé Technologies thermostat.

manufacturer specific cluster implements attributes to control displaying
of outdoor temperature, setting occupancy on/off and setting device time.
"""

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from . import SINOPE
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01


class SinopeTechnologiesThermostat(CustomDevice):
    """SinopeTechnologiesThermostat custom device."""

    class SinopeTechnologiesManufacturerCluster(CustomCluster):
        """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

        cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
        name = "Sinopé Technologies Manufacturer specific"
        ep_attribute = "sinope_manufacturer_specific"
        attributes = {
            0x0010: ("outdoor_temp", t.int16s),
            0x0020: ("secs_since_2k", t.uint32_t),
        }
        client_commands = {}
        server_commands = {}

        def __init__(self, *args, **kwargs):
            """Init method."""
            super().__init__(*args, **kwargs)
            self._attridx = {
                attrname: attrid
                for attrid, (attrname, datatype) in self.attributes.items()
            }

    class SinopeTechnologiesThermostatCluster(CustomCluster, Thermostat):
        """SinopeTechnologiesThermostatCluster custom cluster."""

        def __init__(self, *args, **kwargs):
            """Init method."""
            super().__init__(*args, **kwargs)
            self.attributes = Thermostat.attributes.copy()
            self.attributes[0x0400] = ("set_occupancy", t.enum8)
            self._attridx = {
                attrname: attrid
                for attrid, (attrname, datatype) in self.attributes.items()
            }
            self._client_command_idx = {
                cmd_name: cmd_id
                for cmd_id, (cmd_name, schema, is_reply) in self.client_commands.items()
            }
            self._server_command_idx = {
                cmd_name: cmd_id
                for cmd_id, (cmd_name, schema, is_reply) in self.server_commands.items()
            }

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=0 input_clusters=[0, 3, 4, 5, 513, 516, 1026, 2820,
        # 2821, 65281] output_clusters=[65281, 25]>
        MODELS_INFO: [(SINOPE, "TH1123ZB"), (SINOPE, "TH1124ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0301,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Thermostat.cluster_id,
                    UserInterface.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, SINOPE_MANUFACTURER_CLUSTER_ID],
            },
            # <SimpleDescriptor endpoint=196 profile=49757 device_type=769
            # device_version=0 input_clusters=[1] output_clusters=[]>
            196: {
                PROFILE_ID: 0xC25D,
                DEVICE_TYPE: 0x0301,
                INPUT_CLUSTERS: [PowerConfiguration.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    Identify,
                    Groups,
                    Scenes,
                    UserInterface,
                    TemperatureMeasurement,
                    ElectricalMeasurement,
                    Diagnostic,
                    SinopeTechnologiesThermostatCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota, SINOPE_MANUFACTURER_CLUSTER_ID],
            },
            196: {INPUT_CLUSTERS: [PowerConfiguration]},
        }
    }
