#!/usr/bin/env python3
"""
FocusDesk Sync Daemon for STM32MP135F-DK
Lightweight bidirectional synchronization daemon with SQLite WAL persistence,
Firestore REST client, and rotating atomic JSON snapshots.
Zero external library dependencies - uses Python standard library only.
"""

import sys
import os
import time
import json
import sqlite3
import signal
import glob
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

CONFIG_PATH = "/etc/focusdesk/config.json"
DB_PATH = "/var/lib/focusdesk/tasks.db"
BACKUP_DIR = "/var/lib/focusdesk/backups"
MAX_SNAPSHOTS = 7

running = True

def signal_handler(signum, frame):
    global running
    print(f"[SyncDaemon] Received signal {signum}. Shutting down cleanly...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[SyncDaemon] Error loading config: {e}")
    return {}

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def create_json_snapshot(conn):
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks;")
        rows = cursor.fetchall()
        
        tasks_list = []
        for r in rows:
            tasks_list.append({
                "id": r["id"],
                "ownerId": r["owner_id"],
                "title": r["title"],
                "description": r["description"],
                "priority": r["priority"],
                "status": r["status"],
                "category": r["category"],
                "tags": json.loads(r["tags_json"]) if r["tags_json"] else [],
                "dueAtUtc": r["due_at_utc"],
                "remindBeforeMinutes": r["remind_before_minutes"],
                "createdAt": r["created_at"],
                "updatedAt": r["updated_at"],
                "completedAt": r["completed_at"],
                "archivedAt": r["archived_at"],
                "recurrenceRule": json.loads(r["recurrence_rule_json"]) if r["recurrence_rule_json"] else None,
                "seriesId": r["series_id"],
                "occurrenceKey": r["occurrence_key"],
                "revision": r["revision"]
            })
            
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp_str}.json"
        filepath = os.path.join(BACKUP_DIR, filename)
        temp_filepath = filepath + ".tmp"
        
        payload = {
            "version": 1,
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "source": "STM32MP135 Kiosk SyncDaemon",
            "taskCount": len(tasks_list),
            "tasks": tasks_list
        }
        
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(temp_filepath, filepath)
        
        # Rotate snapshots: keep only the newest MAX_SNAPSHOTS
        existing_files = sorted(glob.glob(os.path.join(BACKUP_DIR, "snapshot_*.json")))
        if len(existing_files) > MAX_SNAPSHOTS:
            for old_file in existing_files[:-MAX_SNAPSHOTS]:
                try:
                    os.remove(old_file)
                except Exception:
                    pass
    except Exception as e:
        print(f"[SyncDaemon] Error creating snapshot: {e}")

