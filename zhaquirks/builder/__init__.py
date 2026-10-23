"""Public facade for the quirks v2 authoring API.

Re-exports everything quirk modules need to author a v2 quirk: the
`QuirkBuilder`, the reporting config, ZHA's entity/device-class enums and the
Home Assistant unit constants. This is the canonical import location
(`from zhaquirks.builder import ...`); the `zigpy.quirks.v2` shim forwards here for
backward compatibility with externally-maintained custom quirks.
"""

from zha.application import EntityPlatform, EntityType
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zha.application.platforms.number.device_class import NumberDeviceClass
from zha.application.platforms.sensor.device_class import (
    SensorDeviceClass,
    SensorStateClass,
)
from zha.units import *  # noqa: F401, F403

from zhaquirks.builder.builder import QuirkBuilder
from zhaquirks.builder.metadata import ReportingConfig

__all__ = [
    "BinarySensorDeviceClass",
    "EntityPlatform",
    "EntityType",
    "NumberDeviceClass",
    "QuirkBuilder",
    "ReportingConfig",
    "SensorDeviceClass",
    "SensorStateClass",
]
