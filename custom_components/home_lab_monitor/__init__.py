"""
Home Lab Monitor - Custom Home Assistant Integration.

Monitors home lab hosts (ping, TCP ports, HTTP services) and exposes
each host as a sensor + binary_sensor in Home Assistant.

Features:
  - Dynamic add/remove host via services
  - Config flow for UI-based setup
  - Periodic scan with configurable interval
  - Port-level and HTTP-level health checks
  - State persistence across restarts
"""

import datetime
import json
import logging
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_HOSTS,
    CONF_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SERVICE_ADD_HOST,
    SERVICE_REMOVE_HOST,
    SERVICE_SCAN_NOW,
    STATE_FILE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    """Set up config entry."""
    from . import sensor as sensor_platform
    from . import binary_sensor as binary_sensor_platform
    
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    interval = config_entry.options.get(
        CONF_INTERVAL, config_entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL)
    )
    timeout = config_entry.options.get(
        CONF_TIMEOUT, config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    )
    hosts = config_entry.options.get(CONF_HOSTS, config_entry.data.get(CONF_HOSTS, []))

    # Load saved hosts from persistent file
    hosts_file = Path(hass.config.dir) / STATE_FILE
    if hosts_file.exists() and not hosts:
        try:
            with open(hosts_file, "r") as f:
                saved_state = json.load(f)
                if saved_state.get("hosts"):
                    hosts = saved_state["hosts"]
                    _LOGGER.info(
                        "Loaded %d saved hosts from %s", len(hosts), hosts_file
                    )
        except Exception as exc:
            _LOGGER.warning("Failed to load saved hosts: %s", exc)

    # Save hosts to persistent file
    try:
        state = {
            "hosts": hosts,
            "saved_at": datetime.datetime.now().isoformat(),
        }
        with open(hosts_file, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as exc:
        _LOGGER.error("Failed to save hosts state: %s", exc)

    # Create coordinator
    coordinator = HomeLabMonitorCoordinator(
        hass, hosts=hosts, scan_interval=interval, timeout=timeout
    )
    hass.data[DOMAIN]["coordinator"] = coordinator
    hass.data[DOMAIN]["config_entry_id"] = config_entry.entry_id

    # Register services
    hass.data[DOMAIN]["services"] = _async_register_services(hass)

    # Initial scan
    await coordinator.async_refresh()

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor", "binary_sensor"])
    
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister services
    services = hass.data[DOMAIN].get("services", {})
    for service_name, service_func in services.items():
        try:
            hass.services.async_unregister(DOMAIN, service_name, service_func)
        except Exception:
            pass

    # Unload platforms
    result = await hass.config_entries.async_unload_platforms(
        config_entry, ["binary_sensor", "sensor"]
    )

    # Clean up hass.data
    hass.data[DOMAIN].clear()
    if DOMAIN in hass.data:
        del hass.data[DOMAIN]

    return result


def _async_register_services(hass: HomeAssistant):
    """Register custom services. Returns dict of service_name -> function for unregistration."""

    async def async_add_host(call: ServiceCall):
        """Add a new host to monitor."""
        name = call.data.get("name", "")
        ip = call.data.get("ip", "")
        ports = call.data.get("ports", [])
        labels = call.data.get("labels", {})
        http_ports = call.data.get("http_ports", [])
        description = call.data.get("description", "")
        group = call.data.get("group", "default")

        if not name or not ip:
            raise ValueError("name and ip are required")

        coordinator: HomeLabMonitorCoordinator = hass.data[DOMAIN]["coordinator"]
        config_entry_id = hass.data[DOMAIN]["config_entry_id"]
        coordinator.add_host(
            {
                "name": name,
                "ip": ip,
                "ports": ports,
                "labels": labels,
                "http_ports": http_ports,
                "description": description,
                "group": group,
                "added_at": datetime.datetime.now().isoformat(),
            }
        )

        # Reload entities
        await hass.config_entries.async_reload(config_entry_id)

    async def async_remove_host(call: ServiceCall):
        """Remove a host from monitoring."""
        host_ip = call.data.get("ip", "")
        if not host_ip:
            raise ValueError("ip is required")

        coordinator: HomeLabMonitorCoordinator = hass.data[DOMAIN]["coordinator"]
        config_entry_id = hass.data[DOMAIN]["config_entry_id"]
        coordinator.remove_host(host_ip)

        # Reload entities
        await hass.config_entries.async_reload(config_entry_id)

    async def async_scan_now(call: ServiceCall):
        """Trigger an immediate scan."""
        coordinator: HomeLabMonitorCoordinator = hass.data[DOMAIN]["coordinator"]
        await coordinator.async_refresh()

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_ADD_HOST, async_add_host)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_HOST, async_remove_host)
    hass.services.async_register(DOMAIN, SERVICE_SCAN_NOW, async_scan_now)

    # Return service refs for later unregistration
    return {
        SERVICE_ADD_HOST: async_add_host,
        SERVICE_REMOVE_HOST: async_remove_host,
        SERVICE_SCAN_NOW: async_scan_now,
    }


