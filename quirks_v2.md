# Quirks v2

## Introduction

Quirks v2 use a fluent interface style. While this isn't common in python it was done to improve the readability of the source code and to make it human-friendly for non developers. The amount of boilerplate code has been significantly reduced and the need to specify a signature dictionary and a replacement dictionary has been removed. This should make it much easier for the community to contribute quirks.

## Goals

- Significantly reduce the amount of boilerplate code required to write a quirk
- Make it easier for the community to contribute quirks
- Make it easier to read and understand quirks
- Make it easier to maintain quirks
- Expose entities from a quirk
- Allow custom logic to determine if a quirk should be applied to a device
- Allow custom binding, reporting configuration or any sort of initialization logic without hacking the bind or configure_reporting methods

## QuirksV2RegistryEntry

- `add_to_registry_v2` - This method is used to add a quirk to the registry. It takes two arguments, the manufacturer and the model. It returns a `QuirksV2RegistryEntry` object.

The `QuirksV2RegistryEntry` class is used to build up a quirk. It has a number of methods that can be chained together to build up the quirk. The `QuirksV2RegistryEntry` class has the following methods:

### Device matching methods

<details>
  <summary>also_applies_to</summary>

This method allows specifying additional manufacturer and models that the quirk should apply to.

```python
"""
Register this quirks v2 entry for an additional manufacturer and model.

Args:
    manufacturer (str): The manufacturer of the device.
    model (str): The model of the device.

Returns:
    QuirksV2RegistryEntry: The updated QuirksV2RegistryEntry object.

"""
```

</details>

<details>
  <summary>filter</summary>

This method allows specifying a custom filter function that determines if the quirk should be applied to a device.

```python
"""Add a filter and returns self.

Args:
    filter_function (FilterType): The filter function to be added. It should take a single argument, a zigpy.device.Device instance, and return a boolean if the condition the filter is testing passes.

Returns:
    QuirksV2RegistryEntry: The instance of the QuirksV2RegistryEntry class.

Example:
    def some_filter(device: zigpy.device.Device) -> bool:
        # Your filter logic here

"""
```

</details>

### Device modification methods

<details>
  <summary>adds</summary>
This method allows adding a cluster to a device when the quirk is applied.

```python
"""
Add an AddsMetadata entry and return self.

This method allows adding a cluster to a device when the quirk is applied.

Args:
    cluster (int | type[Cluster | CustomCluster]): The cluster ID or a subclass of Cluster or CustomCluster.
    cluster_type (ClusterType, optional): The type of cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The endpoint ID. Defaults to 1.
    constant_attributes (dict[ZCLAttributeDef, typing.Any] | None, optional):
        A dictionary of ZCLAttributeDef instances and their values.
        These attributes will be added to the cluster when the quirk is applied and the values will be constant.
        Defaults to None.

Returns:
    QuirksV2RegistryEntry: The updated instance of QuirksV2RegistryEntry.

"""
```

</details>

<details>
  <summary>removes</summary>

This method allows removing a cluster from a device when the quirk is applied.

```python
"""Add a RemovesMetadata entry and returns self.

Args:
    cluster_id (int): The ID of the cluster to be removed.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.

Returns:
    QuirksV2RegistryEntry: The updated instance of QuirksV2RegistryEntry.

This method allows removing a cluster from a device when the quirk is applied.
"""
```

</details>

<details>
  <summary>replaces</summary>

This method allows replacing a cluster on a device when the quirk is applied.

```python
"""Add a ReplacesMetadata entry and returns self.

Args:
    replacement_cluster_class (type[Cluster | CustomCluster]): A subclass of Cluster or CustomCluster that will be used to create a new cluster instance to replace the existing cluster.
    cluster_id (int | None, optional): The cluster_id for the cluster to be removed. If not provided, the cluster_id of the replacement cluster will be used. Defaults to None.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The endpoint_id of the cluster. Defaults to 1.

Returns:
    QuirksV2RegistryEntry: The updated instance of the QuirksV2RegistryEntry class.
"""
```

</details>

<details>
  <summary>device_class</summary>

This method allows specifying a subclass of CustomDeviceV2 for a device when the quirk is applied.

```python
"""Set the custom device class to be used in this quirk and returns self.

Args:
    custom_device_class (type[CustomDeviceV2]): The custom device class to be used in this quirk.
        It must be a subclass of CustomDeviceV2.

Returns:
    QuirksV2RegistryEntry: The instance of the QuirksV2RegistryEntry class.
"""
```

