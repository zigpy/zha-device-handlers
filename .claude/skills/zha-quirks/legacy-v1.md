# Legacy v1 quirks

New quirks use `QuirkBuilder`. Only change v1 quirks that already exist; when porting one to v2, check [unique-ids.md](unique-ids.md) so existing entities keep their IDs.

V1 quirks inherit from `CustomDevice` with explicit `signature` and `replacement` dicts. The signature must match the device exactly; the replacement defines what ZHA should use instead:

```python
from zhaquirks.legacy import CustomDevice
from zhaquirks.const import MODELS_INFO, ENDPOINTS, INPUT_CLUSTERS, ...

class MyDevice(CustomDevice):
    signature = {
        MODELS_INFO: [("Manufacturer", "Model")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [Basic.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id, CustomOnOffCluster],
            }
        },
    }
```

