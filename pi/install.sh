#!/bin/bash
# Spotlight door printer - one-time setup for a Raspberry Pi (Raspberry Pi OS Lite, 64-bit).
# Run as the normal user (not root):  bash install.sh
set -e
RAW=https://raw.githubusercontent.com/ClintJaxon/spotlight-admin/main/pi
DIR=$HOME/spotlight-print
echo "== 1/6 Installing system packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libusb-1.0-0 fonts-dejavu-core curl
echo "== 2/6 Installing the printer software"
mkdir -p "$DIR"
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install --upgrade pip
"$DIR/venv/bin/pip" install brother_ql
curl -fsSL "$RAW/spotlight_print.py" -o "$DIR/spotlight_print.py"
echo "== 3/6 Letting the Pi talk to the Brother over USB"
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", MODE="0666"' | sudo tee /etc/udev/rules.d/99-brother-ql.rules >/dev/null
sudo udevadm control --reload-rules && sudo udevadm trigger
echo "== 4/6 Printer login"
ENVF=$HOME/.spotlight-print.env
if [ ! -f "$ENVF" ]; then
  read -r -p "Printer login email (the one Clint invited for the door printer): " PE
  read -r -s -p "Printer login password: " PP; echo
  printf 'PRINT_EMAIL=%s\nPRINT_PASSWORD=%s\nROTATE=0\n' "$PE" "$PP" > "$ENVF"
  chmod 600 "$ENVF"
fi
echo "== 5/6 Starting it automatically on power-up"
sudo tee /etc/systemd/system/spotlight-print.service >/dev/null <<UNIT
[Unit]
Description=Spotlight door label printer
After=network-online.target
Wants=network-online.target
[Service]
User=$USER
ExecStart=$DIR/venv/bin/python $DIR/spotlight_print.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable spotlight-print
echo "== 6/6 Done. Turn the Brother on (Editor Lite light OFF), then print a test label:"
echo "   $DIR/venv/bin/python $DIR/spotlight_print.py --test"
echo "Then start the watcher:  sudo systemctl start spotlight-print"
