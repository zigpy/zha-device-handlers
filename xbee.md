## Digital GPIO

Digital input/output pins are exposed as switches.

To use this functionality must configure the xbee to send samples to the coordinator, `DH` and `DL` to the coordiator's address (0).
The switch state will change depending on the state.

There are two options of reporting the pin state: periodic sampling (`IR`) and on state change (`IC`).
To configure reporting on state change please set the appropriate bit mask on `IC`, and to send perodic reports every x milliseconds please set `IR` to a value greater than zero.
The recommended approach is to combine both methods. Please note that Home Assistant will mark a zigbee device as unavailable if it doesn't send any communication for more than two hours.

If you want the pin to work as input, it must be configured as input with XCTU.

If you want the pin to work as output, it is still important to configure the sample reporting in order to know the state of the switch.

Currently digital output requires the coordinator to be XBee as well. THe input should work with any coordinator but this is untested.

## Analog Input

The analog input pins are exposed as sensors.

You must configure periodic sampling (`IR`; please see above for more on that) and configure corresponding pins as analog inputs.

The sensors show voltage in percent relative to the analog reference voltage. 0 is 0V and 100 is the analog reference voltage or above.
The analog reference voltage is 1.2V for XBee and selectable between 1.25V, 2.5V and VDD with `AV` command for XBee3.

## Supply Voltage

The supply voltage is exposed as sensor and measured in volts.
To use the functionality, enable it with `V+` command and configure periodic sampling as above.

## PWM Output

XBee3 provides two PWM outputs. They are not currently exposed automatically, you must use `zha.set_zigbee_cluster_attribute` service.

To use the functionality, you must configure an `input_number` and an automation for each PWM pin you want to use as per the following example (replace ieee with the one of your device):
```
input_number:
  pwm0:
    name: PWM0
    min: 0
    max: 1023
  pwm1:
    name: PWM1
    min: 0
    max: 1023
automation:
  - id: '1574205383149'
    alias: XBee PWM0
    description: 'Update cluster attribute on slider change for PWM0'
    trigger:
    - entity_id: input_number.pwm0
      platform: state
    action:
    - service: zha.set_zigbee_cluster_attribute
      data_template:
        ieee: 00:13:a2:00:41:a0:7e:1a
        endpoint_id: 218
        cluster_id: 13
        cluster_type: in
        attribute: 85
        value: '{{ trigger.to_state.state }}'
  - id: '1574205383150'
    alias: XBee PWM1
    description: 'Update cluster attribute on slider change for PWM1'
    trigger:
    - entity_id: input_number.pwm1
      platform: state
    action:
    - service: zha.set_zigbee_cluster_attribute
      data_template:
        ieee: 00:13:a2:00:41:a0:7e:1a
        endpoint_id: 219
        cluster_id: 13
        cluster_type: in
        attribute: 85
        value: '{{ trigger.to_state.state }}'
```
Currently PWM output requires the coordinator to be XBee as well.

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
        args: Home
    action:
      service: zha.issue_zigbee_cluster_command
      data:
        ieee: 00:13:a2:00:12:34:56:78
        endpoint_id: 232
        cluster_id: 17
        cluster_type: in
        command: 0
        command_type: server
        args: Assistant
```
