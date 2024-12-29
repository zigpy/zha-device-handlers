"""Tuya TY0201 temperature and humidity sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.tuya import TuyaPowerConfigurationCluster2AA
from zhaquirks.tuya.builder import TuyaRelativeHumidity, TuyaTemperatureMeasurement

(
    QuirkBuilder("_TZ3000_bjawzodf", "TY0201")
    .applies_to("_TZ3000_zl1kmjqx", "TY0201")
    .applies_to("_TZ3000_zl1kmjqx", "")
    .replaces(TuyaRelativeHumidity)
    .replaces(TuyaTemperatureMeasurement)
    .replaces(TuyaPowerConfigurationCluster2AA)
    .skip_configuration()
    .add_to_registry()
)
