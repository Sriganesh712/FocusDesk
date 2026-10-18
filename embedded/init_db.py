import json
import sqlite3
import os
import datetime

CONFIG_PATH = "/etc/focusdesk/config.json"
DB_PATH = "/var/lib/focusdesk/tasks.db"

default_config = {
    "firebase_project_id": "focusdesk-embedded",
    "firebase_web_api_key": "",
    "owner_id": "local-owner-focusdesk",
    "device_id": "stm32mp135-kiosk-01",
    "sync_interval_sec": 30,
    "idle_backlight_sec": 120,
    "dimmed_brightness": 1,
    "active_brightness": 10
}

# Write config if not exists
if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        json.dump(default_config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o640)
    print("Created config.json")
else:
    print("config.json already exists")

# Initialize SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Enable WAL mode for high concurrency
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    category TEXT DEFAULT 'General',
    tags_json TEXT DEFAULT '[]',
    due_at_utc TEXT,
    remind_before_minutes INTEGER DEFAULT 15,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    archived_at TEXT,
    recurrence_rule_json TEXT,
    series_id TEXT,
    occurrence_key TEXT,
    revision INTEGER NOT NULL DEFAULT 1
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sync_queue (
    op_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    type TEXT NOT NULL,
    patch_json TEXT NOT NULL,
    base_revision INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
""")

# Check task count
cursor.execute("SELECT COUNT(*) FROM tasks;")
count = cursor.fetchone()[0]

if count == 0:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    today_due = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).isoformat()
    tomorrow_due = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()
    
    seed_tasks = [
        (
            "task-stm32-01",
            "local-owner-focusdesk",
            "Verify STM32MP135F-DK Weston LCD",
            "Ensure 480x272 native Wayland GTK3 SHM renders at 60 FPS",
            "critical",
            "completed",
            "Embedded",
            json.dumps(["stm32", "wayland", "lcd"]),
            today_due,
            15,
            now_iso,
            now_iso,
            now_iso,
            None,
            None,
            None,
            None,
            1
        ),
        (
            "task-stm32-02",
            "local-owner-focusdesk",
            "Test Goodix Touchscreen Input",
            "Check touch event coordinates on 480x272 panel",
            "high",
            "pending",
            "Embedded",
            json.dumps(["touch", "goodix"]),
            today_due,
            15,
            now_iso,
            now_iso,
            None,
            None,
            None,
            None,
            None,
            1
        ),
        (
            "task-stm32-03",
            "local-owner-focusdesk",
            "Two-Way Cloud Sync Engine",
            "Verify HTTPS REST sync daemon and SQLite WAL persistence",
            "high",
            "pending",
            "Sync",
            json.dumps(["firebase", "rest", "sqlite"]),
            tomorrow_due,
            15,
            now_iso,
            now_iso,
            None,
            None,
            None,
            None,
            None,
            1
        ),
        (
            "task-stm32-04",
            "local-owner-focusdesk",
            "Deploy React Web App to Vercel",
            "Test offline PWA, IndexedDB storage, and conflict resolution",
            "medium",
            "pending",
            "Web",
            json.dumps(["react", "vite", "pwa"]),
            tomorrow_due,
            30,
            now_iso,
            now_iso,
            None,
            None,
            None,
            None,
            None,
            1
        ),
    ]

    cursor.executemany("""
    INSERT INTO tasks (
        id, owner_id, title, description, priority, status, category,
        tags_json, due_at_utc, remind_before_minutes, created_at,
        updated_at, completed_at, archived_at, recurrence_rule_json,
        series_id, occurrence_key, revision
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, seed_tasks)
    conn.commit()
    print(f"Seeded {len(seed_tasks)} initial tasks.")
else:
    print(f"Database already contains {count} tasks.")

conn.close()
