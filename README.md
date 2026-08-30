# SkylinkNet Alarm — Home Assistant integration

Unofficial Home Assistant integration for **SkylinkNet** alarm hubs
(SkylinkNet / Skylink Home, made by Capital Prospect Ltd). It exposes your hub
as a native **Alarm Control Panel** entity so you can arm home, arm away and
disarm from Home Assistant — with dashboards, automations and schedules —
without IFTTT.

It also brings every door, window and motion sensor paired to your hub into
Home Assistant as a regular `binary_sensor` — **reporting all the time, not just
while the alarm is armed** — so an alarm you already own turns into a house full
of sensors you can automate on.

> ⚠️ This talks to the SkylinkNet cloud (`api-1.skyhm.net`), the same service the
> official app uses. It is not made or endorsed by Skylink. Use at your own risk.

## Features

- `alarm_control_panel` entity per hub: **Arm Home / Arm Away / Disarm** (+ Panic/Trigger).
- **Realtime updates over WebSocket** — the same channel the official app uses, so
  state changes show up in about a second instead of on a poll. A 10-minute poll
  stays as a fallback in case that channel goes quiet.
- States: `disarmed`, `armed_home`, `armed_away`, `pending` (entry delay),
  `arming` (exit delay), `triggered` (panic).
- A `binary_sensor` per contact/motion device, with zone and battery attributes —
  **live whether the alarm is armed or not**, so your alarm's door, window and
  motion sensors become general-purpose Home Assistant sensors. See
  [Your alarm sensors, all day long](#your-alarm-sensors-all-day-long).
- A **connectivity sensor** that tells you when the hub goes offline — see
  [Notifications](#notifications), you really want an automation on this one.
- Open zones are bypassed automatically when arming, so the hub doesn't trigger
  the instant you arm with a door open.
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

## Notifications

> ### ⚠️ Set up the offline alert first — it is the one that matters most
>
> The integration creates a **connectivity** sensor
> (`binary_sensor.<your_hub>_conexion`). When the hub loses its connection to the
> cloud, **you cannot arm or disarm remotely — from Home Assistant *or* from the
> SkylinkNet app** — and the panel/zone entities go `unavailable` so they never
> show a stale state. Without this automation, a hub that quietly went offline
> looks exactly like a hub that is idle.
>
> **Create this one even if you skip every other example below.**
>
> ```yaml
> - alias: SkylinkNet hub offline/online
>   triggers:
>     - trigger: state
>       entity_id: binary_sensor.YOUR_HUB_conexion   # the connectivity sensor
>       to: "off"
>       for: "00:02:00"        # ignore brief internet blips
>       id: offline
>     - trigger: state
>       entity_id: binary_sensor.YOUR_HUB_conexion
>       from: "off"
>       to: "on"
>       id: online
>   conditions:
>     - condition: template
>       value_template: >-
>         {{ trigger.from_state is not none and trigger.from_state.state
>            not in ["unknown", "unavailable"] }}
>   actions:
>     - choose:
>         - conditions:
>             - condition: trigger
>               id: offline
>           sequence:
>             - action: notify.YOUR_PHONE
>               data:
>                 title: 🔴 Alarm
>                 message: Hub OFFLINE — cannot arm or disarm remotely
>                 data:
>                   push:
>                     interruption-level: time-sensitive
>         - conditions:
>             - condition: trigger
>               id: online
>           sequence:
>             - action: notify.YOUR_PHONE
>               data:
>                 title: 🟢 Alarm
>                 message: Hub back online
>   mode: queued
> ```

### Alarm triggered (critical alert)

The panel goes to `triggered` when the alarm fires. On iOS you can send a
**critical** notification — it sounds even if the phone is silenced or in Do Not
Disturb — with a button to disarm right from the notification:

```yaml
- alias: SkylinkNet alarm triggered
  triggers:
    - trigger: state
      entity_id: alarm_control_panel.YOUR_HUB
      to: triggered
  actions:
    - action: notify.YOUR_PHONE
      data:
        title: 🚨 ALARM
        message: The alarm was triggered!
        data:
          push:
            sound:
              name: default
              critical: 1
              volume: 1.0
          actions:
            - action: SKYLINKNET_DISARM
              title: Disarm
              destructive: true
  mode: single

# Makes the "Disarm" button on that notification actually disarm
- alias: SkylinkNet disarm from notification
  triggers:
    - trigger: event
      event_type: mobile_app_notification_action
      event_data:
        action: SKYLINKNET_DISARM
  actions:
    - action: alarm_control_panel.alarm_disarm
      target:
        entity_id: alarm_control_panel.YOUR_HUB
  mode: single
```

The examples below are optional extras.

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

## Your alarm sensors, all day long

Probably the nicest side effect of this integration: **your alarm's sensors keep
reporting even when the alarm is disarmed.**

SkylinkNet only cares about those sensors while the system is armed — their whole
job is to set off the siren. In Home Assistant they are just `binary_sensor`
entities, live 24/7, so door, window and motion detectors you already paid for
and mounted years ago become sensors you can build anything on:

```yaml
# Announce or light up when the front door opens — at any time, armed or not
- alias: Front door opened
  triggers:
    - trigger: state
      entity_id: binary_sensor.front_door
      to: "on"
  actions:
    - action: light.turn_on
      target: { entity_id: light.entry }

# Nobody home and a door opens while disarmed → that is worth knowing about
- alias: Door opened while nobody is home
  triggers:
    - trigger: state
      entity_id: binary_sensor.front_door
      to: "on"
  conditions:
    - condition: state
      entity_id: alarm_control_panel.YOUR_HUB
      state: disarmed
    - condition: numeric_state
      entity_id: zone.home
      below: 1
  actions:
    - action: notify.YOUR_PHONE
      data:
        message: Front door opened and nobody is home

# Don't cool the street: window open while the AC runs
- alias: Window open with AC on
  triggers:
    - trigger: state
      entity_id: binary_sensor.window
      to: "on"
      for: "00:02:00"
  conditions:
    - condition: state
      entity_id: climate.living_room
      state: cool
  actions:
    - action: notify.YOUR_PHONE
      data:
        message: The window is open and the AC is running
```

Other things people build with these: night lights on motion, a chime when a
door opens, "you left the laundry door open" reminders, or a check for open
zones before you leave so you don't have to bypass them when arming.

**One caveat about motion sensors:** alarm PIRs have a cooldown (typically 1–3
minutes between reports) to save battery — they do not report continuous
presence like a dedicated automation sensor. They are great for "turn on when
someone arrives", but for "keep it on while someone is there" use a generous
timer instead of waiting for repeated triggers.

## How it works

- Authenticates to the SkylinkNet cloud (`guest/login`) and keeps the session.
- Listens on `wss://api-1.skyhm.net/websock/hu/<hub_id>/<key>`, which pushes the
  full device list whenever anything changes (the official app uses this too).
- Falls back to reading `api/dev/read` every 10 minutes; the hub's own device
  (`F0000000`) carries the alarm state.
- Sends commands via `api/alarm/set_alarm` (`arm_home` / `arm_away` / `disarm` / `panic`).

## Notes & limitations

- **Cloud dependency:** commands travel through the SkylinkNet cloud, so the hub
  needs internet. Home Assistant automations/schedules run locally, but the final
  command is delivered via the cloud.
- The hub key is per-hub and is **not** returned by the API; you must provide it.
- Reverse-engineered and community-maintained; the cloud API could change.

## License

MIT
