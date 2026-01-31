#!/bin/bash
set -euo pipefail

# Configuration
AGENT_VERSION="3.1.0-4967" # Latest unstable/stable version as of Jan 2026
# Check specifically for Ubuntu 22.04
USER_HOME="/home/mbi"
STAGING_DIR="$USER_HOME/setup_staging"
DOWNLOAD_URL="https://global.download.synology.com/download/Utility/ActiveBackupBusinessAgent/${AGENT_VERSION}/Linux/x86_64/Synology%20Active%20Backup%20for%20Business%20Agent-${AGENT_VERSION}-x64-deb.zip"

echo "=== Synology Active Backup for Business Agent Installer ==="
echo "Target: Ubuntu 22.04"

# 1. Install Dependencies
echo "Step 1: Installing dependencies (headers, dkms, unzip)..."
if ! dpkg -s linux-headers-$(uname -r) >/dev/null 2>&1; then
    apt-get update
    apt-get install -y linux-headers-$(uname -r) dkms make unzip
else
    echo "Dependencies appear to be installed."
fi

# 2. Download Agent
echo "Step 2: Downloading Agent v${AGENT_VERSION}..."
mkdir -p "$STAGING_DIR/synology_agent"
cd "$STAGING_DIR/synology_agent"

if [ ! -f "agent.zip" ]; then
    wget -O "agent.zip" "$DOWNLOAD_URL"
else
    echo "Installer already downloaded."
fi

# 3. Extract
echo "Step 3: Extracting..."
unzip -o agent.zip

# 4. Install
echo "Step 4: Running Installer..."
# The zip typically contains 'install.run'
chmod +x install.run
./install.run

echo "=== Installation Verification ==="
if systemctl is-active synapse-connected >/dev/null 2>&1 || systemctl is-active synology-active-backup-business-agent; then
    echo "✅ Agent Service is installed and running."
else
    echo "⚠️ Agent installed but service status is unclear. Please check."
fi

echo "=== NEXT STEPS ==="
echo "The agent is installed but NOT connected."
echo "You must connect it to your NAS using the following command:"
echo ""
echo "sudo ABB-cli -c <NAS_IP_OR_DOMAIN> <USERNAME> <PASSWORD>"
echo ""
echo "Alternatively, log in to your Synology NAS > Active Backup for Business > Physical Server > Linux, click 'Add Device' and follow the instructions."
