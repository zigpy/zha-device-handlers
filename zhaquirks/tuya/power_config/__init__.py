"""Tuya Power Configuration Clusters."""

from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.tuya import TuyaLocalCluster


class TuyaPowerConfigurationCluster2AAA(PowerConfiguration, TuyaLocalCluster):
    """PowerConfiguration cluster for devices with 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: 4,
        PowerConfiguration.AttributeDefs.battery_rated_voltage.id: 15,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 2,
    }


class TuyaPowerConfigurationCluster2AA(PowerConfiguration, TuyaLocalCluster):
    """PowerConfiguration cluster for devices with 2 AA."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: 3,
        PowerConfiguration.AttributeDefs.battery_rated_voltage.id: 15,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 2,
    }


class TuyaPowerConfigurationCluster3AA(PowerConfiguration, TuyaLocalCluster):
    """PowerConfiguration cluster for devices with 3 AA."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: 3,
        PowerConfiguration.AttributeDefs.battery_rated_voltage.id: 15,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 3,
    }


class TuyaPowerConfigurationCluster4AA(PowerConfiguration, TuyaLocalCluster):
    """PowerConfiguration cluster for devices with 4 AA."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: 3,
        PowerConfiguration.AttributeDefs.battery_rated_voltage.id: 15,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 4,
    }
