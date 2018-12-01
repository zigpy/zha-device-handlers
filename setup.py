"""Setup module for ZHAQuirks"""

from setuptools import find_packages, setup

setup(
    name="zha-quirks",
    version="0.0.1",
    description="Library implementing Zigpy quirks for the ZHA component in Home Assistant",
    url="http://github.com/dmulcahey/zha-device-handlers",
    author="David F. Mulcahey",
    author_email="david.mulcahey@icloud.com",
    license="Apache License Version 2.0",
    packages=find_packages(exclude=['*.tests'])
)
