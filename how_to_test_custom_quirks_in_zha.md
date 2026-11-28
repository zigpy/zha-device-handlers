The instruction-guide below is written with the assumed premises that you are and end-user of Home Assistant's [ZHA integration](https://www.home-assistant.io/integrations/zha), however please note that this guide is meant to be useful regardless if you are an ZHA end-user or first-time zha-quirk developer.

# How to test a not yet merged custom quirk in ZHA

If you have bought a non-standard Zigbee device that is not yet supported in Home Assistant's ZHA integration but someone have already written and shared a experimental "custom quirk" (ZHA Device Handler) that not get been merged into a "[ZHA Device Handlers"](https://github.com/zigpy/zha-device-handlers)" library release then you as an end-user can still manually add that to your Home Assistant instance for testing using something like File Editor or Samba share add-ons in Home Assistant.

1. Get a copy of an existing "custom quirk" that is meant for your specific Zigbee device (or code your own custom quirks). Tip is to search for the specific Zigbee device signature among open issues and open pull requests as those might contain experimental custom quirk that have not yet been merged for your Zigbee device, see https://github.com/zigpy/zha-device-handlers/issues?q=is%3Aissue+is%3Aopen and https://github.com/zigpy/zha-device-handlers/pulls?q=is%3Aopen+is%3Apr
2. Inside your Home Assistant instance, create a directory/folder for your custom quirks (for example `/config/zha_quirks/`)
3. Copy or create a quirk file in this directory (called it for example “`devicemodelzyz_devicetypexyz.py`”). This file should contain the Python script for the quirk and its specific Zigbee device signature unique to it. 
4. Add configuration with the full path to the directory that now containing custom quirk module(s) that will override and take precedence over any built-in quirks matching any device that has the same Zigbee device signature. to Home Assistant's config.yaml
```
zha:
  database_path: /config/zigbee.db
  custom_quirks_path: /config/zha_quirks/
```
5. Restart Home Assistant to make the quirk take effect.
6. If and when a better ZHA Device Handler quirk is merged into the zha-quirks package then remove the custom quirk you added and possibly the whole folder if it was the last custom quirk that you added.

Note! If your Home Assistant is running inside a container then you must then you must edit and add or remove the file inside that container, see the community discussion thread at https://github.com/zigpy/zha-device-handlers/discussions/693
