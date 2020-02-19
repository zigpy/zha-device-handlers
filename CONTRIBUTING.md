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
