#!/bin/bash

# Home Lab Monitor - Installation Script
# This script helps you install the integration on your Home Assistant system

HA_CONFIG_DIR="/config"
CUSTOM_COMPONENTS_DIR="$HA_CONFIG_DIR/custom_components/home_lab_monitor"
WWW_DIR="$HA_CONFIG_DIR/www"
LOVELACE_DIR="$HA_CONFIG_DIR/lovelace"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Home Lab Monitor - Installation Script${NC}"
echo "========================================"
echo ""

# Check if running on Home Assistant system
if [ ! -d "$HA_CONFIG_DIR" ]; then
    echo -e "${RED}Error: Home Assistant config directory not found at $HA_CONFIG_DIR${NC}"
    echo "Please run this script on your Home Assistant system"
    exit 1
fi

# Create custom_components directory if it doesn't exist
echo -e "${YELLOW}Installing Home Lab Monitor integration...${NC}"
mkdir -p "$CUSTOM_COMPONENTS_DIR"
mkdir -p "$WWW_DIR"
mkdir -p "$LOVELACE_DIR"

# Copy integration files
echo -e "Copying integration files to $CUSTOM_COMPONENTS_DIR..."
cp -f /opt/data/home_lab_monitor_integration/*.py "$CUSTOM_COMPONENTS_DIR/"
cp -f /opt/data/home_lab_monitor_integration/*.json "$CUSTOM_COMPONENTS_DIR/"
cp -f /opt/data/home_lab_monitor_integration/*.yaml "$CUSTOM_COMPONENTS_DIR/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Integration files copied successfully${NC}"
else
    echo -e "${RED}✗ Failed to copy integration files${NC}"
    exit 1
fi

# Copy dashboard files
echo -e "Copying dashboard files..."
cp -f /opt/data/home_lab_monitor_integration/dashboard.html "$WWW_DIR/"
cp -f /opt/data/home_lab_monitor_integration/lovelace_dashboard.yaml "$LOVELACE_DIR/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dashboard files copied successfully${NC}"
else
    echo -e "${RED}✗ Failed to copy dashboard files${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Installation Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Restart Home Assistant"
echo "2. Go to Settings > Devices & Services > Add Integration"
echo "3. Search for 'Home Lab Monitor' and follow the setup wizard"
echo "4. Add your hosts using the UI or the add_host service"
echo "5. Import the dashboard: Settings > Dashboards > + Import Dashboard"
echo ""
echo "Dashboard URL: http://your-ha-ip:8123/local/home-lab-monitor.html"
echo ""
echo "For manual configuration, add this to configuration.yaml:"
echo "home_lab_monitor:"
echo "  interval: 60"
echo "  timeout: 3"
echo "  hosts:"
echo "    # Your hosts here"
echo ""
