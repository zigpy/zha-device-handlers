This document describes how to use Digi XBee device as a router or end device.

## Using with non-XBee coordinator

You may need to configure zigpy to listen to the appropriate additional endpoints which it ignores by default. This is an example config for HA ZHA:

```
zha:
  zigpy_config:
    additional_endpoints:
      - endpoint: 0xE6
        profile: 0xC105
        device_type: 0x0000
        device_version: 0b0000
        input_clusters: [0xA1]
        output_clusters: [0x21]
      - endpoint: 0xE8
        profile: 0xC105
        device_type: 0x0000
        device_version: 0b0000
        input_clusters: [0x11, 0x92]
        output_clusters: [0x11]
```

## Digital GPIO

Digital input/output pins are exposed as switches.

To use this functionality must configure the xbee to send samples to the coordinator, `DH` and `DL` to the coordiator's address (0).
The switch state will change depending on the state.

There are two options of reporting the pin state: periodic sampling (`IR`) and on state change (`IC`).
To configure reporting on state change please set the appropriate bit mask on `IC`, and to send perodic reports every x milliseconds please set `IR` to a value greater than zero.
The recommended approach is to combine both methods. Please note that Home Assistant will mark a zigbee device as unavailable if it doesn't send any communication for more than two hours.

If you want the pin to work as input, it must be configured as input with XCTU.

If you want the pin to work as output, it is still important to configure the sample reporting in order to know the state of the switch.

## Analog Input

The analog input pins are exposed as sensors.

You must configure periodic sampling (`IR`; please see above for more on that) and configure corresponding pins as analog inputs.

The sensors show voltage in percent relative to the analog reference voltage. 0 is 0V and 100 is the analog reference voltage or above.
The analog reference voltage is 1.2V for XBee and selectable between 1.25V, 2.5V and VDD with `AV` command for XBee3.

## Supply Voltage

The supply voltage is exposed as sensor and measured in volts.
To use the functionality, enable it with `V+` command and configure periodic sampling as above.

## PWM Output

XBee3 provides two PWM outputs. They are exposed as `number` entities.

## UART

Outgoing UART data can be sent with `zha.issue_zigbee_cluster_command` service.

Incoming UART data will generate `zha_event` event.

For example, the following script replies with an `Assistant` string to the device once it receives a `Home` string from it (replace ieee with your actual endpoint device ieee):
```
automation:
  - alias: XBee UART Test
    trigger:
      platform: event
      event_type: zha_event
      event_data:
        device_ieee: 00:13:a2:00:12:34:56:78
        command: receive_data
        args:
          data: Home
    action:
      service: zha.issue_zigbee_cluster_command
      data:
        ieee: 00:13:a2:00:12:34:56:78
        endpoint_id: 232
        cluster_id: 17
        cluster_type: in
        command: 0
        command_type: server
        params:
          data: Assistant
```

## Remote AT Commands

Like with UART, you can send remote AT commands with `zha.issue_zigbee_cluster_command` service.
If the command is unsuccessful, you will get an exception in the logs. If it is successful, the response will be available as `zha_event` event.

You can check the AT-to-Command_ID mapping in Device info screen. Click on `Manage clusters`, then select XBeeRemoteATRequest cluster, and you would find the mapping in the `Cluster Commands` dropdown list.

Here is an example for the temperature sensor of an XBee Pro, you can get its value with TP command:
```
template:
  - trigger:
    - platform: event
      event_type: zha_event
      event_data:
        device_ieee: 00:13:a2:00:41:98:23:f9
        command: tp_command_response
    sensor:
      - name: "XBee Temperature"
        state: '{{ trigger.event.data.args.response }}'
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement

automation:
  - alias: Update XBee Temperature
    trigger:
      platform: time_pattern
      minutes: "/5"
    action:
      service: zha.issue_zigbee_cluster_command
      data:
        ieee: 00:13:a2:00:41:98:23:f9
        endpoint_id: 230
        command: 0x43
        command_type: server
        cluster_type: out
        cluster_id: 33
        params: {}
```