</details>

<details>
  <summary>node_descriptor</summary>

This method allows specifying a custom node descriptor for a device when the quirk is applied.

```python
"""Set the node descriptor and returns self.

Args:
    node_descriptor (NodeDescriptor): The node descriptor to be set.

Returns:
    QuirksV2RegistryEntry: The updated instance of QuirksV2RegistryEntry.
"""
```

</details>

<details>
  <summary>skip_configuration</summary>

This method allows skipping the reporting configuration for all clusters on this device.

```python
"""Set the skip_configuration flag and returns self.

Args:
    skip_configuration (bool, optional): If True, reporting configuration will not be
        applied to any cluster on this device. Defaults to True.

Returns:
    QuirksV2RegistryEntry: The instance of the QuirksV2RegistryEntry class.
"""
```

</details>

<details>
  <summary>device_automation_triggers</summary>

This method allows specifying device automation triggers for a device when the quirk is applied.

</details>

### Methods for exposing entities

<details>
    <summary>enum</summary>

This method allows exposing an enum based entity in Home Assistant.

```python
"""Add an EntityMetadata containing ZCLEnumMetadata and return self.

This method allows exposing an enum based entity in Home Assistant.

Args:
    attribute_name (str): The name of the ZCL attribute this entity uses for its value.
    enum_class (type[Enum]): The class of the enum to use for the entity.
    cluster_id (int): The ID of the cluster.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    entity_type (EntityType, optional): The type of the entity. Defaults to EntityType.CONFIG.
    entity_platform (EntityPlatform, optional): The platform of the entity. Defaults to EntityPlatform.SELECT.
    initially_disabled (bool, optional): Whether the entity is initially disabled. Defaults to False.
    attribute_initialized_from_cache (bool, optional): Whether the attribute is initialized from the cluster cache. Defaults to True.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The modified QuirksV2RegistryEntry object.
"""
```

</details>

<details>
    <summary>sensor</summary>

This method allows exposing a sensor entity in Home Assistant.

```python
"""Add an EntityMetadata containing ZCLSensorMetadata and return self.

This method allows exposing a sensor entity in Home Assistant.

Args:
    attribute_name (str): The name of the ZCL attribute this entity uses for its value.
    cluster_id (int): The ID of the cluster.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    divisor (int, optional): The divisor for the sensor value. Defaults to 1.
    multiplier (int, optional): The multiplier for the sensor value. Defaults to 1.
    entity_type (EntityType, optional): The type of the entity. Defaults to EntityType.STANDARD.
    device_class (SensorDeviceClass | None, optional): The device class of the sensor. Defaults to None.
    state_class (SensorStateClass | None, optional): The state class of the sensor. Defaults to None.
    unit (str | None, optional): The unit of measurement for the sensor. Defaults to None.
    initially_disabled (bool, optional): Whether the sensor is initially disabled. Defaults to False.
    attribute_initialized_from_cache (bool, optional): Whether the attribute is initialized from the cluster cache. Defaults to True.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The updated QuirksV2RegistryEntry object.
"""
```

</details>

<details>
    <summary>binary_sensor</summary>

This method allows exposing a binary sensor entity in Home Assistant.

```python
"""Add an EntityMetadata containing BinarySensorMetadata and return self.

This method allows exposing a binary sensor entity in Home Assistant.

Args:
    attribute_name (str): The name of the attribute.
    cluster_id (int): The ID of the cluster.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    device_class (BinarySensorDeviceClass | None, optional): The device class of the binary sensor. Defaults to None.
    initially_disabled (bool, optional): Whether the binary sensor is initially disabled. Defaults to False.
    attribute_initialized_from_cache (bool, optional): Whether the attribute is initialized from the cluster cache. Defaults to True.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The registry entry for the binary sensor.
"""
```

</details>

<details>
    <summary>switch</summary>

This method allows exposing a switch entity in Home Assistant.

```python
"""Add an EntityMetadata containing SwitchMetadata and return self.

This method allows exposing a switch entity in Home Assistant.

Args:
    attribute_name (str): The name of the attribute.
    cluster_id (int): The ID of the cluster.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    force_inverted (bool, optional): Whether to force the attribute to be inverted. Defaults to False.
    invert_attribute_name (str | None, optional): The name of the attribute to invert. Defaults to None.
    off_value (int, optional): The value representing the off state. Defaults to 0.
    on_value (int, optional): The value representing the on state. Defaults to 1.
    entity_platform (EntityPlatform, optional): The platform of the entity. Defaults to EntityPlatform.SWITCH.
    initially_disabled (bool, optional): Whether the entity is initially disabled. Defaults to False.
    attribute_initialized_from_cache (bool, optional): Whether the attribute is initialized from the cluster cache. Defaults to True.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The updated QuirksV2RegistryEntry object.
"""
```

