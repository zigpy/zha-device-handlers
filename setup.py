"""Setup module for ZHAQuirks."""

import pathlib

from setuptools import find_packages, setup

VERSION = "0.0.89"


setup(
    name="zha-quirks",
    version=VERSION,
    description="Library implementing Zigpy quirks for ZHA in Home Assistant",
    long_description=(pathlib.Path(__file__).parent / "README.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/dmulcahey/zha-device-handlers",
    author="David F. Mulcahey",
    author_email="david.mulcahey@icloud.com",
    license="Apache License Version 2.0",
    keywords="zha quirks homeassistant hass",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8",
    install_requires=["zigpy>=0.52"],
    tests_require=["pytest"],
)
