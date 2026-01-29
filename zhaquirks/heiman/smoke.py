"""Smoke Sensor."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasWd
from zigpy.zdo.types import LogicalType, NodeDescriptor

(
    QuirkBuilder("HEIMAN", "CO_V15")
    .applies_to("HEIMAN", "SMOK_YDLV10")
    .node_descriptor(
        NodeDescriptor(
            logical_type=LogicalType.EndDevice,
            complex_descriptor_available=False,
            user_descriptor_available=False,
            aps_flags=0,
            frequency_band=NodeDescriptor.FrequencyBand.Freq2400MHz,
            mac_capability_flags=NodeDescriptor.MACCapabilityFlags.AllocateAddress,  # Clears MACCapabilityFlags.MainsPowered
            manufacturer_code=48042,
            maximum_buffer_size=64,
            maximum_incoming_transfer_size=0,
            server_mask=0,
            maximum_outgoing_transfer_size=0,
            descriptor_capability_field=(
                NodeDescriptor.DescriptorCapability.ExtendedActiveEndpointListAvailable
                | NodeDescriptor.DescriptorCapability.ExtendedSimpleDescriptorListAvailable
            ),
        )
    )
    .add_to_registry()
)

(
    QuirkBuilder("HEIMAN", "CO_CTPG")
    .node_descriptor(
        NodeDescriptor(
            logical_type=LogicalType.EndDevice,
            complex_descriptor_available=False,
            user_descriptor_available=False,
            aps_flags=0,
            frequency_band=NodeDescriptor.FrequencyBand.Freq2400MHz,
            mac_capability_flags=NodeDescriptor.MACCapabilityFlags.AllocateAddress,  # Clears MACCapabilityFlags.MainsPowered
            manufacturer_code=4627,
            maximum_buffer_size=64,
            maximum_incoming_transfer_size=0,
            server_mask=0,
            maximum_outgoing_transfer_size=0,
            descriptor_capability_field=(
                NodeDescriptor.DescriptorCapability.ExtendedActiveEndpointListAvailable
                | NodeDescriptor.DescriptorCapability.ExtendedSimpleDescriptorListAvailable
            ),
        )
    )
    .add_to_registry()
)

(
    QuirkBuilder("HEIMAN", "SmokeSensor-N-3.0")
    .applies_to("HEIMAN", "SmokeSensor-EF-3.0")
    .applies_to("HEIMAN", "SmokeSensor-EM")
    .removes(IasWd, endpoint_id=1)
    .add_to_registry()
)
