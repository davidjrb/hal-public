#!/bin/bash
set -e

# Configuration
REPO_DIR="$HOME/instructions"
CONFIG_DIR="$HOME/.config/whatsapp-agent"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "Applying WhatsApp Poller Configuration..."

# 1. Ensure Config Directory Exists
mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"

# 2. Check for twilio.env, prompt if missing
if [ ! -f "$CONFIG_DIR/twilio.env" ]; then
    echo "Creating twilio.env from example..."
    if [ -f "$REPO_DIR/config/twilio.env" ]; then
        cp "$REPO_DIR/config/twilio.env" "$CONFIG_DIR/twilio.env"
    else
        cp "$REPO_DIR/config/twilio.env.example" "$CONFIG_DIR/twilio.env"
        echo "WARNING: Created twilio.env from example. You must edit $CONFIG_DIR/twilio.env with real credentials."
    fi
    chmod 600 "$CONFIG_DIR/twilio.env"
else
    echo "twilio.env already exists, skipping."
fi

# 3. Install Python Dependencies
echo "Installing Python dependencies..."
cd "$REPO_DIR/whatsapp"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
./.venv/bin/pip install -r requirements.txt

# 4. Install Systemd Service
echo "Installing systemd service..."
mkdir -p "$SYSTEMD_DIR"
cp "$REPO_DIR/systemd/whatsapp-poller.service" "$SYSTEMD_DIR/"
systemctl --user daemon-reload

# 5. Enable and Start Service
echo "Enabling and starting service..."
systemctl --user enable whatsapp-poller.service
systemctl --user restart whatsapp-poller.service

# 6. Enable Linger
echo "Enabling linger for user $(whoami)..."
loginctl enable-linger $(whoami)

echo "Done! Check status with: systemctl --user status whatsapp-poller.service"
