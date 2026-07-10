# Deco S1900 Local for Home Assistant

[![HACS validation](https://img.shields.io/github/actions/workflow/status/simone-losito/deco-s1900-local/validate.yml?branch=main&label=HACS)](https://github.com/simone-losito/deco-s1900-local/actions)
[![Hassfest](https://img.shields.io/github/actions/workflow/status/simone-losito/deco-s1900-local/hassfest.yml?branch=main&label=Hassfest)](https://github.com/simone-losito/deco-s1900-local/actions)
[![GitHub release](https://img.shields.io/github/v/release/simone-losito/deco-s1900-local)](https://github.com/simone-losito/deco-s1900-local/releases)
[![License](https://img.shields.io/github/license/simone-losito/deco-s1900-local)](LICENSE)

Local Home Assistant integration for **TP-Link Deco S1900** mesh systems.

Created and maintained by **Simone Losito**.

> This is an unofficial community project and is not affiliated with or endorsed by TP-Link.

## Features

- Fully local communication with the master Deco web interface
- Automatic browser-style encrypted login
- Mesh and node status
- Master and satellite discovery
- Connection type, parent node, IP address and firmware
- Online and known client counts
- Client details grouped by individual Deco
- Guest Wi-Fi state in read-only mode
- Manual refresh button
- Configurable polling interval
- Reauthentication and reconfiguration flows
- Privacy-conscious diagnostics
- Local brand assets for recent Home Assistant versions
- Italian and English translations

## Supported environment

Developed and tested for:

- TP-Link Deco S1900
- Hardware version 1.0
- Firmware `1.5.2 Build 20240927 Rel. 68997`
- Home Assistant 2026.4 or newer

Other firmware versions may work but are not yet confirmed.

## Installation with HACS

1. Open **HACS → Integrations**.
2. Open the menu and select **Custom repositories**.
3. Add:

   `https://github.com/simone-losito/deco-s1900-local`

4. Select category **Integration**.
5. Install **Deco S1900 Local**.
6. Restart Home Assistant.
7. Open **Settings → Devices & services → Add integration**.
8. Search for **Deco S1900 Local**.

## Manual installation

Copy:

`custom_components/deco_s1900_local`

to:

`/config/custom_components/deco_s1900_local`

Then restart Home Assistant.

## Configuration

Use:

- the IP address of the **master Deco**
- an **administrator password** accepted by the local Deco web interface

A dedicated administrator account is recommended because some Deco firmware versions allow only one active web session per account.

## Options

Open the integration and select the gear icon:

- update interval
- maximum number of client details exposed per entity
- enable or disable client details in attributes

The options page reloads the integration automatically after saving.

## Diagnostics

From the integration menu select **Download diagnostics**.

Passwords and detailed client identity information are not exported.

## Dashboard example

The `examples/` directory contains a tablet-oriented Lovelace example.

## Support the project

If this integration is useful, you can support its development:

[![Buy Me a Coffee](https://img.buymeacoffee.com/button-api/?text=Offrimi%20un%20caff%C3%A8&emoji=%E2%98%95&slug=simonelosito&button_colour=00b8d4&font_colour=ffffff&font_family=Poppins&outline_colour=000000&coffee_colour=FFDD00)](https://www.buymeacoffee.com/simonelosito)

> Before publishing, create or confirm the Buy Me a Coffee profile `simonelosito`, or replace the link with your preferred support page.

## License

MIT © 2026 Simone Losito
