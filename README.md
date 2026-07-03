# Home Lab Monitor Integration

Real-time monitoring for your home lab hosts, powered by Home Assistant.

Monitor ping, TCP port status, and HTTP services across all your lab devices — with live dashboards, automatic alerting on status changes, and dynamic host management through the UI.

## Features

- **Multi-layer health checks**: Ping (ICMP), TCP port scanning, and HTTP status code monitoring
- **Dynamic host management**: Add, remove, and reconfigure hosts directly from the Home Assistant UI or via automation scripts
- **Group organization**: Categorize hosts into groups (NAS, Servers, Workstations, Edge)
- **Comprehensive dashboards**: Visualize overall lab health and drill down to individual hosts
- **Real-time alerts**: Get notified when hosts go down, come back up, or services change status
- **Persistent configuration**: Host definitions survive restarts

## Installation

### HACS (Recommended)

1. Open **HACS** → **Integrations**
2. Click **⊕** (Explore and download repositories)
3. Search for **"Home Lab Monitor"** or add custom repository: `https://github.com/jh007e/home-lab-monitor-hacs`
4. Click **Download**
5. **Restart Home Assistant**
6. Go to **Settings → Devices & Services** → **Add Integration** → search for **"Home Lab Monitor"**

### Manual

1. Copy the `home_lab_monitor` folder to your Home Assistant `custom_components/` directory:

   ```bash
   mkdir -p /config/custom_components/home_lab_monitor
   # Copy all files from home_lab_monitor/ into it
   ```

2. Restart Home Assistant

## Configuration

After adding the integration, configure it via the UI:

1. Go to **Settings → Devices & Services → Home Lab Monitor → Configure**
2. Set the **scan interval** (default: 60 seconds) and **timeout** (default: 3 seconds)
3. Click **Submit**

### Adding Hosts

After initial setup, manage hosts through the integration options:

1. Go to **Settings → Devices & Services → Home Lab Monitor → Options**
2. Select **Add Host**
3. Fill in:
   - **Name**: Friendly name (e.g., "Synology NAS")
   - **IP**: IP address to monitor
   - **Group**: Category (default, nas, servers, workstations, edge, other)
   - **Ports**: Comma-separated list (e.g., `22,80,443`)
   - **Labels**: Port:Label pairs (e.g., `22:SSH,80:HTTP,443:HTTPS`)
   - **HTTP Ports**: Specific ports to check for HTTP responses

### Via Services

Add hosts programmatically from automations or scripts:

```yaml
# Add a host
service: home_lab_monitor.add_host
data:
  name: "Synology NAS"
  ip: "192.168.1.35"
  group: "nas"
  ports: [80, 443, 22]
  labels:
    "80": "DSM"
    "443": "DSM-SSL"
    "22": "SSH"
  http_ports: [80, 443]
  description: "Synology NAS for storage"
```

Remove a host:

```yaml
service: home_lab_monitor.remove_host
data:
  ip: "192.168.1.35"
```

Trigger an immediate scan:

```yaml
service: home_lab_monitor.scan_now
data: {}
```

## Available Entities

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.<hostname>_status` | Overall host health (on = healthy) |
| `binary_sensor.<hostname>_port_<port>` | Individual port status |

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.home_lab_overall` | Overall lab health state (healthy, degraded, down) |
| `sensor.<hostname>` | Detailed host information |

### Host Sensor Attributes

All host sensors include:

- **ip**: IP address
- **group**: Host group category
- **status**: Overall status (`healthy`, `degraded`, `down`, `unknown`)
- **ping_ok**: Whether ICMP ping succeeded
- **ports**: Port status map (`{"22": "open", "80": "open"}`)
- **scan_time**: Time taken for last scan (seconds)
- **last_updated**: ISO timestamp
- **http_services**: HTTP response details for monitored ports

## Dashboard

Use the built-in entities card or create custom Lovelace views:

### Quick Dashboard Example

```yaml
title: Home Lab Status
views:
  - title: Overview
    cards:
      - type: entities
        title: Overall Health
        entities:
          - sensor.home_lab_overall
      - type: entities
        title: Hosts
        entities:
          - binary_sensor.nas_status
          - binary_sensor.server1_status
          - binary_sensor.server2_status
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Hosts not showing up | Verify integration is installed in `custom_components/`, check HA logs |
| Services not working | Check Settings → System → Logs for errors |
| Ports reporting closed | Some hosts block ICMP (ping). TCP checks still work independently |
| HACS says "can't use version" | Restart HACS or re-download the integration to refresh the tag |
| Scan fails for specific host | Verify the host is reachable from the Home Assistant machine |

## Architecture

```
Integration Setup
  ├── Coordinator (DataUpdateCoordinator)
  │     └── Periodic scanning of all configured hosts
  ├── Binary Sensors
  │     ├── One per host (overall health)
  │     └── One per port (individual TCP/HTTP status)
  ├── Group Sensor
  │     └── Aggregated lab health overview
  └── Services
        ├── add_host, remove_host, scan_now
        └── Persistent state (JSON) across restarts
```

## Requirements

- Home Assistant 2023.1.0 or later
- Network access to all monitored hosts (must be on the same LAN or reachable)
- ICMP and TCP port access (some hosts may block ping — TCP checks still function)

## License

MIT License — see LICENSE for details.

## Support

Found a bug or have a feature request? [Open an issue](https://github.com/jh007e/home-lab-monitor-hacs/issues)
