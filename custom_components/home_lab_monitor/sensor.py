"""Sensor entities for Home Lab Monitor integration."""

import datetime
import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
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
    """Set up sensor entities."""
    coordinator: HomeLabMonitorCoordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([HomeLabGroupSensor(coordinator)])


class HomeLabGroupSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing overall lab health."""

    _attr_has_entity_name = True
    _attr_entity_category = "diagnostic"

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
            statuses.add(status.get("overall_status", STATUS_UNKNOWN))

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
            host_summary[status.get("name", ip)] = {
                "ip": ip,
                "status": status.get("overall_status", STATUS_UNKNOWN),
                "last_updated": status.get("last_update", ""),
                "scan_time": status.get("scan_time", 0),
                "group": status.get("group", "default"),
            }

            if status.get("overall_status") == STATUS_HEALTHY:
                healthy_count += 1
            elif status.get("overall_status") == STATUS_DEGRADED:
                degraded_count += 1
            elif status.get("overall_status") == STATUS_DOWN:
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
            "config_entry_id": self.hass.data[DOMAIN].get("config_entry_id"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
