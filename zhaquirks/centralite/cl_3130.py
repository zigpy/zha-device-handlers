"""Device handler for centralite 3130."""

from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks import PowerConfigurationCluster
from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.legacy import CustomDevice
from zhaquirks.osram import OSRAM


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


class CentraLite3130(CustomDevice):
    """Custom device representing centralite 3130."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 2821]
        #  output_clusters=[3, 6, 8, 25]>
        MODELS_INFO: [(OSRAM, "LIGHTIFY Dimming Switch"), (CENTRALITE, "3130")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomPowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomPowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
        (SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_MOVE_ON_OFF},
        (SHORT_PRESS, DIM_DOWN): {COMMAND: COMMAND_MOVE},
    }

    # A short press is sent on release, as the same button sends a move when held,
    # and the device stops the move when the button is released. Both buttons send
    # the same stop, with or without on/off, so it belongs to the held button.
    button_event_entities = (
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, TURN_ON),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(SHORT_PRESS, DIM_UP),
                ),
                *(
                    ButtonEvent(
                        event_type=ButtonEventType.LONG_PRESS_END,
                        event_data={
                            COMMAND: command,
                            CLUSTER_ID: LevelControl.cluster_id,
                        },
                        while_held=True,
                    )
                    for command in (COMMAND_STOP, COMMAND_STOP_ON_OFF)
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button_up",
            translation_key="up_button",
            fallback_name="Up button",
        ),
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, TURN_OFF),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(SHORT_PRESS, DIM_DOWN),
                ),
                *(
                    ButtonEvent(
                        event_type=ButtonEventType.LONG_PRESS_END,
                        event_data={
                            COMMAND: command,
                            CLUSTER_ID: LevelControl.cluster_id,
                        },
                        while_held=True,
                    )
                    for command in (COMMAND_STOP, COMMAND_STOP_ON_OFF)
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button_down",
            translation_key="down_button",
            fallback_name="Down button",
        ),
    )
