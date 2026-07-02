"""Config flow for Home Lab Monitor integration."""

import ipaddress
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_HOSTS,
    CONF_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _parse_labels(labels_str: str) -> Dict[str, str]:
    """Parse labels from string format."""
    labels = {}
    if not labels_str.strip():
        return labels
    for pair in labels_str.split(","):
        if ":" in pair:
            k, v = pair.split(":", 1)
            labels[k.strip()] = v.strip()
    return labels


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=3600)
        ),
        vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=30)
        ),
    }
)

HOST_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Required("ip"): str,
        vol.Required("group", default="default"): vol.In(
            ["default", "nas", "servers", "workstations", "edge", "other"]
        ),
        vol.Optional("description"): str,
        vol.Optional("ports", default="22,443"): str,
        vol.Optional("labels", default=""): str,
        vol.Optional("http_ports", default=""): str,
    }
)

GROUPS = ["default", "nas", "servers", "workstations", "edge", "other"]


class HomeLabMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Lab Monitor."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return HomeLabMonitorOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle a config flow init step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        return self.async_create_entry(
            title="Home Lab Monitor",
            data={
                CONF_INTERVAL: user_input[CONF_INTERVAL],
                CONF_TIMEOUT: user_input[CONF_TIMEOUT],
                CONF_HOSTS: [],
            },
        )


class HomeLabMonitorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Show menu for options."""
        menu_options = [
            "add_host",
            "remove_host",
            "scan_now",
            "edit_interval",
        ]
        menu_labels = {
            "add_host": "\U0001f51d Add Host",
            "remove_host": "\U0001f5d1 Remove Host",
            "scan_now": "\U0001f50d Scan Now",
            "edit_interval": "\u2699\ufe0f Edit Settings",
        }
        return self.async_show_menu(step_id="menu", menu_options=menu_labels)

    async def async_step_add_host(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Add a host through options."""
        if user_input is None:
            errors = {}
            schema = HOST_SCHEMA
            return self.async_show_form(
                step_id="add_host", data_schema=schema, errors=errors
            )

        # Validate IP
        try:
            ipaddress.ip_address(user_input["ip"])
        except ValueError:
            errors = {"ip": "invalid_ip"}
            return self.async_show_form(
                step_id="add_host", data_schema=HOST_SCHEMA, errors=errors
            )

        hosts = list(self._config_entry.data.get(CONF_HOSTS, []))
        hosts.append(
            {
                "name": user_input["name"],
                "ip": user_input["ip"],
                "group": user_input.get("group", "default"),
                "description": user_input.get("description", ""),
                "ports": [
                    int(p.strip())
                    for p in user_input["ports"].split(",")
                    if p.strip()
                ],
                "labels": _parse_labels(user_input.get("labels", "")),
                "http_ports": [
                    int(p.strip())
                    for p in user_input["http_ports"].split(",")
                    if p.strip()
                ],
            }
        )

        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={**self._config_entry.data, CONF_HOSTS: hosts},
        )
        return self.async_create_entry(
            data={}, title=f"Host {user_input['name']} added"
        )

    async def async_step_remove_host(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Remove a host through options."""
        hosts = self._config_entry.data.get(CONF_HOSTS, [])
        if user_input is None:
            host_options = [
                selector.SelectOptionDict(
                    value=h["ip"], label=f"{h['name']} ({h['ip']})"
                )
                for h in hosts
            ]
            schema = vol.Schema(
                {
                    vol.Required("ip"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=host_options, multiple=False
                        )
                    ),
                }
            )
            return self.async_show_form(
                step_id="remove_host", data_schema=schema
            )

        hosts = [h for h in hosts if h["ip"] != user_input["ip"]]
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={**self._config_entry.data, CONF_HOSTS: hosts},
        )
        return self.async_create_entry(data={}, title="Host removed")

    async def async_step_scan_now(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Scan now through options."""
        if user_input is None:
            return self.async_show_form(step_id="scan_now")

        await self.hass.services.async_call(
            DOMAIN, "scan_now", {}, blocking=True
        )
        return self.async_create_entry(data={}, title="Scan initiated")

    async def async_step_edit_interval(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Edit scan interval."""
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL,
                        default=self._config_entry.data.get(
                            CONF_INTERVAL, DEFAULT_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=10, max=3600)
                    ),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=self._config_entry.data.get(
                            CONF_TIMEOUT, DEFAULT_TIMEOUT
                        ),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=30)
                    ),
                }
            )
            return self.async_show_form(
                step_id="edit_interval", data_schema=schema
            )

        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={
                **self._config_entry.data,
                CONF_INTERVAL: user_input[CONF_INTERVAL],
                CONF_TIMEOUT: user_input[CONF_TIMEOUT],
            },
        )
        return self.async_create_entry(data={}, title="Settings updated")
