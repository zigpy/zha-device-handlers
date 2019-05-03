[![Build Status](https://travis-ci.org/dmulcahey/zha-device-handlers.svg?branch=master)](https://travis-ci.org/dmulcahey/zha-device-handlers)

# ZHA Device Handlers For Home Assistant

ZHA Device Handlers are custom quirks implementations for [Zigpy](https://github.com/zigpy/zigpy), the library that provides the [Zigbee](http://www.zigbee.org) support for the [ZHA](https://www.home-assistant.io/components/zha/) component in [Home Assistant](https://www.home-assistant.io). 

ZHA device handlers bridge the functionality gap created when manufacturers deviate from the ZCL specification, handling deviations and exceptions by parsing custom messages to and from Zigbee devices. Zigbee devices that deviate from or do not fully conform to the standard specifications set by the Zigbee Alliance may require the development of custom ZHA Device Handlers (ZHA custom quirks handler implementation) to for all their functions to work properly with the ZHA component in Home Assistant. 

Custom quirks implementations for zigpy implemented as ZHA Device Handlers are a similar concept to that of [Hub-connected Device Handlers for the SmartThings Classics platform](https://docs.smartthings.com/en/latest/device-type-developers-guide/) as well that of [Zigbee-Shepherd Converters as used by Zigbee2mqtt](https://www.zigbee2mqtt.io/how_tos/how_to_support_new_devices.html), meaning they are virtual representation of a physical device that expose additional functionality that is not provided out-of-the-box by the existing integration between these platforms. See [Device Specifics](#Device-Specifics) for details.

# Contributing
[guidelines](./CONTRIBUTING.md)

# Currently Supported Devices:

### CentraLite
- [Contact Sensor](http://a.co/g9eWPAQ): CentraLite 3300-S
- [Motion Sensor](http://a.co/9PCEorM): CentraLite 3305-S
- [Dimmer Switch](https://centralite.com/products/smart-switch): CentraLite 3130
- [Water Sensor](https://centralite.com/products/water-sensor): CentraLite 3315-S
- [Contact Sensor](https://www.irisbylowes.com/support/?guideTitle=Iris-Contact-Sensor-3320-L-(2nd-Gen)&guideId=441744fa-3e2b-3bc9-87b2-a8fc76d85341): CentraLite 3320-L
- [Motion Sensor](http://a.co/iYjshAP): CentraLite 3325-S
- [Motion Sensor](https://www.irisbylowes.com/support/?guideTitle=Iris-Motion-Sensor&guideId=4be71b61-5938-30b6-8154-bd90cb9b4796): CentraLite 3326-L
- [Contact Sensor](http://a.co/9PCEorM): CentraLite 3321-S
- [Temperature / Humidity Sensor](https://bit.ly/2GYguGR): CentraLite 3310-S

### Xiaomi Aqara
- [Cube](https://www.aqara.com/en/cube_controller-product.html): lumi.sensor_cube.aqgl01
- [Button](https://www.aqara.com/en/wireless_mini_switch.html): lumi.sensor_switch.aq2
- [Vibration Sensor](http://www.xiaomimagazine.com/new-sensor-for-the-smart-home-xiaomi-check-aqara-smart-motion-sensor/): lumi.vibration.aq1
- [Contact Sensor](https://www.aqara.com/en/door_and_window_sensor-product.html): lumi.sensor_magnet.aq2
- [Motion Sensor](https://www.aqara.com/en/motion_sensor.html): lumi.sensor_motion.aq2
- [Temperature / Humidity Sensor](https://www.aqara.com/en/temperature_and_humidity_sensor-product.html): lumi.weather
- [Water Leak](https://www.aqara.com/en/water_leak_sensor.html): lumi.sensor_wleak.aq1

### Osram
- [OSRAM LIGHTIFY Dimming Switch](https://assets.osram-americas.com/assets/Documents/LTFY012.06c0d6e6-17c7-4dcb-bd2c-1fca7feecfb4.pdf):

### SmartThings
- [Arrival Sensor](https://support.smartthings.com/hc/en-us/articles/212417083): tagv4
- [Motion Sensor](http://a.co/65rSQjZ): MotionV4
- [Multi Sensor](http://a.co/gez6SzW): MultiV4

# Configuration:

1. Update Home Assistant to 0.85.1 or a later version.

**NOTE:** Some devices will need to be unpaired and repaired in order to see sensor values populate in Home Assistant.

# Device Specifics:

### Centralite

- All supported devices report battery level
- Dimmer Switch publishes events to Home Assistant
- Dimmer Switch temperature sensor is removed because it is non functional
- 3321-S reports acceleration
- 3310-S reports humidity

### Osram

- Dimmer Switch publishes events to Home Assistant and reports battery level
- Dimmer Switch temperature sensor is removed because it is non functional

### Xiaomi Aqara

- All supported devices report battery level
- All supported devices report temperature but I am unsure if it is correct or accurate
- Vibration sensor exposes a binary sensor in Home Assistant that reports current vibration state
- Vibration sensor sends `tilt` and `drop` events to Home Assistant
- Cube sends the following events: `flip (90 and 180 degrees)`, `rotate_left`, `rotate_right`, `knock`, `drop`, `slide` and `shake`
- Motion sensor exposes binary sensors for motion and occupancy.
- Button sends events to Home Assistant

### SmartThings

- All supported devices report battery level
- tagV4 exposed as a device tracker in Home Assistant. The current implementation will use batteries rapidly
- MultiV4 reports acceleration

### Thanks

- Special thanks to damarco for the majority of the device tracker code
- Special thanks to Yoda-x for the Xioami attribute parsing code
- Special thanks to damarco and Adminiuga for allowing me to bounce ideas off of them and for listening to me ramble
