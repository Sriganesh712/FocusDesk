#!/usr/bin/env python3
"""
High-Priority Wi-Fi Failover & Preemption Watchdog for STM32MP135F-DK
Priority 1: SRIGANESH_AP (Autoconnect Priority 100)
Priority 2: Moto g96 5g  (Autoconnect Priority 50)
Priority 3: BEST         (Autoconnect Priority 10)
"""

import subprocess
import time
import sys
import os

PRIO_1 = "SRIGANESH_AP"
PRIO_2 = "Moto g96 5g"
FALLBACK = "BEST"
TARGET = "8.8.8.8"

def log(msg):
    sys.stdout.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    sys.stdout.flush()

def get_nm_status():
    """Returns (connection_name, state_code, state_name)"""
    try:
        res = subprocess.run(
            ["nmcli", "-t", "-f", "GENERAL.CONNECTION,GENERAL.STATE", "dev", "show", "wlan0"],
            capture_output=True, text=True, timeout=4
        )
        conn = ""
        state = ""
        for line in res.stdout.strip().split("\n"):
            if line.startswith("GENERAL.CONNECTION:"):
                conn = line.split(":", 1)[1].strip()
            elif line.startswith("GENERAL.STATE:"):
                state = line.split(":", 1)[1].strip()
        state_code = 0
        if state:
            parts = state.split()
            if parts[0].isdigit():
                state_code = int(parts[0])
        return conn, state_code, state
    except Exception as e:
        return "", 0, str(e)

def ping_ok(target, timeout=1):
    try:
        res = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), target],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 1
        )
        return res.returncode == 0
    except Exception:
        return False

def is_prio1_visible():
    try:
        res = subprocess.run(
            ["wpa_cli", "-i", "wlan0", "scan_results"],
            capture_output=True, text=True, timeout=2
        )
        for line in res.stdout.strip().split("\n")[1:]:
            parts = line.split("\t")
            if len(parts) >= 5 and parts[4] == PRIO_1:
                return True
        return False
    except Exception:
        return False

def trigger_bg_scan():
    try:
        subprocess.run(["wpa_cli", "-i", "wlan0", "scan"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
    except Exception:
        pass

def connect_to(profile_name, wait_sec=8):
    log(f"Activating '{profile_name}' (wait {wait_sec}s)...")
    try:
        res = subprocess.run(
            ["nmcli", "--wait", str(wait_sec), "connection", "up", profile_name],
            capture_output=True, text=True, timeout=wait_sec + 3
        )
        if res.returncode == 0:
            log(f"Successfully activated '{profile_name}'.")
            return True
        else:
            err_line = (res.stderr or res.stdout or "").strip().split("\n")[0]
            log(f"Activation failed for '{profile_name}': {err_line}")
            return False
    except Exception as e:
        log(f"Error activating '{profile_name}': {e}")
        return False

def main():
    log(f"Wi-Fi Watchdog started. Prio1='{PRIO_1}', Prio2='{PRIO_2}', Fallback='{FALLBACK}'")
    fail_count = 0
    scan_counter = 0
    prio1_cooldown_until = 0

    while True:
        time.sleep(1.5)
        conn, state_code, state_desc = get_nm_status()

        # Connecting states: prepare(50), config(60), need-auth(70), ip-config(80), ip-check(90)
        # Give connection/DHCP time to finish without interrupting
        if state_code in (50, 60, 70, 80, 90):
            fail_count = 0
            continue

        # Case 1: Fully connected
        if state_code == 100:
            if conn == PRIO_1:
                # We are on Priority 1!
                if ping_ok(TARGET, timeout=1):
                    fail_count = 0
                    prio1_cooldown_until = 0
                else:
                    fail_count += 1
                    log(f"Priority 1 ping check failed ({fail_count}/2)")
                    if fail_count >= 2:
                        log(f"Priority 1 ('{PRIO_1}') lost internet. Triggering instant failover to Priority 2 ('{PRIO_2}')...")
                        prio1_cooldown_until = time.time() + 45
                        if not connect_to(PRIO_2):
                            connect_to(FALLBACK)
                        fail_count = 0
            else:
                # We are on a fallback network (e.g. Moto g96 5g or BEST)
                if not ping_ok(TARGET, timeout=1):
                    fail_count += 1
                    log(f"Fallback connection '{conn}' ping failed ({fail_count}/2)")
                    if fail_count >= 2:
                        log(f"Fallback connection unhealthy. Attempting switch to Priority 1 or Priority 2...")
                        if not connect_to(PRIO_1):
                            if not connect_to(PRIO_2):
                                connect_to(FALLBACK)
                        fail_count = 0
                else:
                    fail_count = 0

                # Preemption: check if Priority 1 has returned to range and cooldown expired
                if time.time() >= prio1_cooldown_until:
                    scan_counter += 1
                    if scan_counter >= 2:  # Every ~3-4 seconds
                        scan_counter = 0
                        trigger_bg_scan()
                        if is_prio1_visible():
                            log(f"Priority 1 ('{PRIO_1}') detected in range! Preempting back to Priority 1...")
                            if connect_to(PRIO_1):
                                fail_count = 0
                                prio1_cooldown_until = 0
                                continue

        # Case 2: Disconnected or failed state
        elif state_code in (40, 110, 120) or not conn or conn == "--":
            prio1_cooldown_until = 0
            fail_count += 1
            if fail_count >= 2:
                log(f"Interface disconnected/failed (state={state_desc}). Initiating connection in priority order...")
                if not connect_to(PRIO_1):
                    if not connect_to(PRIO_2):
                        connect_to(FALLBACK)
                fail_count = 0

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Watchdog terminated by user.")
        sys.exit(0)
