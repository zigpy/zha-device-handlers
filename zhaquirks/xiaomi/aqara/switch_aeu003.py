from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Identify
from zhaquirks.const import (
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    COMMAND_SINGLE,
)
from zhaquirks.xiaomi import (
    AQARA,
    AnalogInputCluster, 
    ElectricalMeasurementCluster,
    MeteringCluster
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_3_SINGLE,
    COMMAND_4_SINGLE,
)
from zhaquirks.xiaomi.aqara.opple_switch import MultistateInputCluster


(
    QuirkBuilder(AQARA, "lumi.switch.aeu003")
    .adds_endpoint(1, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(2, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(3, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(4, zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(21, zha.DeviceType.ON_OFF_SWITCH)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .adds(WindowCovering, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(ElectricalMeasurementCluster, endpoint_id=1)
    .replaces(MeteringCluster, endpoint_id=1)
    .replaces(AnalogInputCluster, endpoint_id=21)
    .device_automation_triggers({
        (COMMAND_SINGLE, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
        (COMMAND_SINGLE, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
    })
    .add_to_registry()
)