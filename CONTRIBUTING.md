# Primer

If you are reading this you must have a device that isn't working 100% as expected. This can be the case for a number of reasons but what we will cover in this guide is the case where functionality is provided by a device in a non spececification compliant maner by a device manufacturer.

## What are these specifications?

[Zigbee Specification](https://zigbeealliance.org/wp-content/uploads/2019/11/docs-05-3474-21-0csg-zigbee-specification.pdf)

[Zigbee Cluster Library](https://zigbeealliance.org/wp-content/uploads/2019/12/07-5123-06-zigbee-cluster-library-specification.pdf)

[Zigbee Base Device Specification](https://zigbeealliance.org/wp-content/uploads/zip/zigbee-base-device-behavior-bdb-v1-0.zip)

[Zigbee Primer](https://docs.smartthings.com/en/latest/device-type-developers-guide/zigbee-primer.html)

## What is a device in human terms?

A device is a physiclal object that you want to join to a Zigbee network: a light bulb, a switch, a sensor etc. The host application, in this case Zigpy, needs to understand how to interact with the device so there are standards that define how the application and devices can communicate. To accomplish that the device and its associated functionality is described by several descriptors that the Zigbee application can use to understand the device and the functionality that it provides. For the purposes of Zigpy and Quirks we will focus on two of them:

- Node Descriptor: desc goes here
- Simple Descriptor: desc goes here

## What is a Node Descriptor and why do we care?

## What is a Simple Descriptor and why do we care?

A simple descriptor is a description of a Zigbee device endpoint. <describe endpoints> <describe clusters>
`<SimpleDescriptor endpoint=1 profile=260 device_type=1026 device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280, 2821] output_clusters=[25]>`

## Parts of a device

Devices contain endpoints and endpoints contain clusters. <add more to this>

## OK, now what?

Now that we got that out of the way we can focus on the task at hand: make our devices work the way they should with Zigpy and ZHA. Because the device doesn't work correctly out of the box we have to write a quirk for it.

## What the heck is a quirk?

In human terms you can think of a quirk like google translate. I know it's a weird comparison but lets dig in a bit. You may only speak one language but there is an interesting article written in another language that you really want to read. Google translate takes the original article and displays it in a format (language) that you understand. A quirk is a file that translates device functionality from the format that the manufacturer chose to implement it in to a format that Zigpy and in turn ZHA understand. The main purpose of a quirk is to serve as a translator. A quirk is comprised of several parts:

- signature
- replacement
- device_automation_triggers

## signature

The signature on a quirk identifies the device as the manufacturer implemented it. You can think of it as a fingerprint or the dna of the device. The signature is what we use to identify the device. If any part of the signature doesn't match what the device returns during discovery the quirk will not match and as a result it will not be applied.

## replacement

The replacement on a quirk is what we want the device to be. Remember, we said that quirks were like Google translate... you can think of the replacement like the output from Google translate. The replacement dict is what will actually be used by Zigpy and ZHA to interact with the device.

## device_automation_triggers

Device automation triggers are essentially representations of the events that the devices fire in HA. They allow users to use actions in the UI instead of using the raw events.

# Great, all of the definitions are out of the way. Let's break down an example!

# Initial Contribution Guidelines - WIP

- All code is formatted with black. The check format script that runs in CI will ensure that code meets this requirement and that it is correctly formatted with black. Instructions for installing black in many editors can be found here: <https://github.com/psf/black#editor-integration>

- Capture the SimpleDescriptor log entries for each endpoint on the device. These can be found in the HA logs after joining a device and they look like this: `<SimpleDescriptor endpoint=1 profile=260 device_type=1026 device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280, 2821] output_clusters=[25]>`. This information can also be obtained from the zigbee.db if you want to take the time to query the tables and reconstitute the log entry. I find it easier to just remove and rejoin the device. ZHA entity ids are stable for the most part so it _shouldn't_ disrupt anything you have configured. These need to match what the device reports EXACTLY or zigpy will not match them when a device joins and the handler will not be used for the device.

- Create a device class extending CustomDevice or a derivitave of it

- All custom cluster definitions must extend CustomCluster

- Use an existing handler as a guide. signature and replacement dicts are required. Include the SimpleDescriptor entry for each endpoint in the signature dict above the definition of the endpoint in this format:

  ```yaml
  #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
  #  device_version=0
  #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
  #  output_clusters=[25]>
  ```

- Use constants for all attribute values referencing the appropriate labels from Zigpy / HA as necessary

- how `device_automation_triggers` work:

  Device automation triggers are essentially representations of the events that the devices fire in HA. They allow users to use actions in the UI instead of using the raw events. Ex: For the Hue remote - the on button fires this event:

  `<Event zha_event[L]: unique_id=00:17:88:01:04:e7:f9:37:1:0x0006, device_ieee=00:17:88:01:04:e7:f9:37, endpoint_id=1, cluster_id=6, command=on, args=[]>`

  and the action defined for this is:

  `(SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON}`

  The first part `(SHORT_PRESS, TURN_ON)` corresponds to the txt the user will see in the UI:

    <img width="620" alt="image" src="https://user-images.githubusercontent.com/1335687/73609115-76480b80-4598-11ea-97eb-8d8343e2355b.png">

  The second part is the event data. You only need to supply enough of the event data to uniquely match the event which in this case is just the command for this event fired by this device: `{COMMAND: COMMAND_ON}`

  If you look at another example for the same device:

  `(SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_STEP, CLUSTER_ID: 8, ENDPOINT_ID: 1, ARGS: [0, 30, 9],}`

  you can see a pattern that illustrates how to match a more complex event. In this case the step command is used for the dim up and dim down buttons so we need to match more of the event data to uniquely match the event.
