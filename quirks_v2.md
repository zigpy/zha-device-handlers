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
