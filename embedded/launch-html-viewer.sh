#!/bin/sh
# FocusDesk & Dashboard Auto-Launcher for STM32MP135F-DK
source /etc/profile.d/weston_profile.sh
source /etc/profile.d/pulse_profile.sh

# Ensure Wayland socket is ready at boot
for i in $(seq 1 30); do
    if [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] || [ -S "/home/weston/wayland-1" ] || [ -S "/run/user/1000/wayland-0" ]; then
        break
    fi
    sleep 0.5
done

while true; do
    /usr/bin/python3 /home/weston/html_viewer.py
    sleep 1
done
