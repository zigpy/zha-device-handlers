### Prerequisites
- You have read this repository's [readme file](README.md), at least vaguely familiarizing yourself with the concepts of `endpoints`, `clusters` and `attributes`.
- You have basic knowledge of the Python programming language, or are at least confident enough in your ability to learn how to use it. It's nothing particularly scary.
- Any devices, be it your HA host, or a quirky device, belong to you.

## 0. A simplified overview.
Any **device** has one or more **endpoints**. Any endpoint has one or more **clusters** of functionality, and any cluster has a number of **attributes**, which can be readable, writable, reportable or any combination of the three. Any attribute has an ID, a name, a data type, and a value. The value is what we're generally after.

## 1. Discovering what a device hides.
Before attempting to surface any attributes to ZHA, making it available as state or configuration in Home Assistant, you need to know **where** the attribute in question lives: which **ID** of which **cluster** of which **endpoint**.

A simple way to view that info is through the HA's Device info page:

<img width="531" height="604" alt="image" src="https://github.com/user-attachments/assets/6393b9cb-46ed-4cca-9188-df86776cf601" />

Then, in the `Clusters` tab, you can click through every cluster's attributes. To view any attribute's value, just press the accent `Read attribute` button.


<img width="542" height="578" alt="image" src="https://github.com/user-attachments/assets/2dcee89f-c9d5-445a-953b-ff8ffc902e14" />

In this example, the device is an air quality monitor capable of measuring VOCs in the air and reporting it as an index (an integer in [1, 500]). This value is accessible through endpoint `3`, cluster `0x000c` (`AnalogInput`), attribute `0x0055` (`present_value`).

