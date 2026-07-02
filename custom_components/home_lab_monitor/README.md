# Home Lab Monitor Integration for Home Assistant

A custom Home Assistant integration that monitors your home lab hosts (ping, TCP ports, HTTP services) and provides real-time status dashboards.

## Features

- **Real-time monitoring**: Ping, port scanning, and HTTP status checks
- **Dynamic host management**: Add/remove hosts via UI or services
- **Group organization**: Organize hosts by category (NAS, Servers, Workstations, Edge)
- **Comprehensive dashboards**: Multiple visualization options
- **Alerting**: Status changes and service outages
- **Persistent configuration**: Hosts survive restarts

## Installation

### Method 1: Copy Files (Recommended)

1. Create the integration directory in your Home Assistant config:
   ```bash
   # On your Home Assistant system (typically at /usr/share/hassio/homeassistant)
   mkdir -p /config/custom_components/home_lab_monitor
   ```

2. Copy all files from this directory to the custom_components directory:
   ```bash
   # From this machine, copy to your HA system
   scp -r home_lab_monitor_integration/* root@192.168.12.227:/usr/share/hassio/homeassistant/custom_components/home_lab_monitor/
   ```

3. Restart Home Assistant

4. Add the integration via UI:
   - Go to Settings > Devices & Services
   - Click "Add Integration"
   - Search for "Home Lab Monitor"
   - Configure scan interval and timeout

### Method 2: Git Submodule

1. Add as a git submodule to your config:
   ```bash
   cd /config
   git submodule add https://github.com/yourusername/home-lab-monitor.git custom_components/home_lab_monitor
   ```

2. Restart Home Assistant

3. Configure via UI (Settings > Devices & Services > Add Integration)

## Configuration

### Initial Setup

After installation, configure via the UI:
1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Home Lab Monitor"
4. Set scan interval (default: 60s) and timeout (default: 3s)

### Adding Hosts

You can add hosts in two ways:

#### Via UI (Settings > Devices & Services > Home Lab Monitor > Options):
1. Click "Add Host"
2. Fill in:
   - Name: Friendly name for the host
   - IP: IP address to monitor
   - Group: Category (default, nas, servers, workstations, edge, other)
   - Ports: Comma-separated list (e.g., 22,80,443)
   - Labels: Port:Label pairs (e.g., 22:SSH,80:HTTP)
   - HTTP Ports: Ports to check for HTTP responses

#### Via Services:
```yaml
# Add a host via service call
service: home_lab_monitor.add_host
data:
  name: "Synology"
  ip: "192.168.12.35"
  group: "nas"
  ports:
    - 80
    - 443
    - 22
  labels:
    "80": "DSM"
    "443": "DSM-SSL"
    "22": "SSH"
  http_ports:
    - 80
    - 443
  description: "Synology NAS"
```

### Removing Hosts

#### Via UI:
1. Go to Settings > Devices & Services > Home Lab Monitor > Options
2. Click "Remove Host"
3. Select the host to remove

#### Via Services:
```yaml
service: home_lab_monitor.remove_host
data:
  ip: "192.168.12.35"
```

## Available Entities

### Binary Sensors
- `binary_sensor.{hostname}_status` - Overall host status (on=healthy, off=not healthy)
- `binary_sensor.{hostname}_port_{port}` - Individual port status

### Sensors
- `sensor.home_lab_overall` - Overall lab health state
- `sensor.{hostname}` - Detailed host information with attributes

### Attributes
All host sensors include these attributes:
- `ip`: IP address
- `group`: Host group category
- `status`: Overall status (healthy, degraded, down, unknown)
- `ping_ok`: Whether ping succeeded
- `ports`: Object mapping port numbers to status
- `scan_time`: Time taken for last scan (seconds)
- `last_updated`: ISO timestamp of last update
- `http_services`: HTTP service status for configured ports

## Dashboard Setup

### Option 1: Native HA Dashboard
Create a new dashboard in Home Assistant and add:
1. Entities card for overall status
2. Horizontal stack with host status cards
3. Button card for scan_now service call

### Option 2: HTML Dashboard
Upload `dashboard.html` to your Home Assistant `www` folder:
```bash
cp dashboard.html /config/www/home-lab-monitor.html
```

Then create a web view in configuration.yaml:
```yaml
panel_custom:
  - name: home-lab-monitor
    title: Home Lab Monitor
    sidebar_title: Lab Monitor
    sidebar_icon: mdi:server
    url: /local/home-lab-monitor.html
    embed_iframe: true
    require_admin: false
```

### Option 3: Lovelace Dashboard YAML
Import the `dashboard.yaml` file or use these entities directly in your UI:
- `sensor.home_lab_overall` - Overall health state
- `binary_sensor.*_status` - Individual host status

## Services

### home_lab_monitor.add_host
Add a new host to monitoring.

**Required fields:**
- `name`: String
- `ip`: String
- `ports`: Array of integers

**Optional fields:**
- `labels`: Object mapping port numbers to labels
- `http_ports`: Array of ports to check for HTTP
- `description`: String
- `group`: String (default: "default")

### home_lab_monitor.remove_host
Remove a host from monitoring.

**Required fields:**
- `ip`: String (IP address of host to remove)

### home_lab_monitor.scan_now
Trigger an immediate scan of all hosts.

**Fields:** None

## Troubleshooting

### Common Issues

**Hosts not showing up:**
- Check that the integration is properly installed in `custom_components/`
- Verify Home Assistant can reach the hosts (same network)
- Check HA logs for errors: `hass --log-rotate-days 0`

**Services not working:**
- Ensure the integration is loaded: Settings > System > Logs
- Check for errors in the Home Assistant log file

**Dashboard not loading:**
- Verify dashboard.html is in the `www` folder
- Check that panel_custom is properly configured
- Clear browser cache and reload

**Ports not responding:**
- Some hosts may block ICMP (ping). The integration falls back to TCP checks
- Verify ports are accessible from the Home Assistant host

## Architecture

The integration consists of:
- **Coordinator**: `DataUpdateCoordinator` that handles periodic scanning
- **Binary Sensors**: One per host + one per port
- **Group Sensor**: Shows overall lab health
- **Services**: For dynamic host management
- **Persistence**: Hosts saved to JSON file for restart recovery

## Files Structure

```
home_lab_monitor_integration/
├── __init__.py          # Main integration logic
├── binary_sensor.py     # Binary sensor entities
├── sensor.py            # Sensor entities
├── config_flow.py       # UI configuration flow
├── const.py             # Constants
├── manifest.json        # Integration manifest
├── services.yaml        # Service definitions
├── dashboard.yaml       # Dashboard configuration
├── dashboard.html       # Standalone HTML dashboard
└── README.md            # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.