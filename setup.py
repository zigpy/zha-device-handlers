"""Setup module for ZHAQuirks."""

from setuptools import find_packages, setup

VERSION = "0.0.13"


def readme():
    """Print long description."""
    with open('README.md') as f:
        return f.read()


setup(
    name="zha-quirks",
    version=VERSION,
    description="Library implementing Zigpy quirks for ZHA in Home Assistant",
    long_description=readme(),
    long_description_content_type='text/markdown',
    url="https://github.com/dmulcahey/zha-device-handlers",
    author="David F. Mulcahey",
    author_email="david.mulcahey@icloud.com",
    license="Apache License Version 2.0",
    keywords='zha quirks homeassistant hass',
    packages=find_packages(exclude=['*.tests']),
    python_requires='>=3'
)
