"""Philips Hue Smart Plug family devices."""

from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.builder import QuirkBuilder
from zhaquirks.philips import PHILIPS, SIGNIFY

(
    QuirkBuilder(PHILIPS, "LOM001")  # Hue smart plug - EU
    .applies_to(SIGNIFY, "LOM001")
    .applies_to(PHILIPS, "LOM002")  # Hue smart plug bluetooth
    .applies_to(SIGNIFY, "LOM002")
    .applies_to(PHILIPS, "LOM003")  # Hue smart plug - UK
    .applies_to(SIGNIFY, "LOM003")
    .applies_to(PHILIPS, "LOM004")  # Hue smart plug bluetooth
    .applies_to(SIGNIFY, "LOM004")
    .applies_to(PHILIPS, "LOM005")  # Hue smart plug - AU
    .applies_to(SIGNIFY, "LOM005")
    .applies_to(PHILIPS, "LOM006")  # Hue smart plug - CH
    .applies_to(SIGNIFY, "LOM006")
    .applies_to(PHILIPS, "LOM007")  # Hue smart plug
    .applies_to(SIGNIFY, "LOM007")
    .applies_to(PHILIPS, "LOM008")  # Hue smart plug - EU
    .applies_to(SIGNIFY, "LOM008")
    .applies_to(PHILIPS, "LOM009")  # Hue smart plug - UK
    .applies_to(SIGNIFY, "LOM009")
    .applies_to(PHILIPS, "LOM010")  # Hue smart plug bluetooth
    .applies_to(SIGNIFY, "LOM010")
    .applies_to(PHILIPS, "LOM011")  # Hue smart plug - AU
    .applies_to(SIGNIFY, "LOM011")
    # Hide the dead level configuration entities (e.g. "Power-on level") that
    # ZHA would otherwise create from the plugs' Level Control cluster. The
    # functional "Power-on behaviour" setting on the On/Off cluster is not
    # affected.
    .prevent_default_entity_creation(endpoint_id=11, cluster_id=LevelControl.cluster_id)
    .add_to_registry()
)
