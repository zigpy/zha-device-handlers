"""LIDL PSBZS A1 water valve."""
from __future__ import annotations

import asyncio
import logging

from typing import Dict

import zigpy
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time
)
from zigpy.quirks import CustomDevice
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaOnOff,
    TuyaDPType,
    TuyaMCUCluster,
    TuyaPowerConfigurationCluster2AA
)

_LOGGER = logging.getLogger(__name__)


async def cast_tuya_magic_spell_task(
        dev: zigpy.device.Device, tries: int = 100, rejoin: bool = False
) -> None:
    """Initialize device so that all endpoints become available."""
    import inspect

    basic_cluster = dev.endpoints[1].in_clusters[0]

    # The magic spell is needed only once.
    # TODO: Improve by doing this only once (successfully).

    # Magic spell - part 1
    # Note: attribute order is important
    attr_to_read = [
        "manufacturer",
        "zcl_version",
        "app_version",
        "model",
        "power_source",
        0xFFFE,
    ]
    if "tries" in inspect.getfullargspec(basic_cluster.read_attributes)[0]:
        _LOGGER.debug(f"Cast Tuya Magic Spell on {dev.ieee!r} with {tries} tries")
        res = await basic_cluster.read_attributes(attr_to_read, tries=tries)
    else:
        _LOGGER.debug(f"Cast Tuya Magic Spell on {dev.ieee!r}")
        res = await basic_cluster.read_attributes(attr_to_read)

    _LOGGER.debug(f"Tuya Magic Spell result {res!r} for {dev.ieee!r}")

    # # Magic spell - part 2 (skipped - does not seem to be needed)
    # attr_to_write={0xffde:13}
    # basic_cluster.write_attributes(attr_to_write)

    if rejoin:
        # Leave with rejoin - may need to be adjuste to work everywhere
        # or require a minimum zigpy version
        # This should have the device leave and rejoin immediately triggering
        # the discovery of the endpoints that appear after the magic trick

        # Note: this is not validated yet and disabled by default
        _LOGGER.debug(f"Send leave with rejoin request to {dev.ieee!r}")
        res = await dev.zdo.request(0x0034, dev.ieee, 0x01, tries)
        _LOGGER.debug(f"Leave with rejoin result {res!r} for {dev.ieee!r}")

        app = dev.application
        # Delete the device from the database
        app.listener_event("device_removed", dev)

        # Delete the device from zigpy
        app.devices.pop(dev.ieee, None)


def cast_tuya_magic_spell(dev: zigpy.device.Device, tries: int = 3) -> None:
    """Set up the magic spell asynchronously."""

    # Note for sleepy devices the number of tries may need to be increased to 100.

    dev._magic_spell_task = asyncio.create_task(
        cast_tuya_magic_spell_task(dev, tries=tries)
    )


class TuyaWaterValveManufCluster(TuyaMCUCluster):
    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            0xef01: ("timer", t.uint32_t, True),
            0xef02: ("timer_time_left", t.uint32_t, True),
            0xef03: ("frost_lock", t.Bool, True),
            0xef04: ("frost_lock_reset", t.Bool, True),  # 0 resets frost lock
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            TuyaDPType.BOOL,
        ),
        5: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "timer",
            TuyaDPType.VALUE,
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "timer_time_left",
            TuyaDPType.VALUE,
        ),
        11: DPToAttributeMapping(
            TuyaPowerConfigurationCluster2AA.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
        ),
        108: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "frost_lock",
            TuyaDPType.BOOL,
            lambda x: not x,  # invert for lock entity
        ),
        109: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "frost_lock_reset",
            TuyaDPType.BOOL,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
    }


class ParksidePSBZS(CustomDevice):
    """LIDL Parkside water without implemented scheduler."""

    def __init__(self, *args, **kwargs):
        """Initialize with task."""
        super().__init__(*args, **kwargs)

        # cast_tuya_magic_spell(self, tries=3)
        self._init_plug_task = asyncio.create_task(self.spell())

    async def spell(self) -> None:
        """Initialize device so that all endpoints become available."""
        basic_cluster = self.endpoints[1].in_clusters[0]

        attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
        await basic_cluster.read_attributes(attr_to_read)
        _LOGGER.debug("Device class is casting Tuya Magic Spell")

    signature = {
        MODELS_INFO: [("_TZE200_htnnfasr", "TS0601")],  # HG06875
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 1, 3, 4, 5, 6, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaWaterValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    TuyaPowerConfigurationCluster2AA,
                    TuyaWaterValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
