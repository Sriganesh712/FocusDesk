#!/usr/bin/env python3
"""
FocusDesk Sync Daemon for STM32MP135F-DK
Lightweight bidirectional synchronization daemon with SQLite WAL persistence,
authenticated Firebase Firestore REST client, token caching/refresh,
and rotating atomic JSON snapshots.
Zero external library dependencies - Python standard library only.
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
AUTH_STATE_PATH = "/var/lib/focusdesk/auth_state.json"
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

def get_auth_token(config):
    """
    Acquire or refresh a valid Firebase ID token using cached tokens,
    refresh token exchange, or email/password sign-in.
    """
    api_key = config.get("firebase_web_api_key")
    email = config.get("auth_email")
    password = config.get("auth_password")
    
    if not api_key:
        return None, None

    now = time.time()
    state = {}
    if os.path.exists(AUTH_STATE_PATH):
        try:
            with open(AUTH_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    id_token = state.get("id_token")
    refresh_token = state.get("refresh_token")
    expires_at = state.get("expires_at", 0)
    user_id = state.get("user_id")

    # If existing ID token is valid for at least 5 more minutes, use it
    if id_token and (expires_at - now) > 300:
        return id_token, user_id

    # Try refreshing ID token via securetoken API
    if refresh_token:
        try:
            token_url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
            ref_data = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }).encode("utf-8")
            req = urllib.request.Request(
                token_url,
                data=ref_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                ref_res = json.loads(resp.read().decode("utf-8"))
                new_id_token = ref_res.get("id_token")
                new_refresh_token = ref_res.get("refresh_token", refresh_token)
                expires_in = int(ref_res.get("expires_in", "3600"))
                user_id = ref_res.get("user_id", user_id)

                state = {
                    "id_token": new_id_token,
                    "refresh_token": new_refresh_token,
                    "expires_at": now + expires_in,
                    "user_id": user_id
                }
                with open(AUTH_STATE_PATH, "w", encoding="utf-8") as f:
                    json.dump(state, f)
                return new_id_token, user_id
        except Exception as e:
            print(f"[SyncDaemon] Token refresh failed: {e}. Will attempt sign-in.")

    # Authenticate via email & password
    if email and password:
        try:
            login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            payload = json.dumps({
                "email": email,
                "password": password,
                "returnSecureToken": True
            }).encode("utf-8")
            req = urllib.request.Request(
                login_url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                login_res = json.loads(resp.read().decode("utf-8"))
                new_id_token = login_res.get("idToken")
                new_refresh_token = login_res.get("refreshToken")
                expires_in = int(login_res.get("expiresIn", "3600"))
                user_id = login_res.get("localId")

                state = {
                    "id_token": new_id_token,
                    "refresh_token": new_refresh_token,
                    "expires_at": now + expires_in,
                    "user_id": user_id
                }
                with open(AUTH_STATE_PATH, "w", encoding="utf-8") as f:
                    json.dump(state, f)
                print(f"[SyncDaemon] Authenticated successfully as {email} ({user_id})")
                return new_id_token, user_id
        except Exception as e:
            print(f"[SyncDaemon] Sign-in failed: {e}")

    return None, None

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

def to_firestore_fields(data_dict):
    fields = {}
    for k, v in data_dict.items():
        if v is None:
            fields[k] = {"nullValue": None}
        elif isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        elif isinstance(v, float):
            fields[k] = {"doubleValue": v}
        elif isinstance(v, list):
            fields[k] = {"arrayValue": {"values": [{"stringValue": str(item)} for item in v]}}
    return fields

def push_pending_operations(conn, config, id_token, auth_uid):
    project_id = config.get("firebase_project_id")
    owner_id = config.get("owner_id") or auth_uid
    
    if not project_id or not id_token or not owner_id:
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
        
        # Fetch current full local task row if available
        cursor.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,))
        task_row = cursor.fetchone()
        
        # Build field paths for updateMask
        field_paths = list(patch.keys())
        query_mask = "&".join([f"updateMask.fieldPaths={k}" for k in field_paths])
        
        patch_fields = to_firestore_fields(patch)
        patch_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/users/{owner_id}/tasks/{task_id}?{query_mask}"
        
        success = False
        try:
            req_data = json.dumps({"fields": patch_fields}).encode("utf-8")
            req = urllib.request.Request(
                patch_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {id_token}"
                },
                method="PATCH"
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                if resp.status in (200, 201):
                    cursor.execute("DELETE FROM sync_queue WHERE op_id = ?;", (op_id,))
                    conn.commit()
                    pushed += 1
                    success = True
        except urllib.error.HTTPError as e:
            # If 403 or 404 and we have full local task row, document may not exist in cloud yet.
            # Perform full document upsert!
            if task_row:
                try:
                    full_task_dict = {
                        "id": task_row["id"],
                        "ownerId": owner_id,
                        "title": task_row["title"],
                        "description": task_row["description"] or "",
                        "priority": task_row["priority"],
                        "status": task_row["status"],
                        "category": task_row["category"] or "General",
                        "createdAt": task_row["created_at"],
                        "updatedAt": task_row["updated_at"],
                        "completedAt": task_row["completed_at"],
                        "archivedAt": task_row["archived_at"],
                        "dueAtUtc": task_row["due_at_utc"],
                        "remindBeforeMinutes": task_row["remind_before_minutes"],
                        "revision": task_row["revision"]
                    }
                    upsert_fields = to_firestore_fields(full_task_dict)
                    upsert_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/users/{owner_id}/tasks/{task_id}"
                    upsert_req = urllib.request.Request(
                        upsert_url,
                        data=json.dumps({"fields": upsert_fields}).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {id_token}"
                        },
                        method="PATCH"
                    )
                    with urllib.request.urlopen(upsert_req, timeout=8.0) as uresp:
                        if uresp.status in (200, 201):
                            cursor.execute("DELETE FROM sync_queue WHERE op_id = ?;", (op_id,))
                            conn.commit()
                            pushed += 1
                            success = True
                except Exception as ex2:
                    cursor.execute(
                        "UPDATE sync_queue SET retry_count = retry_count + 1, error = ? WHERE op_id = ?;",
                        (f"Upsert failed: {ex2}", op_id)
                    )
                    conn.commit()
            if not success:
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

def pull_remote_tasks(conn, config, id_token, auth_uid):
    project_id = config.get("firebase_project_id")
    owner_id = config.get("owner_id") or auth_uid
    
    if not project_id or not id_token or not owner_id:
        return 0

    list_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/users/{owner_id}/tasks?pageSize=100"
    
    try:
        req = urllib.request.Request(
            list_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {id_token}"
            }
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            documents = data.get("documents", [])
            
            cursor = conn.cursor()
            updated_count = 0
            
            for doc in documents:
                name = doc.get("name", "")
                task_id = name.split("/")[-1]
                fields = doc.get("fields", {})
                
                # Parse Firestore fields safely
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
                
                # Numeric revision
                rev_val = fields.get("revision", {})
                if "integerValue" in rev_val:
                    revision = int(rev_val["integerValue"])
                elif "doubleValue" in rev_val:
                    revision = int(rev_val["doubleValue"])
                else:
                    revision = 1
                
                cursor.execute("SELECT revision, updated_at FROM tasks WHERE id = ?;", (task_id,))
                local = cursor.fetchone()
                
                if not local:
                    # Insert remote task into local SQLite DB
                    cursor.execute("""
                    INSERT INTO tasks (
                        id, owner_id, title, description, priority, status, category,
                        tags_json, due_at_utc, remind_before_minutes, created_at,
                        updated_at, completed_at, archived_at, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '[]', ?, 15, ?, ?, ?, ?, ?);
                    """, (task_id, owner_id, title, desc, priority, status, category, due_at_utc, created_at, updated_at, completed_at, archived_at, revision))
                    updated_count += 1
                elif revision > local["revision"]:
                    # Remote has higher revision: update local task
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
                # Touch database file to notify UI file watcher immediately
                try:
                    os.utime(DB_PATH, None)
                except Exception:
                    pass
                print(f"[SyncDaemon] Pulled {updated_count} task update(s) from cloud.")
                
            # Update lastSyncTime in sync_meta table
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('lastSyncTime', ?);", (now_iso,))
            conn.commit()
            return updated_count
    except Exception as e:
        print(f"[SyncDaemon] Pull tasks error: {e}")
        return 0

def run_sync_cycle():
    config = load_config()
    conn = get_db()
    try:
        # 1. Acquire valid ID token & UID
        id_token, auth_uid = get_auth_token(config)
        if not id_token:
            print("[SyncDaemon] Notice: Cloud authentication not established yet. Running local-only.")
        else:
            # 2. Push any pending local mutations
            pushed = push_pending_operations(conn, config, id_token, auth_uid)
            if pushed > 0:
                print(f"[SyncDaemon] Successfully pushed {pushed} operation(s) to cloud.")
                
            # 3. Pull remote tasks
            pull_remote_tasks(conn, config, id_token, auth_uid)
        
        # 4. Always maintain rotating atomic backup snapshot
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
        interval = int(config.get("sync_interval_sec", 15))
        
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
