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

## Notifications (optional)

Every time the panel arms, the integration fires a **`skylinknet_armed`** event
on the Home Assistant bus. Its data is:

| Field | Meaning |
|-------|---------|
| `mode` | `arm_home` or `arm_away` |
| `bypass` | `true` if any open zone was bypassed |
| `bypassed` | list of bypassed zone **names** |
| `bypassed_ids` | list of bypassed device ids |
| `hub_id`, `entity_id` | which hub / entity |

Use that event (and the panel's own state) to get push notifications. Replace
`notify.YOUR_PHONE` with your own service (e.g. `notify.mobile_app_...`) and
`alarm_control_panel.YOUR_HUB` with your entity id.

**On arm** — tells you the mode and which open zones were bypassed:

```yaml
- alias: SkylinkNet armed notification
  triggers:
    - trigger: event
      event_type: skylinknet_armed
  actions:
    - action: notify.YOUR_PHONE
      data:
        title: 🛡️ Alarm
        message: >-
          {% set mode = 'Home' if trigger.event.data.mode == 'arm_home' else 'Away' %}
          {% set b = trigger.event.data.bypassed %}
          {% if b %}Armed {{ mode }} — bypassed: {{ b | join(', ') }}{% else %}Armed {{ mode }}{% endif %}
  mode: queued
```

**On disarm** — fires for disarms from *anywhere* (HA, the SkylinkNet app, or the
physical keypad), because it watches the panel's state:

```yaml
- alias: SkylinkNet disarmed notification
  triggers:
    - trigger: state
      entity_id: alarm_control_panel.YOUR_HUB
      to: disarmed
  conditions:
    - condition: template
      value_template: >-
        {{ trigger.from_state is not none and trigger.from_state.state
           not in ["unknown", "unavailable", "disarmed"] }}
  actions:
    - action: notify.YOUR_PHONE
      data:
        title: 🔓 Alarm
        message: Disarmed
  mode: queued
```

You can do much more with the contact/motion `binary_sensor`s — e.g. notify when
a door opens while armed, or turn on lights on motion at night.

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
