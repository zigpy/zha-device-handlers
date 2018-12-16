## Initial Contribution Guidelines - WIP

- Capture the SimpleDescriptor log entries for each endpoint on the device. These can be found in the HA logs after joining a device and they look like this: `<SimpleDescriptor endpoint=1 profile=260 device_type=1026 device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280, 2821] output_clusters=[25]>`. This information can also be obtained from the zigbee.db if you want to take the time to query the tables and reconstitute the log entry. I find it easier to just remove and rejoin the device. ZHA entity ids are stable for the most part so it *shouldn't* disrupt anything you have configured. These need to match what the device reports EXACTLY or zigpy will not match them when a device joins and the handler will not be used for the device.

- Create a device class extending CustomDevice or a derivitave of it

- Use an existing handler as a guide. signature and replacement dicts are required. Include the SimpleDescriptor entry for each endpoint in the signature dict above the definition of the endpoint in this format: 

    ```yaml

    #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
    #  device_version=0
    #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
    #  output_clusters=[25]>

    ```

- manufacturer and model are required on EVERY replacement endpoint definition and they NEED to match what the device reports to HA.

- Use constants for all attribute values referencing the appropriate labels from Zigpy / HA as necessary