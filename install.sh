#!/usr/bin/env bash
#
# install.sh — one-shot setup for openaiy: a push-to-talk voice assistant for
# the Google AIY Voice Kit v1 (Voice HAT) on stock 64-bit Raspberry Pi OS.
#
# Everything runs on OpenAI, so all you need is one OpenAI API key. The script
# installs dependencies, enables the Voice HAT sound card, stores your key, and
# registers a systemd service so the assistant is ready at every boot:
# power on, wait for it to boot, press the button, talk.
#
# Usage (run from inside the repo directory):
#     sudo ./install.sh
#
set -euo pipefail

SERVICE_NAME="openaiy"
OVERLAY_LINE="dtoverlay=googlevoicehat-soundcard"

# --- must be root (for apt, boot config, systemd) -------------------------- #
if [ "${EUID}" -ne 0 ]; then
  echo "Please run with sudo:  sudo ./install.sh" >&2
  exit 1
fi

# --- figure out who and where ---------------------------------------------- #
TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo root)}"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
ENV_FILE="$APP_DIR/openaiy.env"
PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "==> Installing for user '$TARGET_USER'"
echo "==> App directory:   $APP_DIR"

# --- system packages ------------------------------------------------------- #
echo "==> Installing system packages..."
apt-get update
apt-get install -y python3-venv python3-gpiozero python3-lgpio alsa-utils

# --- make sure the user can reach GPIO + audio ----------------------------- #
usermod -aG gpio,audio "$TARGET_USER" || true

# --- enable the Voice HAT sound card --------------------------------------- #
if [ -f /boot/firmware/config.txt ]; then
  CONFIG_TXT=/boot/firmware/config.txt
elif [ -f /boot/config.txt ]; then
  CONFIG_TXT=/boot/config.txt
else
  CONFIG_TXT=""
  echo "!! Could not find config.txt. Enable the overlay manually, then reboot:" >&2
  echo "   $OVERLAY_LINE" >&2
fi

REBOOT_NEEDED=0
if [ -n "$CONFIG_TXT" ]; then
  if grep -qxF "$OVERLAY_LINE" "$CONFIG_TXT"; then
    echo "==> Voice HAT overlay already enabled in $CONFIG_TXT"
  else
    echo "==> Enabling Voice HAT overlay in $CONFIG_TXT"
    printf '\n# AIY Voice HAT (added by openaiy install.sh)\n%s\n' "$OVERLAY_LINE" >> "$CONFIG_TXT"
    REBOOT_NEEDED=1
  fi
fi

# --- python environment ---------------------------------------------------- #
echo "==> Creating virtual environment (with access to system gpiozero/lgpio)..."
sudo -u "$TARGET_USER" python3 -m venv --system-site-packages "$VENV_DIR"
echo "==> Installing Python packages..."
sudo -u "$TARGET_USER" "$PIP" install --upgrade pip
sudo -u "$TARGET_USER" "$PIP" install --upgrade pyyaml requests openai

# --- OpenAI API key -------------------------------------------------------- #
existing_openai="$(grep -oP '^OPENAI_API_KEY=\K.+' "$ENV_FILE" 2>/dev/null || true)"
if [ -n "$existing_openai" ] && [ "$existing_openai" != "REPLACE_WITH_YOUR_KEY" ]; then
  echo "==> Reusing existing OpenAI key in $ENV_FILE"
else
  echo
  read -rsp "Enter your OpenAI API key (input hidden): " OPENAI_KEY; echo
  if [ -z "$OPENAI_KEY" ]; then
    echo "!! No key entered — writing a placeholder. Edit $ENV_FILE before first use." >&2
    OPENAI_KEY="REPLACE_WITH_YOUR_KEY"
  fi
  printf 'OPENAI_API_KEY=%s\n' "$OPENAI_KEY" > "$ENV_FILE"
  chown "$TARGET_USER":"$TARGET_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "==> Saved key to $ENV_FILE (permissions 600)"
fi

# --- systemd service ------------------------------------------------------- #
echo "==> Writing systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<UNIT
[Unit]
Description=openaiy push-to-talk voice assistant
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$TARGET_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$PY $APP_DIR/assistant.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

# --- done ------------------------------------------------------------------ #
echo
echo "============================================================"
echo " Install complete."
echo
if [ "$REBOOT_NEEDED" -eq 1 ]; then
  echo " The Voice HAT sound card was just enabled, so a reboot is"
  echo " required. After it reboots, the assistant starts on its own."
  echo
  echo "     sudo reboot"
else
  echo " Start it now (it also auto-starts on every boot):"
  echo
  echo "     sudo systemctl start ${SERVICE_NAME}"
fi
echo
echo " Handy commands:"
echo "     systemctl status ${SERVICE_NAME}        # running?"
echo "     journalctl -u ${SERVICE_NAME} -f        # live logs / transcripts"
echo "     sudo systemctl restart ${SERVICE_NAME}"
echo
echo " If audio doesn't work, run 'arecord -l' to confirm the card name and"
echo " update record_device / play_device in config.yaml to match."
echo "============================================================"
