"""Develco IO Module."""

from zigpy.quirks.v2 import QuirkBuilder

(
    QuirkBuilder("frient A/S", "IOMZB-110")
    # Name the two outputs
    # .add_metadata(unique_id="116-0x0006-on_off", name="COM 1")
    # .add_metadata(unique_id="117-0x0006-on_off", name="COM 2")
    # And the two inputs
    # .add_metadata(unique_id="112-0x000f-binary_input", name="IN1")
    # .add_metadata(unique_id="112-0x000f-binary_input", name="IN2")
    # .add_metadata(unique_id="112-0x000f-binary_input", name="IN3")
    # .add_metadata(unique_id="112-0x000f-binary_input", name="IN4")
    .add_to_registry()
)
