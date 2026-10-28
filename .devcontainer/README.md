# Devcontainer for `zha-device-handlers`

This folder contains the VS Code Dev Container configuration for this repository.
Using the devcontainer is optional, but it is a convenient way to get a consistent setup quickly.

## Why use it

- Fast onboarding for new contributors
- Isolated environment (keeps your host setup clean)
- Same base tooling across machines and Codespaces

## Quick start

1. Open this repository in VS Code.
2. Click "Reopen in Container" when VS Code prompts you.
3. Wait until container creation and `postCreateCommand` finish.
4. Start working.

## What happens automatically

- Base image: `mcr.microsoft.com/devcontainers/python:1-3.12`
- Workspace path: `/workspaces/zha-device-handlers`
- Initial setup command: `bash script/setup`

If setup fails, run `bash script/setup` manually in the container terminal.

## Project docs

For day-to-day commands and contribution guidance, please use:

- Main contributor docs: [../README.md](../README.md)
- Agent-specific guidance: [../AGENTS.md](../AGENTS.md)
