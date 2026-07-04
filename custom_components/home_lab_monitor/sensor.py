"""Sensor entities for Home Lab Monitor integration."""

import datetime
import logging
from typing import Any, Dict

from homeassistant.const import EntityCategory
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from . import HomeLabMonitorCoordinator
from .const import DOMAIN, STATUS_HEALTHY, STATUS_DEGRADED, STATUS_DOWN, STATUS_UNKNOWN

_LOGGER = logging.getLogger(__name__)


def _get_status_dict(coordinator: HomeLabMonitorCoordinator, ip: str) -> Dict[str, Any]:
    """Convert HostStatus dataclass to dict for consistent access."""
    status = coordinator.data.get(ip) if coordinator.data else None
    if status is None:
        return {}
    # HostStatus dataclass -> dict
    if hasattr(status, '__dict__'):
        return status.__dict__
    # Already a dict
    if isinstance(status, dict):
        return status
    return {}


def _get_overall_status(status) -> str:
    """Extract overall_status from HostStatus dataclass or dict."""
    if hasattr(status, 'overall_status'):
        return status.overall_status
    if isinstance(status, dict):
        return status.get("overall_status", STATUS_UNKNOWN)
    return STATUS_UNKNOWN


def _get_name(status) -> str:
    """Extract name from HostStatus dataclass or dict."""
    if hasattr(status, 'name'):
        return status.name
    if isinstance(status, dict):
        return status.get("name", "")
    return ""


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: HomeLabMonitorCoordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([HomeLabGroupSensor(coordinator)])


class HomeLabGroupSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing overall lab health."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HomeLabMonitorCoordinator):
        """Initialize group sensor."""
        super().__init__(coordinator)
        self._attr_name = "Home Lab Overall"
        self._attr_unique_id = "home_lab_monitor_overall"

    @property
    def state(self) -> str:
        """Return overall lab health state."""
        if not self.coordinator.data:
            return STATUS_UNKNOWN

        statuses = set()
        for ip, status in self.coordinator.data.items():
            statuses.add(_get_overall_status(status))

        # If any host is down, overall is down
        if STATUS_DOWN in statuses:
            return STATUS_DOWN
        # If any host is degraded, overall is degraded
        if STATUS_DEGRADED in statuses:
            return STATUS_DEGRADED
        # If all hosts are healthy, overall is healthy
        if statuses == {STATUS_HEALTHY}:
            return STATUS_HEALTHY

        return STATUS_UNKNOWN

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {
                "total_hosts": 0,
                "healthy": 0,
                "degraded": 0,
                "down": 0,
                "hosts": {},
            }

        host_summary = {}
        healthy_count = 0
        degraded_count = 0
        down_count = 0

        for ip, status in self.coordinator.data.items():
            name = _get_name(status)
            overall_status = _get_overall_status(status)
            
            host_summary[name if name else ip] = {
                "ip": ip,
                "status": overall_status,
                "last_updated": status.last_update if hasattr(status, 'last_update') else status.get("last_update", ""),
                "scan_time": status.scan_time if hasattr(status, 'scan_time') else status.get("scan_time", 0),
                "group": status.group if hasattr(status, 'group') else status.get("group", "default"),
            }

            if overall_status == STATUS_HEALTHY:
                healthy_count += 1
            elif overall_status == STATUS_DEGRADED:
                degraded_count += 1
            elif overall_status == STATUS_DOWN:
                down_count += 1

        return {
            "total_hosts": len(self.coordinator.data),
            "healthy": healthy_count,
            "degraded": degraded_count,
            "down": down_count,
            "hosts": host_summary,
            "last_scan": datetime.datetime.now().isoformat(),
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": "Home Lab Monitor Hub",
            "model": "Home Lab Monitor",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
