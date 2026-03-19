"""Gledopto GL-C-009P v2 quirk."""

from zigpy.zcl.clusters.lighting import Color

from zhaquirks.v2 import QuirkBuilder

# This V2 quirk handles the GL-C-009P when in Dimmer Mode (Red LED).
# It removes the non-functional Color cluster to ensure the UI only shows brightness.
(QuirkBuilder("GLEDOPTO", "GL-C-009P").removes(Color.cluster_id).add_to_registry())
