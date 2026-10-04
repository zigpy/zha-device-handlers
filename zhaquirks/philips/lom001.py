"""Philips Hue Smart Plug family devices.

The Hue smart plugs are simple on/off relay devices, but Signify presumably
built their firmware on the same generic Zigbee lighting stack used in their
dimmable bulbs. As a result, the plugs advertise the standard Level Control
cluster (``0x0008``) on their main endpoint in addition to the On/Off cluster
(``0x0006``).

ZHA automatically exposes configuration entities for writable attributes of
the Level Control cluster, such as the "Power-on level" number (the
``start_up_current_level`` attribute, ``0x4000``), none of which have any
effect on a relay plug. The functional power-on setting for these plugs is
the "Power-on behaviour" select (the ``start_up_on_off`` attribute of the
On/Off cluster), which remains exposed.
"""

from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.builder import QuirkBuilder
from zhaquirks.philips import PHILIPS, SIGNIFY

(
    QuirkBuilder(PHILIPS, "LOM001") # Hue smart plug - EU
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
    .removes(LevelControl.cluster_id, endpoint_id=11)
    .add_to_registry()
)
