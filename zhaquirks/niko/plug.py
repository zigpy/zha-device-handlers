"""Niko Smart plugs, 552-80698 and 552-80699.

The plugs work with ZHA as they are, these quirks only give them a name that matches
the other Niko devices.
"""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.niko import NIKO

# The 552-80698 reports its manufacturer as "Niko NV", the outlet as "NIKO NV".
NIKO_PLUG_MANUFACTURER = "Niko NV"

(
    QuirkBuilder(NIKO_PLUG_MANUFACTURER, "Smart plug Zigbee SE")
    .friendly_name(
        manufacturer="Niko",
        model="Smart plug with side earthing pin (552-80698)",
    )
    .add_to_registry()
)

(
    QuirkBuilder(NIKO_PLUG_MANUFACTURER, "Smart plug Zigbee PE")
    .applies_to(NIKO, "Smart plug Zigbee PE")
    .friendly_name(
        manufacturer="Niko",
        model="Smart plug with earthing pin (552-80699)",
    )
    .add_to_registry()
)
