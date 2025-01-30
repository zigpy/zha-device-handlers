"""Tuya TY0201 temperature and humidity sensor."""

from zhaquirks.tuya import TuyaPowerConfigurationCluster2AA
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZ3000_bjawzodf", "TY0201")
    .applies_to("_TZ3000_zl1kmjqx", "TY0201")
    .applies_to("_TZ3000_zl1kmjqx", "")
    .replaces(TuyaPowerConfigurationCluster2AA)
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