@dataclass
class HostStatus:
    """Status of a monitored host."""

    name: str
    ip: str
    alive: bool = False
    ping_ok: bool = False
    ports: dict = field(default_factory=dict)
    http_services: dict = field(default_factory=dict)
    overall_status: str = "unknown"
    last_scan: str = ""
    scan_time: float = 0.0
    group: str = "default"
    description: str = ""
    last_update: str = ""
    consecutive_failures: int = 0


class HomeLabMonitorCoordinator(DataUpdateCoordinator):
    """Coordinator for home lab monitor data."""

    def __init__(
        self, hass: HomeAssistant, hosts: list, scan_interval: int, timeout: int = 3
    ):
        """Initialize coordinator."""
        self.hass = hass
        self.hosts = hosts  # list of host configs
        self.scan_interval = scan_interval
        self.timeout = timeout
        self.host_statuses = {}  # ip -> HostStatus

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(seconds=scan_interval),
        )

    def add_host(self, host_config: dict):
        """Add a host to monitoring."""
        if any(h["ip"] == host_config["ip"] for h in self.hosts):
            _LOGGER.warning(
                "Host %s (%s) already exists",
                host_config["name"],
                host_config["ip"],
            )
            return

        self.hosts.append(host_config)
        self._save_hosts()
        _LOGGER.info("Added host: %s (%s)", host_config["name"], host_config["ip"])

        # Reload config entry with new hosts
        entry = (
            self.hass.config_entries.async_entries(DOMAIN)[0]
            if self.hass.config_entries.async_entries(DOMAIN)
            else None
        )
        if entry:
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_HOSTS: self.hosts}
            )

    def remove_host(self, ip: str):
        """Remove a host from monitoring."""
        before = len(self.hosts)
        self.hosts = [h for h in self.hosts if h["ip"] != ip]
        if len(self.hosts) < before:
            self._save_hosts()
            _LOGGER.info("Removed host: %s", ip)

            entry = (
                self.hass.config_entries.async_entries(DOMAIN)[0]
                if self.hass.config_entries.async_entries(DOMAIN)
                else None
            )
            if entry:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_HOSTS: self.hosts}
                )
        else:
            _LOGGER.warning("Host with IP %s not found", ip)

    def _save_hosts(self):
        """Persist hosts to disk."""
        hosts_file = Path(self.hass.config.dir) / STATE_FILE
        try:
            state = {
                "hosts": self.hosts,
                "saved_at": datetime.datetime.now().isoformat(),
            }
            with open(hosts_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            _LOGGER.error("Failed to save hosts: %s", exc)

    def _scan_host(self, host_name: str, host_info: dict) -> HostStatus:
        """Scan a single host."""
        ip = host_info["ip"]
        ports = host_info.get("ports", [])
        labels = host_info.get("labels", {})
        http_ports = host_info.get("http_ports", [])
        description = host_info.get("description", "")
        group = host_info.get("group", "default")
        timeout = self.timeout

        start = datetime.datetime.now()
        status = HostStatus(
            name=host_name,
            ip=ip,
            group=group,
            description=description,
            last_scan=start.isoformat(),
            last_update=start.isoformat(),
        )

        # Ping check
        try:
            result = os.popen(f"ping -c 1 -W {timeout} {ip} 2>&1").read()
            status.ping_ok = "1 packets received" in result or "1 received" in result
            status.alive = status.ping_ok
        except Exception as exc:
            _LOGGER.debug("Ping check failed for %s: %s", ip, exc)

        # Port checks
        port_results = {}
        for port in ports:
            port_key = str(port)
            is_open = self._check_port(ip, port, timeout)
            label = labels.get(port_key, f"Port {port}")

            port_results[port] = {"open": is_open, "label": label, "port": port}

            # HTTP check for HTTP ports
            if is_open and port in http_ports:
                http_status, http_error = self._check_http(ip, port)
                port_results[port]["http_status"] = http_status
                port_results[port]["http_error"] = http_error

                if is_open and http_status and 200 <= http_status < 400:
                    port_results[port]["status"] = "ok"
                elif is_open and http_status:
                    port_results[port]["status"] = f"http_{http_status}"
                elif is_open:
                    port_results[port]["status"] = "open-no-http"
                else:
                    port_results[port]["status"] = "closed"
            elif is_open:
                port_results[port]["status"] = "open"
            else:
                port_results[port]["status"] = "closed"

            if is_open:
                status.alive = True

        status.ports = port_results

        # Determine overall status
        if not status.alive:
            status.overall_status = "down"
        elif len(ports) > 0 and all(not pr["open"] for pr in port_results.values()):
            status.overall_status = "down"
        else:
            open_ports = [p for p in port_results.values() if p["open"]]
            if len(open_ports) == len(ports):
                status.overall_status = "healthy"
            else:
                status.overall_status = "degraded"

        # Build HTTP services summary
        for port in ports:
            if port in http_ports and port in port_results:
                pr = port_results[port]
                status.http_services[labels.get(str(port), f"Port {port}")] = {
                    "port": port,
                    "http_status": pr.get("http_status", 0),
                    "status": pr.get("status", "unknown"),
                }

        # Scan time
        scan_end = datetime.datetime.now()
        status.scan_time = (scan_end - start).total_seconds()

        return status

    def _check_port(self, ip: str, port: int, timeout: int) -> bool:
        """Check if a TCP port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_http(self, ip: str, port: int) -> tuple:
        """Check HTTP service on a port. Returns (status_code, error)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((ip, port))
            request = f"GET / HTTP/1.0\r\nHost: {ip}\r\nConnection: close\r\n\r\n"
            sock.sendall(request.encode())
            response = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass
            sock.close()

            text = response.decode("utf-8", errors="replace")
            lines = text.split("\r\n")
            status_code = 0
            if lines:
                parts = lines[0].split(" ", 2)
                if len(parts) >= 2:
                    try:
                        status_code = int(parts[1])
                    except ValueError:
                        pass
            return status_code, ""
        except Exception as exc:
            return 0, str(exc)

    async def _async_update_data(self):
        """Update all host statuses."""
        try:
            new_statuses = {}
            for host in self.hosts:
                try:
                    status = self._scan_host(host["name"], host)
                    new_statuses[host["ip"]] = status
                    _LOGGER.debug(
                        "Host %s (%s): %s (%.1fs)",
                        status.name,
                        status.ip,
                        status.overall_status,
                        status.scan_time,
                    )
                except Exception as exc:
                    _LOGGER.error("Failed to scan %s: %s", host["name"], exc)
                    new_statuses[host["ip"]] = HostStatus(
                        name=host["name"],
                        ip=host["ip"],
                        overall_status="unknown",
                        description=host.get("description", ""),
                        group=host.get("group", "default"),
                        last_scan=datetime.datetime.now().isoformat(),
                    )
            self.host_statuses = new_statuses
            return new_statuses
        except Exception as exc:
            raise UpdateFailed(f"Scan error: {exc}") from exc