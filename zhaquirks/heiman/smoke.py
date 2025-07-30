"""Smoke Sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasWd, IasZone
import zigpy.zdo.types

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.heiman import HEIMAN








# Node descriptor for SMOK_YDLV10 and CO_V15
node_descriptor_1 = zigpy.zdo.types.NodeDescriptor(
    0x02, 0x40, 0x84 & 0b1111_1011, 0xBBAA, 0x40, 0x0000, 0x0000, 0x0000, 0x03
)

# Node descriptor for CO_CTPG
node_descriptor_2 = zigpy.zdo.types.NodeDescriptor(
    logical_type=2,
    complex_descriptor_available=0,
    user_descriptor_available=0,
    reserved=0,
    aps_flags=0,
    frequency_band=8,
    mac_capability_flags=132 & 0b1111_1011,
    manufacturer_code=4627,
    maximum_buffer_size=64,
    maximum_incoming_transfer_size=0,
    server_mask=0,
    maximum_outgoing_transfer_size=0,
    descriptor_capability_field=3,
)

(
    QuirkBuilder(HEIMAN, "SMOK_YDLV10")
    .applies_to(HEIMAN, "CO_V15")
    .removes(cluster_id=IasWd.cluster_id, endpoint_id=1)
    .node_descriptor(node_descriptor_1)
    .add_to_registry()
)

(
    QuirkBuilder(HEIMAN, "CO_CTPG")
    .removes(cluster_id=IasWd.cluster_id, endpoint_id=1)
    .node_descriptor(node_descriptor_2)
    .add_to_registry()
)

(
    QuirkBuilder("HEIMAN", "SmokeSensor-N-3.0")
    .applies_to("HEIMAN", "SmokeSensor-EF-3.0")
    .applies_to("HEIMAN", "SmokeSensor-EM")
    .removes(cluster_id=IasWd.cluster_id, endpoint_id=1)
    .add_to_registry()
)
