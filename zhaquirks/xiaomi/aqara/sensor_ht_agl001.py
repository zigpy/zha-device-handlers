"""Quirk for the Aqara Climate Sensor W100 (lumi.sensor_ht.agl001).

Exposes the three buttons (plus/center/minus = endpoints 1/2/3) as zha_event and
device-automation triggers via the shared Aqara ``MultistateInputCluster``, and battery
from the 0xFCC0 heartbeat struct. The W100 reports battery percent only in heartbeat
tag 102 — there is no tag-1 voltage, and the standard PowerConfiguration attribute
always reports 0 — so ``XiaomiCluster._parse_aqara_attributes`` maps tag 102 for this
model (matching zigbee2mqtt's TH-S04D converter,
https://github.com/Koenkk/zigbee-herdsman-converters/pull/10787).
"""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import COMMAND, DOUBLE_PRESS, LONG_PRESS, LONG_RELEASE, SHORT_PRESS
from zhaquirks.xiaomi import (
    AQARA,
    RelativeHumidityCluster,
    TemperatureMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfiguration,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    COMMAND_3_DOUBLE,
    COMMAND_3_HOLD,
    COMMAND_3_RELEASE,
    COMMAND_3_SINGLE,
    MultistateInputCluster,
)

PLUS_BUTTON = "plus"
CENTER_BUTTON = "center"
MINUS_BUTTON = "minus"


(
    QuirkBuilder(AQARA, "lumi.sensor_ht.agl001")
    .friendly_name(manufacturer="Aqara", model="Climate Sensor W100")
    .replaces(TemperatureMeasurementCluster)
    .replaces(RelativeHumidityCluster)
    .replaces(XiaomiPowerConfiguration)
    .replaces(XiaomiAqaraE1Cluster)
    .replaces(MultistateInputCluster)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .device_automation_triggers(
        {
            (SHORT_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, PLUS_BUTTON): {COMMAND: COMMAND_1_RELEASE},
            (SHORT_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_DOUBLE},
            (LONG_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_HOLD},
            (LONG_RELEASE, CENTER_BUTTON): {COMMAND: COMMAND_2_RELEASE},
            (SHORT_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_SINGLE},
            (DOUBLE_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_DOUBLE},
            (LONG_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_HOLD},
            (LONG_RELEASE, MINUS_BUTTON): {COMMAND: COMMAND_3_RELEASE},
        }
    )
    .add_to_registry()
)