</details>

<details>
    <summary>number</summary>

This method allows exposing a number entity in Home Assistant.

```python
"""Add an EntityMetadata containing NumberMetadata and return self.

This method allows exposing a number entity in Home Assistant.

Args:
    attribute_name (str): The name of the attribute.
    cluster_id (int): The ID of the cluster.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    min_value (float | None, optional): The minimum value of the number. Defaults to None.
    max_value (float | None, optional): The maximum value of the number. Defaults to None.
    step (float | None, optional): The step value of the number. Defaults to None.
    unit (str | None, optional): The unit of the number. Defaults to None.
    mode (str | None, optional): The mode of the number. Defaults to None.
    multiplier (float | None, optional): The multiplier of the number. Defaults to None.
    device_class (NumberDeviceClass | None, optional): The device class of the number. Defaults to None.
    initially_disabled (bool, optional): Whether the number is initially disabled. Defaults to False.
    attribute_initialized_from_cache (bool, optional): Whether the attribute is initialized from the cluster cache. Defaults to True.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The modified QuirksV2RegistryEntry object.
"""
```

</details>

<details>
    <summary>write_attr_button</summary>

This method allows exposing a button entity in Home Assistant that writes a value to an attribute when pressed.

```python
"""Add an EntityMetadata containing WriteAttributeButtonMetadata and return self.

This method allows exposing a button entity in Home Assistant that writes
a value to an attribute when pressed.

Args:
    attribute_name (str): The name of the attribute to write.
    attribute_value (int): The value to write to the attribute.
    cluster_id (int): The ID of the cluster.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    entity_type (EntityType, optional): The type of the entity. Defaults to EntityType.CONFIG.
    initially_disabled (bool, optional): Whether the entity is initially disabled. Defaults to False.
    attribute_initialized_from_cache (bool, optional): Whether the attribute is initialized from the cluster cache. Defaults to True.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The modified QuirksV2RegistryEntry object.
"""
```

</details>

<details>
    <summary>command_button</summary>

This method allows exposing a button entity in Home Assistant that executes a ZCL command when pressed.

```python
"""Add an EntityMetadata containing ZCLCommandButtonMetadata and return self.

This method allows exposing a button entity in Home Assistant that executes
a ZCL command when pressed.

Args:
    command_name (str): The name of the ZCL command to be executed.
    cluster_id (int): The ID of the cluster to which the command belongs.
    command_args (tuple | None, optional): The arguments to be passed to the command. Defaults to None.
    command_kwargs (dict[str, Any] | None, optional): The keyword arguments to be passed to the command. Defaults to None.
    cluster_type (ClusterType, optional): The type of the cluster. Defaults to ClusterType.Server.
    endpoint_id (int, optional): The ID of the endpoint. Defaults to 1.
    entity_type (EntityType, optional): The type of the entity. Defaults to EntityType.CONFIG.
    initially_disabled (bool, optional): Whether the button is initially disabled. Defaults to False.
    translation_key (str | None, optional): The translation key for the entity. Defaults to None. If not provided, the attribute_name will be used.

Returns:
    QuirksV2RegistryEntry: The updated QuirksV2RegistryEntry object.
"""
```

</details>

## Breakdown of a minimal example

```python
from zigpy.quirks.v2 import add_to_registry_v2

(
    add_to_registry_v2("IKEA of Sweden", "TRADFRI remote control")
    .replaces(PowerConfig1CRCluster)
    .replaces(ScenesCluster, cluster_type=ClusterType.Client)
)
```

`add_to_registry_v2` this method is used to add a quirk to the registry. It takes two arguments, the manufacturer and the model. It returns a `QuirksV2RegistryEntry` object. This object has a number of methods that can be chained together to build up the quirk.

`replaces` this method is used to specify the cluster that the quirk should replace.

This quirk would have looked like this in the original quirks system:

https://github.com/zigpy/zha-device-handlers/blob/e4d0663aa4fb2f4bd0b41825f1942e3d29893375/zhaquirks/ikea/fivebtnremote.py#L387-L447
