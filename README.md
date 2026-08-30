# SkylinkNet Alarm — Home Assistant integration

Unofficial Home Assistant integration for **SkylinkNet** alarm hubs
(SkylinkNet / Skylink Home, made by Capital Prospect Ltd). It exposes your hub
as a native **Alarm Control Panel** entity so you can arm home, arm away and
disarm from Home Assistant — with dashboards, automations and schedules —
without IFTTT.

> ⚠️ This talks to the SkylinkNet cloud (`api-1.skyhm.net`), the same service the
> official app uses. It is not made or endorsed by Skylink. Use at your own risk.

## Features

- `alarm_control_panel` entity per hub: **Arm Home / Arm Away / Disarm** (+ Panic/Trigger).
- Live state polling: `disarmed`, `armed_home`, `armed_away`, `pending` (entry delay),
  `arming` (exit delay), `triggered` (panic).
- Simple UI setup (config flow) — no YAML.

## Requirements

- Home Assistant **2024.11** or newer.
- A SkylinkNet account (email + password — the same you use in the app).
- Your **Hub Password** (the *key* you set when you first configured the hub).
  If you don't remember it, you can reset the key from the SkylinkNet app.

## Installation

### Via HACS (recommended)

1. In HACS → **Integrations** → menu (⋮) → **Custom repositories**.
2. Add this repository URL, category **Integration**.
3. Install **SkylinkNet Alarm**, then restart Home Assistant.

### Manual

Copy `custom_components/skylinknet/` into your HA `config/custom_components/`
folder and restart Home Assistant.

## Setup

1. **Settings → Devices & Services → Add Integration → SkylinkNet Alarm**.
2. Enter your account **email** and **password**.
3. Pick your **hub** and enter its **Hub Password (key)**.

An alarm panel entity will be created. Add the **Alarm Panel** card to a
dashboard, or use it in automations/schedules like any other alarm entity.

## How it works

- Authenticates to the SkylinkNet cloud (`guest/login`) and keeps the session.
- Reads the current state from `api/dev/read` (the hub's own device, `F0000000`).
- Sends commands via `api/alarm/set_alarm` (`arm_home` / `arm_away` / `disarm` / `panic`).

## Notes & limitations

- **Cloud dependency:** commands travel through the SkylinkNet cloud, so the hub
  needs internet. Home Assistant automations/schedules run locally, but the final
  command is delivered via the cloud.
- The hub key is per-hub and is **not** returned by the API; you must provide it.
- Reverse-engineered and community-maintained; the cloud API could change.

## License

MIT
