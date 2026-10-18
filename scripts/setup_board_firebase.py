import os
import json
import subprocess
import sys

ENV_PATH = r"D:\Files\FocusDesk\.env"
PLINK_PATH = r"C:\Program Files\PuTTY\plink.exe"
HOSTKEY = "SHA256:csiG0+qUBwQEy2+aYR0ZbEeZwpJDpmCH6wrLbxr39Ls"
PASSWORD = "Sriganesh@712"
CANDIDATE_HOSTS = ["root@10.50.27.58", "root@10.57.135.57", "root@10.158.208.57"]

def get_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

def update_board_config():
    env = get_env()
    proj_id = env.get("VITE_FIREBASE_PROJECT_ID", "focusdsk")
    api_key = env.get("VITE_FIREBASE_API_KEY", "")

    config_data = {
        "firebase_project_id": proj_id,
        "firebase_web_api_key": api_key,
        "owner_id": "t5eO3BwTjBXjMIaRofFmDud9nok1",
        "auth_email": "kiosk-device@focusdesk.local",
        "auth_password": "DevicePassword123!",
        "device_id": "stm32mp135-kiosk-01",
        "sync_interval_sec": 10,
        "idle_backlight_sec": 120,
        "dimmed_brightness": 1,
        "active_brightness": 10
    }

    # Save to D:\Files\FocusDesk\embedded\config.json
    local_cfg = r"D:\Files\FocusDesk\embedded\config.json"
    with open(local_cfg, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
    print("Saved local config to:", local_cfg)

    # Deploy to STM32 board via deploy_to_board.py
    deploy_script = r"D:\Files\FocusDesk\scripts\deploy_to_board.py"
    res = subprocess.run([sys.executable, deploy_script, local_cfg, "/etc/focusdesk/config.json", "0640", "root:weston"], capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)

if __name__ == "__main__":
    update_board_config()
