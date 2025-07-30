"""Konke Button Remote."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.konke import KONKE, KonkeOnOffCluster
from zhaquirks.quirk_ids import KONKE_BUTTON

KONKE_CLUSTER_ID = 0xFCC0




(
    QuirkBuilder(KONKE, "3AFE280100510001")
    .applies_to(KONKE, "3AFE170100510001")
    .replaces_endpoint(endpoint_id=1, profile_id=zha.PROFILE_ID, device_type=zha.DeviceType.REMOTE_CONTROL)
    .replaces(replacement_cluster_class=PowerConfigurationCluster)
    .replaces(replacement_cluster_class=KonkeOnOffCluster)
    .device_automation_triggers({
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
    })
    .add_to_registry()
)


