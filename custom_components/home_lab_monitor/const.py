"""Constants for Home Lab Monitor integration."""

DOMAIN = "home_lab_monitor"

# Config entry keys
CONF_HOSTS = "hosts"
CONF_INTERVAL = "interval"
CONF_TIMEOUT = "timeout"

# Default values
DEFAULT_INTERVAL = 60  # seconds
DEFAULT_TIMEOUT = 3    # seconds

# Service names
SERVICE_ADD_HOST = "add_host"
SERVICE_REMOVE_HOST = "remove_host"
SERVICE_SCAN_NOW = "scan_now"

# State persistence
STATE_FILE = "home_lab_monitor_hosts.json"

# Status values
STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"
STATUS_UNKNOWN = "unknown"
