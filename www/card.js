/* Home Lab Monitor Custom Lovelace Card - v1.0.2 */
(() => {
  "use strict";

  class HomeLabMonitorCard extends HTMLElement {
    constructor() {
      super();
      this._config = {};
      this._hosts = {};
      this._overallStatus = "unknown";
      this._totalHosts = 0;
      this._healthy = 0;
      this._degraded = 0;
      this._down = 0;
      this._refreshTimer = null;
      this._hass = null;
    }

    setConfig(config) {
      if (!config) {
        throw new Error("Home Lab Monitor: Configuration is required");
      }
      this._config = {
        title: "Home Lab Monitor",
        entity_id: "sensor.home_lab_monitor_overall",
        show_status: true,
        show_last_update: true,
        show_scan_time: false,
        show_group: true,
        show_ip: false,
        show_ports: true,
        show_http: true,
        show_latency: true,
        group_by: "name",
        max_groups: 0,
        collapsed: false,
        theme_mode: "auto",
        card_type: "cards",
        refresh_interval: 60000,
        ...config
      };
    }

    connectedCallback() {
      this._updateCard();
      if (this._config.refresh_interval > 0) {
        this._refreshTimer = setInterval(() => this._updateCard(), this._config.refresh_interval);
      }
    }

    disconnectedCallback() {
      if (this._refreshTimer) {
        clearInterval(this._refreshTimer);
      }
    }

    set hass(hass) {
      this._hass = hass;
      this._updateCard();
    }

    getCardSize() {
      return 2;
    }

    static getStubConfig() {
      return {
        title: "Home Lab Monitor",
        entity_id: "sensor.home_lab_monitor_overall",
        show_status: true,
        show_last_update: true,
        show_scan_time: false,
        show_group: true,
        show_ip: false,
        show_ports: true,
        show_http: true,
        show_latency: true,
        group_by: "name",
        max_groups: 0,
        collapsed: false,
        theme_mode: "auto",
        card_type: "cards",
        refresh_interval: 60000,
      };
    }

    _updateCard() {
      const hass = this._hass;
      if (!hass || !hass.states) return;

      const entity = hass.states[this._config.entity_id];
      if (!entity) return;

      const attrs = entity.attributes || {};
      this._hosts = attrs.hosts || {};
      this._overallStatus = entity.state || "unknown";
      this._totalHosts = attrs.total_hosts || 0;
      this._healthy = attrs.healthy || 0;
      this._degraded = attrs.degraded || 0;
      this._down = attrs.down || 0;

      this._render();
    }

    _render() {
      const config = this._config;
      const themeMode = config.theme_mode || "auto";
      const currentTheme = themeMode === "auto" 
        ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
        : themeMode;

      const card = document.createElement("ha-card");
      card.type = "basic";
      
      // Header
      const header = document.createElement("div");
      header.className = "card-header";
      header.innerHTML = `
        <h1>${config.title}</h1>
        ${config.show_status ? this._renderStatusSummary() : ""}
      `;
      
      // Body
      const body = document.createElement("div");
      body.className = `card-body ${currentTheme}`;
      
      if (config.card_type === "cards") {
        this._renderCards(body);
      } else if (config.card_type === "glance") {
        this._renderGlance(body);
      } else if (config.card_type === "table") {
        this._renderTable(body);
      }
      
      // Footer
      const footer = document.createElement("div");
      footer.className = "card-footer";
      footer.innerHTML = `
        <span>Last scan: ${new Date().toLocaleTimeString()}</span>
        <span>${this._totalHosts} hosts</span>
      `;
      
      card.appendChild(header);
      card.appendChild(body);
      card.appendChild(footer);
      
      // Clear existing content
      while (this.firstChild) {
        this.removeChild(this.firstChild);
      }
      this.appendChild(card);
    }

    _renderStatusSummary() {
      return `
        <div class="status-summary">
          <span class="status-item healthy">● ${this._healthy}</span>
          <span class="status-item degraded">● ${this._degraded}</span>
          <span class="status-item down">● ${this._down}</span>
          <span class="status-item total">${this._totalHosts} total</span>
        </div>
      `;
    }

    _renderCards(body) {
      const config = this._config;
      const hostsArray = Object.entries(this._hosts).map(([ip, host]) => ({ ip, ...host }));
      hostsArray.sort((a, b) => (a.name || a.ip).localeCompare(b.name || b.ip));

      const grid = document.createElement("div");
      grid.className = "hosts-grid";

      hostsArray.forEach(host => {
        const card = this._createHostCard(host);
        grid.appendChild(card);
      });

      body.appendChild(grid);
    }

    _createHostCard(host) {
      const config = this._config;
      const card = document.createElement("div");
      card.className = `host-card status-${host.overall_status || "unknown"}`;

      const hostName = host.name || host.ip;
      const statusIcon = this._getStatusIcon(host.overall_status);
      const statusText = this._getStatusText(host.overall_status);

      let content = `
        <div class="host-header">
          <span class="host-name">${hostName}</span>
          <span class="status-badge ${host.overall_status || "unknown"}">${statusIcon} ${statusText}</span>
        </div>
      `;

      if (config.show_ip && host.ip) {
        content += `<div class="host-ip">${host.ip}</div>`;
      }

      if (config.show_group && host.group) {
        content += `<div class="host-group">${host.group}</div>`;
      }

      if (config.show_ports && host.ports) {
        content += `<div class="host-ports">`;
        Object.entries(host.ports).forEach(([port, status]) => {
          const statusClass = status === "open" ? "open" : status === "closed" ? "closed" : "unknown";
          content += `<span class="port-badge ${statusClass}">${port}: ${status}</span>`;
        });
        content += `</div>`;
      }

      if (config.show_http && host.http) {
        content += `<div class="host-http">HTTP: ${host.http.status_code || "N/A"} - ${host.http.status_text || "N/A"}</div>`;
      }

      if (config.show_latency && host.latency !== undefined) {
        content += `<div class="host-latency">Latency: ${host.latency}ms</div>`;
      }

      if (config.show_scan_time && host.scan_time) {
        content += `<div class="host-scan-time">Scan: ${host.scan_time}ms</div>`;
      }

      if (config.show_last_update && host.last_update) {
        content += `<div class="host-last-update">Last: ${new Date(host.last_update).toLocaleTimeString()}</div>`;
      }

      card.innerHTML = content;
      return card;
    }

    _renderGlance(body) {
      const hostsArray = Object.entries(this._hosts).map(([ip, host]) => ({ ip, ...host }));
      hostsArray.sort((a, b) => (a.name || a.ip).localeCompare(b.name || b.ip));

      const glance = document.createElement("div");
      glance.className = "glance-view";

      hostsArray.forEach(host => {
        const statusIcon = this._getStatusIcon(host.overall_status);
        const hostName = host.name || host.ip;
        const statusText = this._getStatusText(host.overall_status);

        const item = document.createElement("div");
        item.className = `glance-item status-${host.overall_status || "unknown"}`;
        item.innerHTML = `
          <span class="status-icon">${statusIcon}</span>
          <span class="host-name">${hostName}</span>
          <span class="status-text">${statusText}</span>
        `;
        glance.appendChild(item);
      });

      body.appendChild(glance);
    }

    _renderTable(body) {
      const config = this._config;
      const table = document.createElement("table");
      table.className = "hosts-table";

      // Header
      const thead = document.createElement("thead");
      thead.innerHTML = `
        <tr>
          <th>Host</th>
          <th>Status</th>
          ${config.show_ip ? "<th>IP</th>" : ""}
          ${config.show_group ? "<th>Group</th>" : ""}
          ${config.show_ports ? "<th>Ports</th>" : ""}
          ${config.show_http ? "<th>HTTP</th>" : ""}
          ${config.show_latency ? "<th>Latency</th>" : ""}
          ${config.show_scan_time ? "<th>Scan</th>" : ""}
          ${config.show_last_update ? "<th>Last</th>" : ""}
        </tr>
      `;
      table.appendChild(thead);

      // Body
      const tbody = document.createElement("tbody");
      const hostsArray = Object.entries(this._hosts).map(([ip, host]) => ({ ip, ...host }));
      hostsArray.sort((a, b) => (a.name || a.ip).localeCompare(b.name || b.ip));

      hostsArray.forEach(host => {
        const tr = document.createElement("tr");
        tr.className = `status-${host.overall_status || "unknown"}`;

        const hostName = host.name || host.ip;
        const statusText = this._getStatusText(host.overall_status);

        tr.innerHTML = `
          <td>${hostName}</td>
          <td><span class="status-badge ${host.overall_status || "unknown"}">${statusText}</span></td>
          ${config.show_ip ? `<td>${host.ip}</td>` : ""}
          ${config.show_group ? `<td>${host.group || "-"}</td>` : ""}
          ${config.show_ports ? `<td>${this._portsToString(host.ports)}</td>` : ""}
          ${config.show_http ? `<td>${host.http ? `${host.http.status_code} - ${host.http.status_text}` : "-"}</td>` : ""}
          ${config.show_latency ? `<td>${host.latency !== undefined ? `${host.latency}ms` : "-"}</td>` : ""}
          ${config.show_scan_time ? `<td>${host.scan_time ? `${host.scan_time}ms` : "-"}</td>` : ""}
          ${config.show_last_update ? `<td>${host.last_update ? new Date(host.last_update).toLocaleTimeString() : "-"}</td>` : ""}
        `;
        tbody.appendChild(tr);
      });

      table.appendChild(tbody);
      body.appendChild(table);
    }

    _getStatusIcon(status) {
      switch (status) {
        case "healthy": return "✓";
        case "degraded": return "⚠";
        case "down": return "✗";
        default: return "?";
      }
    }

    _getStatusText(status) {
      switch (status) {
        case "healthy": return "Healthy";
        case "degraded": return "Degraded";
        case "down": return "Down";
        default: return "Unknown";
      }
    }

    _portsToString(ports) {
      if (!ports) return "-";
      const open = Object.entries(ports).filter(([_, status]) => status === "open").length;
      const total = Object.keys(ports).length;
      return `${open}/${total}`;
    }
  }

  // Define the custom element
  customElements.define("home-lab-monitor-card", HomeLabMonitorCard);

  // Register with Home Assistant Lovelace
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "home-lab-monitor-card",
    name: "Home Lab Monitor",
    description: "A custom card for Home Lab Monitor integration",
    preview: false,
    documentationURL: "https://github.com/jh007e/home-lab-monitor-hacs",
  });
})();
