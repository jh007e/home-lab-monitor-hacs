"""Binary sensor entities for Home Lab Monitor."""

import logging
import datetime
from typing import Any, Dict, Optional

from homeassistant.const import EntityCategory
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from . import HomeLabMonitorCoordinator, HostStatus
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

    _attr_entity_category = EntityCategory.DIAGNOSTIC
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

    def _get_status(self) -> Optional[HostStatus]:
        """Get HostStatus dataclass for this sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._ip)

    @property
    def is_on(self) -> bool:
        """Return True if host is healthy (not down)."""
        status = self._get_status()
        if status is None:
            return False
        return status.overall_status == STATUS_HEALTHY

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        status = self._get_status()
        if status is None:
            return {}

        # Convert ports to serializable dict
        ports_dict = {}
        if status.ports:
            for port_key, port_info in status.ports.items():
                ports_dict[str(port_key)] = {
                    "open": port_info.get("open", False) if isinstance(port_info, dict) else False,
                    "label": port_info.get("label", "") if isinstance(port_info, dict) else "",
                    "status": port_info.get("status", "unknown") if isinstance(port_info, dict) else "unknown",
                }

        # Convert http_services to serializable dict
        http_dict = {}
        if status.http_services:
            for svc_name, svc_info in status.http_services.items():
                http_dict[svc_name] = {
                    "port": svc_info.get("port", 0) if isinstance(svc_info, dict) else 0,
                    "status": svc_info.get("status", "unknown") if isinstance(svc_info, dict) else "unknown",
                    "http_status": svc_info.get("http_status", 0) if isinstance(svc_info, dict) else 0,
                }

        return {
            "ip": self._ip,
            "group": self._group,
            "description": self.host_config.get("description", ""),
            "status": status.overall_status,
            "ping_ok": status.ping_ok,
            "alive": status.alive,
            "ports": ports_dict,
            "scan_time": round(status.scan_time, 2),
            "last_updated": status.last_update,
            "http_services": http_dict,
            "consecutive_failures": status.consecutive_failures,
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

    _attr_entity_category = EntityCategory.DIAGNOSTIC
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

    def _get_status(self) -> Optional[HostStatus]:
        """Get HostStatus dataclass for this sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._ip)

    @property
    def is_on(self) -> bool:
        """Return True if port is open."""
        status = self._get_status()
        if status is None:
            return False
        port_data = status.ports.get(str(self._port), {})
        if isinstance(port_data, dict):
            return port_data.get("open", False)
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        status = self._get_status()
        if status is None:
            return {}
        port_data = status.ports.get(str(self._port), {})
        return {
            "port": self._port,
            "label": self._label,
            "open": port_data.get("open", False) if isinstance(port_data, dict) else False,
            "http_status": port_data.get("http_status", 0) if isinstance(port_data, dict) else 0,
            "status": port_data.get("status", "unknown") if isinstance(port_data, dict) else "unknown",
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
