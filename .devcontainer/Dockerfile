FROM mcr.microsoft.com/devcontainers/python:1-3.12

USER root
ENV DEBIAN_FRONTEND=noninteractive

# Install common build dependencies required for compiling Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        cargo \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip/setuptools to a modern version
RUN python3 -m pip install --upgrade pip setuptools wheel

USER vscode

WORKDIR /workspaces/zha-device-handlers
