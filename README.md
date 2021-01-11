# ZHA Device Handlers For Home Assistant

![CI](https://github.com/zigpy/zha-device-handlers/workflows/CI/badge.svg?branch=dev)
[![Coverage Status](https://coveralls.io/repos/github/zigpy/zha-device-handlers/badge.svg)](https://coveralls.io/github/zigpy/zha-device-handlers)

ZHA Device Handlers are custom quirks implementations for [Zigpy](https://github.com/zigpy/zigpy), the library that provides the [Zigbee](http://www.zigbee.org) support for the [ZHA](https://www.home-assistant.io/components/zha/) component in [Home Assistant](https://www.home-assistant.io).

ZHA device handlers bridge the functionality gap created when manufacturers deviate from the ZCL specification, handling deviations and exceptions by parsing custom messages to and from Zigbee devices. Zigbee devices that deviate from or do not fully conform to the standard specifications set by the Zigbee Alliance may require the development of custom ZHA Device Handlers (ZHA custom quirks handler implementation) to for all their functions to work properly with the ZHA component in Home Assistant.

Custom quirks implementations for zigpy implemented as ZHA Device Handlers are a similar concept to that of [Hub-connected Device Handlers for the SmartThings Classics platform](https://docs.smartthings.com/en/latest/device-type-developers-guide/) as well that of [Zigbee-Herdsman Converters / Zigbee-Shepherd Converters as used by Zigbee2mqtt](https://www.zigbee2mqtt.io/how_tos/how_to_support_new_devices.html), meaning they are virtual representation of a physical device that expose additional functionality that is not provided out-of-the-box by the existing integration between these platforms. See [Device Specifics](#Device-Specifics) for details.

# How to contribute

## Primer

ZHA device handlers and it's provided Quirks allow Zigpy, ZHA and Home Assistant to work with non standard Zigbee devices. If you are reading this you may have a device that isn't working as expected. This can be the case for a number of reasons but in this guide we will cover the cases where functionality is provided by a device in a non specification compliant manner by the device manufacturer.

## What are these specifications

[Zigbee Specification](https://zigbeealliance.org/wp-content/uploads/2019/11/docs-05-3474-21-0csg-zigbee-specification.pdf)

[Zigbee Cluster Library](https://zigbeealliance.org/wp-content/uploads/2019/12/07-5123-06-zigbee-cluster-library-specification.pdf)

[Zigbee Base Device Specification](https://zigbeealliance.org/wp-content/uploads/zip/zigbee-base-device-behavior-bdb-v1-0.zip)

[Zigbee Primer](https://docs.smartthings.com/en/latest/device-type-developers-guide/zigbee-primer.html)

## What is a device in human terms

A device is a physical object that you want to join to a Zigbee network: a light bulb, a switch, a sensor etc. The host application, in this case Zigpy, needs to understand how to interact with the device so there are standards that define how the application and devices can communicate. The device's functionality is described by several **descriptors** while the device itself contains **endpoints** and **endpoints** contain **clusters**. There are two types of clusters an endpoint contains:

- **in_clusters** - are "Server" clusters in ZCL terms. These clusters control the device, e.g. a smart plug or light bulb would have an `on_off` server cluster. **in_clusters** are also the ones which also send attribute reports and/or you can read an attribute from a **in_cluster**.
- **out_clusters** - are "Client" clusters. These clusters control some other device, as "Client" cluster sends commands to "Server" cluster. For example an On/Off remote would have an `on_off` client cluster and will generate cluster commands and send those to some other device.
  Zigpy needs to understand all these elements in order to correctly work with the device.

### Endpoints

Endpoints are essentially groupings of functionality. For example, a typical Zigbee light bulb will have a single endpoint for the light. A multi-gang wall switch may have an endpoint for each individual switch so they can all be controlled separately. Each endpoint has several functions represented by clusters.

### Clusters

Clusters are objects that contain the information (attributes and commands) for individual functions. There is the ability to turn the switch on and off, maybe there is energy monitoring, maybe there is the ability to add each switch to an individual group or a scene, etc. Each of these functions belong to a cluster.

### Descriptors

For the purposes of Zigpy and Quirks we will focus on two descriptors: **Node Descriptor** and **Simple Descriptor**.

#### Node Descriptor

A node descriptor explains some basic device attributes to Zigpy. The manufacturer code and the power type are the ones that we generally care about. In most cases you won't have to worry about this but it is good to know why it is there in case you come across it while looking at an existing quirk. Here is an example:
`<Optional byte1=2 byte2=64 mac_capability_flags=128 manufacturer_code=4174 maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=0 maximum_outgoing_transfer_size=82 descriptor_capability_field=0>`

#### Simple Descriptor

A simple descriptor is a description of a Zigbee device endpoint and is responsible for explaining the endpoint's functionality. It contains a profile id, the device type, and collections of clusters. The profile id tells the application what set of Zigbee rules to use. The most common profile will be 260 (0x0104) for the Home Automation profile. The device type tells the application what logical type of device this is ex: on off light, color light, etc. The clusters explain to the application what types of functionality exist on the endpoint. Here is an example:
`<SimpleDescriptor endpoint=1 profile=260 device_type=1026 device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280, 2821] output_clusters=[25]>`

## What the heck is a quirk

In human terms you can think of a quirk like google translate. I know it's a weird comparison but lets dig in a bit. You may only speak one language but there is an interesting article written in another language that you really want to read. Google translate takes the original article and displays it in a format (language) that you understand. A quirk is a file that translates device functionality from the format that the manufacturer chose to implement it in to a format that Zigpy and in turn ZHA understand. The main purpose of a quirk is to serve as a translator. A quirk is comprised of several parts:

- Signature - To identify and apply the correct quirk
- Replacement - To allow Zigpy and ZHA to correctly work with the device
- device_automation_triggers - To let the Home Assistant Device Automation engine and users interact with the device

### Signature

The signature on a quirk identifies the device as the manufacturer implemented it. You can think of it as a fingerprint or the dna of the device. The signature is what we use to identify the device. If any part of the signature doesn't match what the device returns during discovery the quirk will not match and as a result it will not be applied. The signature is made up of several parts:

- `models_info`
- `endpoints`

Models info tells the application which devices should use this particular quirk. Endpoints are the simple descriptors that we spoke about earlier exactly as they are on the device. `endpoints` is a dict where the key is the id of the endpoint and the value is an object with the following properties: `profile_id`, `device_type`, `input_clusters` and `output_clusters`. Creating the signature element is generally just a job of transcribing what the device gives us. Here is an example:

```python
signature = {
    MODELS_INFO: [(LUMI, "lumi.plug.maus01")],
    ENDPOINTS: {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81
        # device_version=1
        # input_clusters=[0, 4, 3, 6, 16, 5, 10, 1, 2, 2820]
        # output_clusters=[25, 10]>
        1: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
            INPUT_CLUSTERS: [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                DeviceTemperature.cluster_id,
                Groups.cluster_id,
                Identify.cluster_id,
                OnOff.cluster_id,
                Scenes.cluster_id,
                BinaryOutput.cluster_id,
                Time.cluster_id,
                ElectricalMeasurement.cluster_id,
            ],
            OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
        },
    },
}
```

### Replacement

The replacement on a quirk is what we want the device to be. Remember, we said that quirks were like Google translate... you can think of the replacement like the output from Google translate. The replacement dict is what will actually be used by Zigpy and ZHA to interact with the device. The structure of `replacement` is the same as signature with 2 key differences: `models_info` is generally omitted and there is an extra element `skip_configuration` that instructs the application to skip configuration if necessary. Some manufacturers have not implemented the specifications correctly and the devices come pre-configured and therefore the configuration calls fail (non Zigbee 3.0 Xiaomi devices for instance). Usually, you should not add `skip_configuration`.

Here is an example:

```python
replacement = {
    SKIP_CONFIGURATION: True,
    ENDPOINTS: {
        1: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
            INPUT_CLUSTERS: [
                BasicCluster,
                PowerConfiguration.cluster_id,
                DeviceTemperature.cluster_id,
                Groups.cluster_id,
                Identify.cluster_id,
                OnOff.cluster_id,
                Scenes.cluster_id,
                BinaryOutput.cluster_id,
                Time.cluster_id,
                ElectricalMeasurementCluster,
            ],
            OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
        },
    },
}
```

### device_automation_triggers

Device automation triggers are essentially representations of the events that the devices fire in HA. They allow users to use actions in the UI instead of using the raw events.

# Building a quirk

Now that we got that out of the way we can focus on the task at hand: make our devices work the way they should with Zigpy and ZHA. Because the device doesn't work correctly out of the box we have to write a quirk for it. First lets look at what the quirk looks like when complete:

```python
class Plug(XiaomiCustomDevice):
    """lumi.plug.maus01 plug."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voltage_bus = Bus()
        self.consumption_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.plug.maus01")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 4, 3, 6, 16, 5, 10, 1, 2, 2820]
            # output_clusters=[25, 10]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    BinaryOutput.cluster_id,
                    Time.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=9
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[12, 4]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id, Groups.cluster_id],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=83
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[12]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            # <SimpleDescriptor endpoint=100 profile=260 device_type=263
            # device_version=2
            # input_clusters=[15]
            # output_clusters=[15, 4]>
            100: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [BinaryInput.cluster_id],
                OUTPUT_CLUSTERS: [BinaryInput.cluster_id, Groups.cluster_id],
            },
        },
    }
    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    BinaryOutput.cluster_id,
                    Time.cluster_id,
                    ElectricalMeasurementCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id, Groups.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            100: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [BinaryInput.cluster_id],
                OUTPUT_CLUSTERS: [BinaryInput.cluster_id, Groups.cluster_id],
            },
        },
    }
```

This quirk is for the US version of the Xiaomi plug. Xiaomi is notorious for not following the Zigbee specifications and most of their non Zigbee 3.0 devices need a quirk to function correctly. In this case we are correcting the `ElectricalMeasurement` cluster readings. Xiaomi decided to report the values for this cluster on the `AnalogInput` cluster instead. To fix this we will create a custom cluster to replace the `AnalogInput` and `ElectricalMeasurement` clusters. We will take the values that are reported on the `AnalogInput` cluster and publish them to the `ElectricalMeasurement` cluster. Doing this allows the device to work as if Xiaomi had implemented this in the first place. This is the act of translating that was mentioned in the Google Translate analogy above.

First things first. All device definitions in quirks must extend `CustomDevice` or a derivative of it and all clusters that you define must extend `CustomCluster` or a derivative of it. If you want to send messages between `CustomCluster` definitions as we do here you need to create channels for the communication to flow through. We do this by adding instances of `Bus` on our `CustomDevice` implementation. `Bus` is a utility class used specifically for this purpose and adding it to the device implementation ensures that all clusters that you define will have access to the `Bus` so that they can communicate with each other.

```python
class Plug(XiaomiCustomDevice):
    """lumi.plug.maus01 plug."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voltage_bus = Bus()
        self.consumption_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)
```

You can see that we have extended `XiaomiCustomDevice` which is a derivative of `CustomDevice` shared by Xiaomi devices. You can also see that we have added some instances of `Bus` so that we can pass messages between `CustomCluster` definitions. To be clear, this is not always necessary. Quirks can be used to change formats of data on an existing cluster, to add manufacturer specific attributes or commands to clusters etc. In these instances you just need to create a derivative of `CustomCluster` and add your logic. This is more of an advanced example to illustrate what is possible.

Here are the custom cluster definitions:

```python
class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster, only used to relay power consumption information to ElectricalMeasurementCluster."""

    cluster_id = AnalogInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if value is not None and value >= 0:
            self.endpoint.device.power_bus.listener_event(POWER_REPORTED, value)


class ElectricalMeasurementCluster(LocalDataCluster, ElectricalMeasurement):
    """Electrical measurement cluster to receive reports that are sent to the basic cluster."""

    cluster_id = ElectricalMeasurement.cluster_id
    POWER_ID = 0x050B
    VOLTAGE_ID = 0x0500
    CONSUMPTION_ID = 0x0304

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.voltage_bus.add_listener(self)
        self.endpoint.device.consumption_bus.add_listener(self)
        self.endpoint.device.power_bus.add_listener(self)

    def power_reported(self, value):
        """Power reported."""
        self._update_attribute(self.POWER_ID, value)

    def voltage_reported(self, value):
        """Voltage reported."""
        self._update_attribute(self.VOLTAGE_ID, value)

    def consumption_reported(self, value):
        """Consumption reported."""
        self._update_attribute(self.CONSUMPTION_ID, value)
```

In the `AnalogInput` cluster we override the `_update_attribute` method so that we can access the data that the cluster receives when the device sends a report and we send the data via an event on a bus to the `ElectricalMeasurement` cluster. This is the line that does the heavy lifting:

`self.endpoint.device.power_bus.listener_event(POWER_REPORTED, value)`

Then in the `ElectricalMeasurement` cluster we need to subscribe to these events and handle them. This is how we subscribe to our custom events:

`self.endpoint.device.power_bus.add_listener(self)`

and this method (the method name must match the event name that you publish EXACTLY):

```python
def power_reported(self, value):
    """Power reported."""
    self._update_attribute(self.POWER_ID, value)
```

receives the event and handles updating the attribute on the correct zigbee cluster. As you can see there really isn't much here that needs to be done to accomplish our goal.

Once we have created our `CustomCluster` implementations we have to tell the `CustomDevice` implementation to use them. We do this in the `replacement` dict in the quirk definition. Start by copying the `signature` dict and remove the `models_info` from it. Then we replace the cluster ids that we want to override with the names of our `CustomCluster` implementations that we have created. The result looks like this:

```python
replacement = {
    SKIP_CONFIGURATION: True,
    ENDPOINTS: {
        1: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
            INPUT_CLUSTERS: [
                BasicCluster,
                PowerConfiguration.cluster_id,
                DeviceTemperature.cluster_id,
                Groups.cluster_id,
                Identify.cluster_id,
                OnOff.cluster_id,
                Scenes.cluster_id,
                BinaryOutput.cluster_id,
                Time.cluster_id,
                ElectricalMeasurementCluster,
            ],
            OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
        },
        2: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
            INPUT_CLUSTERS: [AnalogInputCluster],
            OUTPUT_CLUSTERS: [AnalogInput.cluster_id, Groups.cluster_id],
        },
        3: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
            INPUT_CLUSTERS: [AnalogInput.cluster_id],
            OUTPUT_CLUSTERS: [AnalogInput.cluster_id],
        },
        100: {
            PROFILE_ID: zha.PROFILE_ID,
            DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
            INPUT_CLUSTERS: [BinaryInput.cluster_id],
            OUTPUT_CLUSTERS: [BinaryInput.cluster_id, Groups.cluster_id],
        },
```

You can see that we have replaced `ElectricalMeasurement.cluster_id` from endpoint 1 in the `signature` dict with the name of our cluster that we created: `ElectricalMeasurementCluster` and on endpoint 2 we replaced `AnalogInput.cluster_id` with the implementation we created for that: `AnalogInputCluster`. This instructs Zigpy to use these `CustomCluster` derivatives instead of the normal cluster definitions for these clusters and this is why this part of the quirk is called `replacement`.

Now lets put this all together. If you examine the device definition above you will see that we have defined our custom device, we defined the `signature` dict where we transcribed the `SimpleDescriptor` output we obtained when the device joined the network and we defined the `replacement` dict where we swapped the cluster ids for the culsters that we wanted to replace with the `CustomCluster` implementations that we created.

# Contribution Guidelines

- All code is formatted with black. The check format script that runs in CI will ensure that code meets this requirement and that it is correctly formatted with black. Instructions for installing black in many editors can be found here: <https://github.com/psf/black#editor-integration>

- Capture the SimpleDescriptor log entries for each endpoint on the device. These can be found in the HA logs after joining a device and they look like this: `<SimpleDescriptor endpoint=1 profile=260 device_type=1026 device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280, 2821] output_clusters=[25]>`. This information can also be obtained from the zigbee.db if you want to take the time to query the tables and reconstitute the log entry. I find it easier to just remove and rejoin the device. ZHA entity ids are stable for the most part so it _shouldn't_ disrupt anything you have configured. These need to match what the device reports EXACTLY or zigpy will not match them when a device joins and the handler will not be used for the device. You can also obtain this information from the device screen in HA for the device. The `Zigbee Device Signature` button will launch a dialog that contains all of the information necessary to create quirks.

- All custom device definitions must extend `CustomDevice` or a derivative of it

- All custom cluster definitions must extend `CustomCluster` or a derivative of it

- Use constants for all attribute values referencing the appropriate labels from Zigpy / HA as necessary

- Use an existing handler as a guide. signature and replacement dicts are required. Include the SimpleDescriptor entry for each endpoint in the signature dict above the definition of the endpoint in this format:

  ```yaml
  #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
  #  device_version=0
  #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
  #  output_clusters=[25]>
  ```

# How `device_automation_triggers` work

Device automation triggers are essentially representations of the events that the devices fire in HA. They allow users to use actions in the UI instead of using the raw events. Ex: For the Hue remote - the on button fires this event:

`<Event zha_event[L]: unique_id=00:17:88:01:04:e7:f9:37:1:0x0006, device_ieee=00:17:88:01:04:e7:f9:37, endpoint_id=1, cluster_id=6, command=on, args=[]>`

and the action defined for this is:

`(SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON}`

The first part `(SHORT_PRESS, TURN_ON)` corresponds to the txt the user will see in the UI:

<img width="620" alt="image" src="https://user-images.githubusercontent.com/1335687/73609115-76480b80-4598-11ea-97eb-8d8343e2355b.png">

The second part is the event data. You only need to supply enough of the event data to uniquely match the event which in this case is just the command for this event fired by this device: `{COMMAND: COMMAND_ON}`

If you look at another example for the same device:

`(SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_STEP, CLUSTER_ID: 8, ENDPOINT_ID: 1, ARGS: [0, 30, 9],}`

You can see a pattern that illustrates how to match a more complex event. In this case the step command is used for the dim up and dim down buttons so we need to match more of the event data to uniquely match the event.

# Testing new releases

Testing a new release of the zha-quirks package before it is released in Home Assistant.

If you are using Supervised Home Assistant (formerly known as the Hassio/Hass.io distro):

- Add <https://github.com/home-assistant/hassio-addons-development> as "add-on" repository
- Install "Custom deps deployment" addon
- Update config like:

  ```yml
  pypi:
    - zha-quirks==0.0.38
  apk: []
  ```

  where 0.0.38 is the new version

- Start the addon

If you are instead using some custom python installation of Home Assistant then do this:

- Activate your python virtual env
- Update package with `pip`

  ```bash
  pip install zha-quirks==0.0.38
  ```

# Testing quirks in development in docker based install

If you are using Supervised Home Assistant (formerly known as the Hassio/Hass.io distro) you will need to get access to the home-assistant docker container. Directions below are given for using the portainer add-on to do this, there are other methods as well not covered here.

- Install the portainer add-on (<https://github.com/hassio-addons/addon-portainer>) from Home Assistant Community Add-ons.
- Follow the add-on documentation to un-hide the home-assistant container (<https://github.com/hassio-addons/addon-portainer/blob/master/portainer/DOCS.md>)
- Stage the update quirk in a directory within your config directory
- Use portainer to access a console in the home-assistant container:

  <img src="https://user-images.githubusercontent.com/11084412/88719260-fdfa7700-d0f0-11ea-8791-88ed3e26915d.png" width=400 >

- Access the quirks directory
  - on HA > 0.113: /usr/local/lib/python3.8/site-packages/zhaquirks/
  - on HA < 0.113: /usr/local/lib/python3.7/site-packages/zhaquirks/
- Copy updated/new quirk to zhaquirks directory: `cp -a /config/temp/NEW_QUIRK ./`
- Remove the **pycache** folder so it is regenerated `rm -rf ./__pycache__/`
- Close out the console and restart HA.
- Note: The added/update quirk will not survive a HA version update.

# Thanks

- Special thanks to damarco for the majority of the device tracker code
- Special thanks to Yoda-x for the Xioami attribute parsing code
- Special thanks to damarco and Adminiuga for allowing me to bounce ideas off of them and for listening to me ramble

# Related projects

## Zigpy

**[zigpy](https://github.com/zigpy/zigpy)** is **[Zigbee protocol stack](https://en.wikipedia.org/wiki/Zigbee)** integration project to implement the **[Zigbee Home Automation](https://www.zigbee.org/)** standard as a Python 3 library. Zigbee Home Automation integration with zigpy allows you to connect one of many off-the-shelf Zigbee adapters using one of the available Zigbee radio library modules compatible with zigpy to control Zigbee based devices. There is currently support for controlling Zigbee device types such as binary sensors (e.g., motion and door sensors), sensors (e.g., temperature sensors), lightbulbs, switches, locks, fans, covers (blinds, marquees, and more). A working implementation of zigpy exist in **[Home Assistant](https://www.home-assistant.io)** (Python based open source home automation software) as part of its **[ZHA component](https://www.home-assistant.io/components/zha/)**

## ZHA Map

[zha-map](https://github.com/zha-ng/zha-map) project allow building a Zigbee network topology map for ZHA component in Home Assistant.

## zha-network-visualization-card

[zha-network-visualization-card](https://github.com/dmulcahey/zha-network-visualization-card) is a custom Lovelace element for visualizing the Zigbee network map for ZHA component in Home Assistant.

## ZHA Network Card

[zha-network-card](https://github.com/dmulcahey/zha-network-card) is a custom Lovelace card that displays ZHA network and device information in Home Assistant

## zigpy-deconz-parser

[zigpy-deconz-parser](https://github.com/zha-ng/zigpy-deconz-parser) project can parse Home Assistant ZHA component debug log using `zigpy-deconz` library if you have ConBee or RaspBee hardware.