If you can find all the values you are interested in via this process, you're in luck and can jump straight to section 2. But chances are, you can't find _everything_ this way. If it is the case, you will need to do the following:
1. Install and activate the [ZHA Toolkit](https://github.com/mdeweerd/zha-toolkit) integration (just follow the README instructions).
2. Go to Developer tools -> Actions. You'll be using the [scan_device](https://github.com/mdeweerd/zha-toolkit?tab=readme-ov-file#scan_device-scan-a-deviceread-all-attribute-values) service call of the integration. Be sure to read what it does!
Your action yaml should be looking like this:
```yaml
service: zha_toolkit.scan_device
data:
  ieee: 00:12:4b:00:2c:85:6f:56 # Find the IEEE of your device on the Device info page.
  event_success: scan_device_success # The name of a success event.
  event_fail: scan_device_failure # The name of a failure event.
```
3. Perform the action and wait for a response. This may take some time, so be patient. We'll be assuming the happy path here, so if this action fails for you, consult the integration's readme.
4. In the response, we're interested in the `scan` object, as it contains everything ZHA Toolkit was able to find about the device. It has the following structure:
<details>
<summary>A shortened version of the scan object</summary>

```yaml
scan:
  ieee: your ieee
  nwk: your nwk
  model: your model name
  manufacturer: your manufacturer name
  manufacturer_id: "0x0"
  endpoints:
    - id: 4
    # ...
    - id: 3
      device_type: "0x000c"
      profile: "0x0104"
      in_clusters:
        "0x000c":
          cluster_id: "0x000c"
          title: AnalogInput
          name: analog_input
          attributes:
            "0x0055":
              attribute_id: "0x0055"
              attribute_name: present_value
              value_type:
                - "0x39"
                - Single
                - Analog
              access: READ|REPORT
              access_acl: 5
              attribute_value: 100
            "0x0221":
              attribute_id: "0x0221"
              attribute_name: "545"
              value_type:
                - "0x21"
                - uint16_t
                - Analog
              access: READ|WRITE
              access_acl: 3
              attribute_value: 500
            "0x0222":
              attribute_id: "0x0222"
              attribute_name: "546"
              value_type:
                - "0x21"
                - uint16_t
                - Analog
              access: READ|WRITE
              access_acl: 3
              attribute_value: 0
            "0x0225":
              attribute_id: "0x0225"
              attribute_name: "549"
              value_type:
                - "0x10"
                - Bool
                - Discrete
              access: READ|WRITE
              access_acl: 3
              attribute_value: 0
      out_clusters: {}
    - id: 2
    # ...
    - id: 1
    # ...
```
</details>

Look at that! Our attribute `present_value` of the endpoint `3`, cluster `0x000c` (`analog_input`) is there, but so are other attributes we haven't seen before: `0x0221`, `0x0222` and `0x0225`. They don't have a `name`, like `present_value` does, their name is just a decimal representation of their ID, and they won't show up in the "Manage Zigbee device" popup. This is the kind of attributes we'll be hunting for in our quirk.

Be sure to save this data somewhere safe, as you'll be frequently consulting it when developing the quirk.

At this point you need to assign meaning to the attributes, noting the ones you want and discarding the ones you don't want. If you do not have any documentation on the device, try to find a zigbee-herdsman converter for it (it's basically the same as a quirk, but for the Zigbee2MQTT integration). It looks something like [this](https://github.com/smartboxchannel/EFEKTA-AQ-Smart-Monitor-Gen2/blob/main/z2m_converter/AQSM_G2.js). From it you can probably collect some relevant semantics for the attributes and assigning meaning will become a lot simpler.

Otherwise, you are on your own, and you are now a reverse engineer. Try doing something to the device, seeing which attributes change and deducing their meaning based on the change.

## 2. Enabling quirks.
1. Go to your instance's `configuration.yaml` file and add the following configuration:
```yaml
zha:
    enable_quirks: true
    custom_quirks_path: your/quirks/dir/
```
Where `your/quirks/dir/` is the path to the directory where you'll be placing your quirks. If this string doesn't start with a slash, the path is relative to the directory the `configuration.yaml` file is contained in. Create the directory if necessary.

## 3. Writing a quirk.
We'll be using the Quirks V2 API, as it is far more user-friendly and powerful. In your quirks directory, create a Python file (`.py` extension) with a descriptive name, e.g. `<manufacturer>_<device>_quirk.py`.

The quirks V2 API starts with the call to a `QuirksBuilder` constructor, and ends with a call to its method `add_to_registry()`:
```python
from zigpy.quirks.v2 import QuirkBuilder
(
    QuirkBuilder("your manufacturer name", "your device name")
    # interesting stuff in between
    .add_to_registry()
)
```
Pay special attention to the arguments of the constructor (manufacturer name, device name), as the device will be matched against that to decide whether to apply the quirk or not. Also notice the import at the beginning of a file - you can't use something without importing it first. Here, the `QuirkBuilder` is imported from [this file](https://github.com/zigpy/zigpy/blob/dev/zigpy/quirks/v2/__init__.py#L578). See examples of other quirks, or use the "search in repository" function if unsure where you need to import something from.

### 3.1. Exposing a supported attribute.
Now, for already available attributes (the ones with non-numerical names) the process of exposing them to ZHA is relatively simple:
```python
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass
)
from zigpy.zcl.clusters.general import AnalogInput
(
    QuirkBuilder("your manufacturer name", "your device name")
    .sensor(
        attribute_name="present_value",
        cluster_id=AnalogInput.cluster_id, # 0x000c works too
        endpoint_id=3,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.AQI,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=120, reportable_change=1
        ),
        translation_key="voc_index",
        fallback_name="VOC index",
    )
    .add_to_registry()
)
```
Here's what we've done:

- The first three arguments of the `sensor()` function (`attribute_name`, `cluster_id` and `endpoint_id`) combined tell Zigpy _where_ to look for the value,
- `state_class` and `device_class` communicate _what_ the value is to Home Assistant, affecting how the entity looks,
- `reporting_config` is an object with the following arguments:
  - `reportable_change` - the minimum number the attibute's value has to change by (delta) to be reported before `max_interval`,
  - `min_interval` - the minimum amount of time in seconds between reports of the attribute. It will not be reported more often that that, even if the value's delta is greater than `reportable_change`,
  - `max_interval` - the maximum amount of time in seconds between reports of the attribute. It will not be reported less often that that, even if the value's delta does not exceed `reportable_change`. 
- `translation_key` is the key which HA will try to find in its translations to localize the name, 
- `fallback_name` is the name used if `translation_key` is not found.

Explore [zigpy/quirks/v2](https://github.com/zigpy/zigpy/tree/dev/zigpy/quirks/v2) to see what else is possible. Here are some other functions available right now:

| Name                  | Description                                                                                                     | Example                                                                                                                            |
|-----------------------|-----------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `enum()`              | This method allows exposing an enum based entity in Home Assistant, a.k.a. the `select` entity.                 | <img width="586" height="146" alt="image" src="https://github.com/user-attachments/assets/6385a101-8696-45a0-8ea5-ca0a314b0803" /> |
| `sensor()`            | This method allows exposing a sensor entity in Home Assistant.                                                  | <img width="575" height="177" alt="image" src="https://github.com/user-attachments/assets/71d2abea-9ed5-4c85-b912-3178e407c40f" /> |
| `switch()`            | This method allows exposing a switch entity in Home Assistant.                                                  | <img width="582" height="101" alt="image" src="https://github.com/user-attachments/assets/e09c67eb-beba-429f-a87d-0d382e272dc0" /> |
| `number()`            | This method allows exposing a number entity in Home Assistant.                                                  | <img width="575" height="209" alt="image" src="https://github.com/user-attachments/assets/d0d1c536-cb58-4b97-ba9f-75c1f3b7c84e" /> |
| `binary_sensor()`     | This method allows exposing a binary sensor entity in Home Assistant.                                           | <img width="594" height="107" alt="image" src="https://github.com/user-attachments/assets/3b2c584b-cea4-4363-83aa-9a2a3e3abbd7" /> |
| `write_attr_button()` | This method allows exposing a button entity in Home Assistant that writes a value to an attribute when pressed. | <img width="562" height="93" alt="image" src="https://github.com/user-attachments/assets/27c3c4cb-b8c2-45c9-8b7b-44791dae006f" />  |
| `command_button()`    | This method allows exposing a button entity in Home Assistant that execute a ZCL command when pressed.          | <img width="573" height="104" alt="image" src="https://github.com/user-attachments/assets/9e72611f-d03b-4f83-b30a-d123c55d2215" /> |

Those entities don't necessarily have to look the way the examples do, since Home Assistant can change the UI depending on `state_class` and `device_class`, `entity_type`, `unit` and `mode` (in case of `number`).

To apply the quirk, save the file, restart your Home Assistant instance and pay close attention to the `home-assistant.log` file (same directory as `configuration.yaml`), as syntax errors in the code of your quirk will be reported there.

If you've done everything right, your device will now expose a new sensor entity (VOC index):

<img width="329" height="471" alt="image" src="https://github.com/user-attachments/assets/e68a40e9-c57e-43ca-af91-da91890b0465" />

### 3.2. Exposing an unsupported attribute.
The device we're working on has a read-write attribute in the Carbon Dioxide (CO₂) Concentration (`0x040d`) cluster under the endpoint `2` with ID `0x0205`, which tells the device the current altitude above sea level in meters for more accurate CO₂ measurements. This attribute being writeable means that it is a _configuration attribute_. 

Sadly, we cannot use its name directly (as it doesn't _have_ one) - we need to give it a name, and for that we need to _replace_ this device's CO₂ cluster with a virtual one we will write. This virtual cluster will find the attribute by its ID (`0x0205`), define its type and access level (all present in the `scan_device` result), and finally give it a name. 

But there's a slight complication in this plan: we already have supported attributes in the Carbon Dioxide (CO₂) Concentration (`0x040d`) cluster, and replacing it with one attribute defined will make already supported attributes unsupported. Do we need to re-define them just for one more attribute? Fortunately, no. 

If we navigate to the [zigpy/zcl/clusters](https://github.com/zigpy/zigpy/tree/dev/zigpy/zcl/clusters) directory of the zigpy repository, we'll find a [measurement.py](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/measurement.py) file with a [CarbonDioxideConcentration](https://github.com/zigpy/zigpy/blob/dev/zigpy/zcl/clusters/measurement.py#L361) class within. Instead of creating a brand new cluster and having to re-define all its attributes, we want to **extend** an existing cluster, appending a new attribute to it instead. Note that this class's `cluster_id` (`0x040D`) corresponds exactly with our CO₂ cluster:
```python
class CarbonDioxideConcentration(_ConcentrationMixin, Cluster):
    cluster_id: Final[t.uint16_t] = 0x040D
    name: Final = "Carbon Dioxide (CO₂) Concentration"
    ep_attribute: Final = "carbon_dioxide_concentration"
```
Also note that this class does not define any attributes by itself, but **extends** another class - `_ConcentrationMixin`, which defines the attributes:
```python
class _ConcentrationMixin:
    """Mixin for the common attributes of the concentration measurement clusters"""

    class AttributeDefs(BaseAttributeDefs):
        measured_value: Final = ZCLAttributeDef(
            id=0x0000, type=t.Single, access="rp", mandatory=True
        )  # fraction of 1 (one)
        min_measured_value: Final = ZCLAttributeDef(
            id=0x0001, type=t.Single, access="r", mandatory=True
        )
        max_measured_value: Final = ZCLAttributeDef(
            id=0x0002, type=t.Single, access="r", mandatory=True
        )
        tolerance: Final = ZCLAttributeDef(id=0x0003, type=t.Single, access="r")
        cluster_revision: Final = foundation.ZCL_CLUSTER_REVISION_ATTR
        reporting_status: Final = foundation.ZCL_REPORTING_STATUS_ATTR

```
That's because a lot of other classes representing concentration clusters (`CarbonMonoxideConcentration`, `EthyleneConcentration` and so on) have exactly the same set of attributes.

So, our custom cluster will look like this:
```python
from typing import Final
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration
from zigpy.zcl.foundation import ZCLAttributeDef

class CO2Cluster(CarbonDioxideConcentration, CustomCluster): # Extends CarbonDioxideConcentration and CustomCluster

    class AttributeDefs(CarbonDioxideConcentration.AttributeDefs): # Extends CarbonDioxideConcentration's attribute definitions
        altitude: Final = ZCLAttributeDef(id=0x0205, type=t.uint16_t, access="rw")
```

The `ZCLAttributeDef`'s `id` argument is the ID of an attribute from the scan response, as is the `type`, as is the `access` (`r` stands for `READ`, `w` stands for `WRITE` and `p` stands for `REPORT`).

So, after creating this cluster's class and replacing it, our quirk would look like this:
```python
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    NumberDeviceClass,
)
from zigpy.zcl.clusters.general import AnalogInput

from typing import Final
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.measurement import CarbonDioxideConcentration
from zigpy.zcl.foundation import ZCLAttributeDef

from zigpy.quirks.v2.homeassistant import UnitOfLength

class CO2Cluster(CarbonDioxideConcentration, CustomCluster):

    class AttributeDefs(CarbonDioxideConcentration.AttributeDefs):
        altitude: Final = ZCLAttributeDef(id=0x0205, type=t.uint16_t, access="rw")

(
    QuirkBuilder("your manufacturer name", "your device name")
    .replaces(CO2Cluster, endpoint_id=2)
    .sensor(
        attribute_name="present_value",
        cluster_id=AnalogInput.cluster_id,
        endpoint_id=3,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.AQI,
        reporting_config=ReportingConfig(
            min_interval=10, max_interval=120, reportable_change=1
        ),
        translation_key="voc_index",
        fallback_name="VOC index",
    )
    .number( # Setting the altitude above sea level (for high accuracy of the CO2 sensor)
        attribute_name=CO2Cluster.AttributeDefs.altitude.name,
        cluster_id=CO2Cluster.cluster_id,
        endpoint_id=2,
        translation_key="whatever",
        fallback_name="Altitude above sea level",
        device_class=NumberDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=3000,
        step=1
    )
    .add_to_registry()
)
```

After successfully restarting Home Assistant, we've got a new configuration entity:
<img width="339" height="148" alt="image" src="https://github.com/user-attachments/assets/e91dc4a3-eba7-4edc-bb37-c425a57cdbbf" />

## 4. Conclusion
You now know how to scan devices for attributes and expose them to Home Assistatnt as entities. The basics, one might say. One can do a lot more, and if one wants to, being at least a bit familiar with the API is the first step to doing that.
