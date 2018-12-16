# ZHA Device Handlers For Home Assistant

ZHA Device Handlers are quirks implementations for [Zigpy](https://github.com/zigpy/zigpy), the library that provides the [Zigbee](http://www.zigbee.org) support for the [ZHA](https://www.home-assistant.io/components/zha/) component in [Home Assistant](https://www.home-assistant.io). These device handlers are similar to the device handlers that exist as part of the Smart Things platform and they expose additional functionality that isn't provided OOTB by the existing integration between these platforms. See [Device Specifics](#Device-Specifics) for details. 

These device handlers currently require the use of a custom [branch](https://github.com/dmulcahey/home-assistant/tree/dm/zha-sensor-playground) of Home Assistant. This will be remediated soon. 
#
# Currently Supported Devices:

### CentraLite
- [Dimmer Switch](https://centralite.com/products/smart-switch): CentraLite 3130
- [Water Sensor](https://centralite.com/products/water-sensor): CentraLite 3315-S
- [Contact Sensor](https://www.irisbylowes.com/support/?guideTitle=Iris-Contact-Sensor-3320-L-(2nd-Gen)&guideId=441744fa-3e2b-3bc9-87b2-a8fc76d85341): CentraLite 3320-L
- [Motion Sensor](https://www.irisbylowes.com/support/?guideTitle=Iris-Motion-Sensor&guideId=4be71b61-5938-30b6-8154-bd90cb9b4796): CentraLite 3326-L

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
#
# Configuration:

1. Update Home Assistant to use the ZHA component from this [branch](https://github.com/dmulcahey/home-assistant/tree/dm/zha-sensor-playground). Be sure to get the `zha.py` files from every component that ZHA supports.

**NOTE:** Some devices will need to be unpaired and repaired in order to see sensor values populate in Home Assistant.

#
# Device Specifics:

### Centralite 

- All supported devices report battery level
- Dimmer Switch publishes events to Home Assistant
- Dimmer Switch temperature sensor is removed because it is non functional

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

- tagV4 exposed as a device tracker in Home Assistant and reports battery. The current implementation will use batteries rapidly. 

#
### Thanks

- Special thanks to damarco for the majority of the device tracker code
- Special thanks to Yoda-x for the Xioami attribute parsing code
- Special thanks to damarco and Adminiuga for allowing me to bounce ideas off of them and for listening to me ramble
