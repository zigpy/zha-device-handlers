"""Device handler for Bosch RBSH-TRV0-ZB-EU thermostat."""

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters import general, hvac, homeautomation

from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    Groups,
    Time,
    PowerConfiguration,
    ZCLAttributeDef,
)
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class BoschOperatingMode(t.enum8):
    Schedule = 0x00
    Manual = 0x01
    Pause = 0x05


class State(t.enum8):
    Off = 0x00
    On = 0x01


class BoschDisplayOrientation(t.enum8):
    Normal = 0x00
    Flipped = 0x01


class BoschDisplayedTemperature(t.enum8):
    Target = 0x00
    Measured = 0x01


class BoschThermostatCluster(CustomCluster, Thermostat):
    """Bosch thermostat cluster."""

    class AttributeDefs(Thermostat.AttributeDefs):
        operating_mode = ZCLAttributeDef(
            id=t.uint16_t(0x4007),
            type=BoschOperatingMode,
            is_manufacturer_specific=True,
        )

        pi_heating_demand = ZCLAttributeDef(
            id=t.uint16_t(0x4020),
            # Values range from 0-100
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        window_open = ZCLAttributeDef(
            id=t.uint16_t(0x4042),
            type=State,
            is_manufacturer_specific=True,
        )

        boost = ZCLAttributeDef(
            id=t.uint16_t(0x4043),
            type=State,
            is_manufacturer_specific=True,
        )


class BoschUserInterfaceCluster(CustomCluster, UserInterface):
    """Bosch UserInterface cluster."""

    class AttributeDefs(UserInterface.AttributeDefs):
        display_orientation = ZCLAttributeDef(
            id=t.uint16_t(0x400B),
            type=BoschDisplayOrientation,
            is_manufacturer_specific=True,
        )

        display_ontime = ZCLAttributeDef(
            id=t.uint16_t(0x403A),
            # Usable values range from 2-30
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        display_brightness = ZCLAttributeDef(
            id=t.uint16_t(0x403B),
            # Values range from 0-10
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        displayed_temperature = ZCLAttributeDef(
            id=t.uint16_t(0x4039),
            type=BoschDisplayedTemperature,
            is_manufacturer_specific=True,
        )


class BoschThermostat(CustomDevice):
    """Bosch thermostat custom device."""

    signature = {
        MODELS_INFO: [("BOSCH", "RBSH-TRV0-ZB-EU")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=769
            # device_version=1
            # input_clusters=[0, 1, 3, 4, 32, 513, 516, 2821]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    general.Basic.cluster_id,
                    general.PowerConfiguration.cluster_id,
                    general.Identify.cluster_id,
                    general.Groups.cluster_id,
                    general.PollControl.cluster_id,
                    hvac.Thermostat.cluster_id,
                    hvac.UserInterface.cluster_id,
                    homeautomation.Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [general.Ota.cluster_id,
                                  general.Time.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    BoschThermostatCluster,
                    BoschUserInterfaceCluster,
                    Diagnostic,
                    Groups,
                    Identify,
                    Ota,
                    PollControl,
                    PowerConfiguration,
                    Time,
                ],
                OUTPUT_CLUSTERS: [Ota, Time],
            },
        },
    }
