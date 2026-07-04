"""Binary sensor entities for Home Lab Monitor."""

import logging
import datetime
from typing import Any, Dict

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from . import HomeLabMonitorCoordinator
from .const import DOMAIN, STATUS_HEALTHY, STATUS_DEGRADED, STATUS_DOWN, STATUS_UNKNOWN

_LOGGER = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Simple slugify."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: HomeLabMonitorCoordinator = hass.data[DOMAIN]["coordinator"]
    hosts = coordinator.hosts

    entities = []
    for host in hosts:
        entities.append(HomeLabHostSensor(coordinator, host))
        for port in host.get("ports", []):
            port_key = str(port)
            label = host.get("labels", {}).get(port_key, f"Port {port}")
            entities.append(HomeLabPortSensor(coordinator, host, port, label))

    async_add_entities(entities, update_before_add=True)


class HomeLabHostSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for overall host health."""

    _attr_entity_category = "diagnostic"
    _attr_has_entity_name = True

    def __init__(self, coordinator: HomeLabMonitorCoordinator, host_config: dict):
        """Initialize sensor."""
        super().__init__(coordinator)
        self.host_config = host_config
        self._ip = host_config["ip"]
        self._name = host_config["name"]
        self._group = host_config.get("group", "default")

        self._attr_name = f"{self._name} Status"
        self._attr_unique_id = f"{_slugify(self._name)}_status"

    @property
    def is_on(self) -> bool:
        """Return True if host is healthy (not down)."""
        if not self.coordinator.data:
            return False
        status_data = self.coordinator.data.get(self._ip, {})
        return status_data.get("overall_status") == STATUS_HEALTHY

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        status_data = self.coordinator.data.get(self._ip, {})
        return {
            "ip": self._ip,
            "group": self._group,
            "description": self.host_config.get("description", ""),
            "status": status_data.get("overall_status", STATUS_UNKNOWN),
            "ping_ok": status_data.get("ping_ok", False),
            "ports": {str(k): v.get("status", "unknown") for k, v in status_data.get("ports", {}).items()},
            "scan_time": round(status_data.get("scan_time", 0), 2),
            "last_updated": status_data.get("last_updated", ""),
            "http_services": status_data.get("http_services", {}),
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._name,
            "model": f"Host ({self._ip})",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class HomeLabPortSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for individual port status."""

    _attr_entity_category = "diagnostic"
    _attr_has_entity_name = True

    def __init__(self, coordinator: HomeLabMonitorCoordinator, host_config: dict, port: int, label: str):
        """Initialize port sensor."""
        super().__init__(coordinator)
        self.host_config = host_config
        self._ip = host_config["ip"]
        self._name = host_config["name"]
        self._port = port
        self._label = label

        self._attr_name = f"{self._label} Port"
        self._attr_unique_id = f"{_slugify(self._name)}_port_{port}"

    @property
    def is_on(self) -> bool:
        """Return True if port is open."""
        if not self.coordinator.data:
            return False
        status_data = self.coordinator.data.get(self._ip, {})
        ports = status_data.get("ports", {})
        port_data = ports.get(str(self._port), {})
        return port_data.get("open", False)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        status_data = self.coordinator.data.get(self._ip, {})
        ports = status_data.get("ports", {})
        port_data = ports.get(str(self._port), {})
        return {
            "port": self._port,
            "label": self._label,
            "open": port_data.get("open", False),
            "http_status": port_data.get("http_status", 0),
            "status": port_data.get("status", "unknown"),
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": f"{self._name} - {self._label}",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