def push_pending_operations(conn, config):
    project_id = config.get("firebase_project_id")
    api_key = config.get("firebase_web_api_key")
    owner_id = config.get("owner_id", "local-owner-focusdesk")
    
    if not project_id or not api_key:
        return 0

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sync_queue ORDER BY timestamp ASC LIMIT 20;")
    ops = cursor.fetchall()
    
    pushed = 0
    for op in ops:
        op_id = op["op_id"]
        task_id = op["task_id"]
        op_type = op["type"]
        patch = json.loads(op["patch_json"])
        
        # Build Firestore REST Document format
        fields = {}
        for k, v in patch.items():
            if v is None:
                fields[k] = {"nullValue": None}
            elif isinstance(v, str):
                fields[k] = {"stringValue": v}
            elif isinstance(v, int):
                fields[k] = {"integerValue": str(v)}
            elif isinstance(v, float):
                fields[k] = {"doubleValue": v}
            elif isinstance(v, bool):
                fields[k] = {"booleanValue": v}
            elif isinstance(v, list):
                fields[k] = {"arrayValue": {"values": [{"stringValue": str(item)} for item in v]}}
                
        doc_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/users/{owner_id}/tasks/{task_id}?key={api_key}"
        
        try:
            req_data = json.dumps({"fields": fields}).encode("utf-8")
            req = urllib.request.Request(
                doc_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="PATCH"
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                if resp.status in (200, 201):
                    cursor.execute("DELETE FROM sync_queue WHERE op_id = ?;", (op_id,))
                    conn.commit()
                    pushed += 1
        except urllib.error.HTTPError as e:
            cursor.execute(
                "UPDATE sync_queue SET retry_count = retry_count + 1, error = ? WHERE op_id = ?;",
                (f"HTTP {e.code}: {e.reason}", op_id)
            )
            conn.commit()
        except Exception as e:
            cursor.execute(
                "UPDATE sync_queue SET retry_count = retry_count + 1, error = ? WHERE op_id = ?;",
                (str(e), op_id)
            )
            conn.commit()
            
    return pushed

def pull_remote_tasks(conn, config):
    project_id = config.get("firebase_project_id")
    api_key = config.get("firebase_web_api_key")
    owner_id = config.get("owner_id", "local-owner-focusdesk")
    
    if not project_id or not api_key:
        return 0

    list_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/users/{owner_id}/tasks?key={api_key}&pageSize=100"
    
    try:
        req = urllib.request.Request(list_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            documents = data.get("documents", [])
            
            cursor = conn.cursor()
            updated_count = 0
            
            for doc in documents:
                name = doc.get("name", "")
                task_id = name.split("/")[-1]
                fields = doc.get("fields", {})
                
                # Parse Firestore fields
                title = fields.get("title", {}).get("stringValue", "Untitled")
                desc = fields.get("description", {}).get("stringValue", "")
                priority = fields.get("priority", {}).get("stringValue", "medium")
                status = fields.get("status", {}).get("stringValue", "pending")
                category = fields.get("category", {}).get("stringValue", "General")
                due_at_utc = fields.get("dueAtUtc", {}).get("stringValue", None)
                updated_at = fields.get("updatedAt", {}).get("stringValue", datetime.now(timezone.utc).isoformat())
                created_at = fields.get("createdAt", {}).get("stringValue", updated_at)
                completed_at = fields.get("completedAt", {}).get("stringValue", None)
                archived_at = fields.get("archivedAt", {}).get("stringValue", None)
                revision = int(fields.get("revision", {}).get("integerValue", "1"))
                
                cursor.execute("SELECT revision, updated_at FROM tasks WHERE id = ?;", (task_id,))
                local = cursor.fetchone()
                
                if not local:
                    # Insert remote task
                    cursor.execute("""
                    INSERT INTO tasks (
                        id, owner_id, title, description, priority, status, category,
                        tags_json, due_at_utc, remind_before_minutes, created_at,
                        updated_at, completed_at, archived_at, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '[]', ?, 15, ?, ?, ?, ?, ?);
                    """, (task_id, owner_id, title, desc, priority, status, category, due_at_utc, created_at, updated_at, completed_at, archived_at, revision))
                    updated_count += 1
                elif revision > local["revision"]:
                    # Remote has higher revision: update local
                    cursor.execute("""
                    UPDATE tasks SET
                        title = ?, description = ?, priority = ?, status = ?,
                        category = ?, due_at_utc = ?, updated_at = ?,
                        completed_at = ?, archived_at = ?, revision = ?
                    WHERE id = ?;
                    """, (title, desc, priority, status, category, due_at_utc, updated_at, completed_at, archived_at, revision, task_id))
                    updated_count += 1
                    
            if updated_count > 0:
                conn.commit()
                print(f"[SyncDaemon] Pulled {updated_count} task update(s) from cloud.")
            return updated_count
    except Exception as e:
        # Expected if offline or keys not yet configured
        return 0

def run_sync_cycle():
    config = load_config()
    conn = get_db()
    try:
        # 1. Push any pending local mutations
        pushed = push_pending_operations(conn, config)
        if pushed > 0:
            print(f"[SyncDaemon] Successfully pushed {pushed} operation(s) to cloud.")
            
        # 2. Pull remote tasks
        pull_remote_tasks(conn, config)
        
        # 3. Always maintain rotating atomic backup snapshot
        create_json_snapshot(conn)
    finally:
        conn.close()

def main():
    print("[SyncDaemon] Starting FocusDesk Sync Daemon for STM32MP135F-DK...")
    last_run = 0
    
    # Run once immediately on start
    run_sync_cycle()
    
    while running:
        config = load_config()
        interval = int(config.get("sync_interval_sec", 30))
        
        now = time.time()
        if now - last_run >= interval:
            run_sync_cycle()
            last_run = now
            
        # Sleep in small increments for responsive SIGTERM handling
        for _ in range(5):
            if not running:
                break
            time.sleep(1)

    print("[SyncDaemon] FocusDesk Sync Daemon stopped.")

if __name__ == "__main__":
    main()
