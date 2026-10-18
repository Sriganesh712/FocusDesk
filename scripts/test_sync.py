import sys
import subprocess
import json
import time
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run():
    print("[1] Simulating user tapping [Done] on STM32 touchscreen for task-web-1001...")
    
    remote_script = """
import sqlite3, json, datetime
conn = sqlite3.connect('/var/lib/focusdesk/tasks.db')
c = conn.cursor()
now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
c.execute("UPDATE tasks SET status='completed', completed_at=?, updated_at=?, revision=2 WHERE id='task-web-1001';", (now_iso, now_iso))
patch = {"status": "completed", "completedAt": now_iso, "updatedAt": now_iso, "revision": 2}
c.execute("INSERT INTO sync_queue (op_id, task_id, type, patch_json, base_revision, timestamp) VALUES (?, ?, ?, ?, ?, ?);",
          ("op-touch-test", "task-web-1001", "COMPLETE", json.dumps(patch), 1, now_iso))
conn.commit()
conn.close()
print("Touch complete action recorded in SQLite & sync_queue")
"""
    import base64
    b64 = base64.b64encode(remote_script.encode("utf-8")).decode("ascii")
    cmd = f"python3 -c \"import base64; exec(base64.b64decode('{b64}').decode())\""
    res = subprocess.run(["python", r"D:\Files\FocusDesk\scripts\ssh_run.py", cmd], capture_output=True, text=True)
    print("STM32 response:", res.stdout.strip())
    if res.stderr.strip():
        print("STM32 stderr:", res.stderr.strip())
    
    print("\n[2] Waiting 12 seconds for sync_daemon to cycle and push to Firestore...")
    time.sleep(12)
    
    print("\n[3] Checking sync_queue on STM32...")
    res2 = subprocess.run(["python", r"D:\Files\FocusDesk\scripts\ssh_run.py", "sqlite3 /var/lib/focusdesk/tasks.db 'SELECT count(*) FROM sync_queue;'"], capture_output=True, text=True)
    print("Pending sync_queue count on STM32:", res2.stdout.strip())
    
    print("\n[4] Querying Firestore to verify task-web-1001 status in cloud...")
    import urllib.request
    api_key = "AIzaSyCUAvR0Sv42aOzG-PSIBzWcZwEM2DBWZu8"
    login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = json.dumps({"email": "kiosk-device@focusdesk.local", "password": "DevicePassword123!", "returnSecureToken": True}).encode("utf-8")
    req = urllib.request.Request(login_url, data=data, headers={"Content-Type": "application/json"})
    res3 = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    id_token = res3["idToken"]
    uid = res3["localId"]
    
    url = f"https://firestore.googleapis.com/v1/projects/focusdsk/databases/(default)/documents/users/{uid}/tasks/task-web-1001"
    req4 = urllib.request.Request(url, headers={"Authorization": f"Bearer {id_token}"})
    with urllib.request.urlopen(req4) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
        status = doc["fields"]["status"]["stringValue"]
        rev = doc["fields"]["revision"]["integerValue"]
        completed_at = doc["fields"].get("completedAt", {}).get("stringValue", "N/A")
        print(f"Firestore task-web-1001 Status: {status}")
        print(f"Firestore task-web-1001 Revision: {rev}")
        print(f"Firestore task-web-1001 CompletedAt: {completed_at}")

if __name__ == "__main__":
    run()
