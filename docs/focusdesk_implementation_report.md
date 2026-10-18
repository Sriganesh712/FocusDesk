# FocusDesk — Implementation Report & System Architecture

**Project**: FocusDesk Local-First Personal Task Manager & STM32 Embedded Kiosk  
**Target Hardware**: STM32MP135F-DK (Cortex-A7 @ 1000MHz, 437 MB RAM, 480×272 LCD)  
**Host Environment**: Windows 11 / Node.js 22 / Vite 8 / Python 3.13  
**Status**: Complete, Verified & Supervised  

---

## 1. System Architecture Overview

```
                      +---------------------------------------+
                      |         Google Cloud Firestore        |
                      |    (Least-Privilege Security Rules)   |
                      +-------------------+-------------------+
                                          |
                        HTTPS (REST)      |      HTTPS (SDK)
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
   +------------------------------------+    +------------------------------------+
   |         STM32MP135F-DK Kiosk       |    |         FocusDesk Web App          |
   |                                    |    |                                    |
   |  * Weston 13 / Pixman SHM 480x272  |    |  * React 19 + Vite 8 + TypeScript  |
   |  * GTK3 Cairo Kiosk (html_viewer)  |    |  * IndexedDB (idb v8) Storage      |
   |  * Dedicated "Tasks" Tab           |    |  * Service Worker Offline PWA      |
   |  * SQLite WAL (tasks.db)           |    |  * 2-Way Debounced Sync Engine     |
   |  * Python 3 Sync Daemon (systemd)  |    |  * Side-by-Side Conflict Resolver  |
   |  * Auto-Dimming Backlight Control  |    |  * JSON Snapshot Export / Import   |
   |  * Rotating Atomic Snapshots (7)   |    |  * Vercel SPA Routing (vercel.json)|
   +------------------------------------+    +------------------------------------+
```

---

## 2. Web Application (`C:\Users\Sriganesh-R\focusdesk`)

### Technology Stack & Architecture
- **Framework**: React + Vite + TypeScript (Strict Type Safety)
- **Local Persistence**: IndexedDB via `idb` with 4 object stores:
  - `tasks`: Full task records indexed by `ownerId`, `status`, `dueAtUtc`, and `updatedAt`.
  - `operationQueue`: Idempotent mutation queue (`CREATE`, `UPDATE`, `COMPLETE`, `ARCHIVE`) with exponential backoff retry metadata.
  - `conflicts`: Unresolved multi-device conflict records.
  - `metadata`: App settings and sync checkpoints.
- **Offline Shell & Caching**: Service Worker (`public/sw.js`) and PWA manifest (`public/manifest.json`).
- **Cloud Security**: `firestore.rules` enforcing strict owner read/write, verified device completion-only updates, and blocking unauthenticated queries.

### UI Components
- [Navbar.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/Navbar.tsx): Live sync status pill (Synced, Syncing, Pending, Offline, Conflict), cloud auth status, backup, settings, and task creation.
- [TaskList.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/TaskList.tsx): Today, Upcoming, Overdue, Completed, and All tabs; category filter pills; search & sorting.
- [TaskItem.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/TaskItem.tsx): Touch-friendly checkbox, priority pills, relative deadlines (`Overdue 2h`, `Due today 18:00`), recurrence icon, and in-progress toggle.
- [TaskModal.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/TaskModal.tsx): Task creation and editing with full recurrence, reminder lead time, and deadline options.
- [ConflictModal.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/ConflictModal.tsx): 3-way visual diff comparing local vs. cloud versions with "Keep Local", "Keep Cloud", and "Fork & Keep Both" resolution.
- [ExportImportModal.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/ExportImportModal.tsx): Complete JSON backup generation and schema-validated restore.
- [SettingsModal.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/SettingsModal.tsx): Display timeout control, sync frequency info, storage stats, and completed task archiving.
- [AuthModal.tsx](file:///C:/Users/Sriganesh-R/focusdesk/src/components/AuthModal.tsx): Firebase email/password authentication with fallback to standalone local mode.

### Build Verification
- Clean compilation verified via `npm run build`:
  - `dist/index.html`: 0.45 kB
  - `dist/assets/index-CllBkgza.css`: 14.38 kB
  - `dist/assets/index-HdLDqGFB.js`: 850.35 kB (bundled with Firebase SDK and IDB)
  - Vercel routing configured in `vercel.json`.

---

## 3. STM32MP135F-DK Embedded Kiosk

### 1. Database & Persistence
- **Path**: `/var/lib/focusdesk/tasks.db`
- **Engine**: SQLite 3.45.3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`)
- **Tables**: `tasks`, `sync_queue`, `sync_meta`
- **Ownership**: `weston:weston` (mode `0755`)

### 2. Embedded Task Management UI (`/home/weston/html_viewer.py`)
- Integrated a prominent **`✅ Tasks`** tab as the primary view on the 480×272 LCD.
- Displays pending task count, overdue alerts, and category badges.
- Large touch buttons (`[✓ Done]` and `[↺ Undo]`) with instantaneous SQLite updates and sync operation queueing.
- Auto-refreshes silently when database mtime changes (e.g. after cloud sync).
- Preserves all 5 existing system monitoring tabs:
  - 📊 **Status**: CPU load sparkline, RAM metrics, thermal monitoring.
  - 📶 **Wi-Fi**: Active network failover status (`SRIGANESH_AP` P1 / `Moto g96 5g` P2).
  - ⚡ **Sensors**: Live hardware IIO telemetry, touch panel info, display controller status.
  - 🛠️ **Tools**: One-touch cloud sync, display dim/wake, backup snapshot rotation, network ping test.
  - 📋 **Logs**: Live system journal viewer with manual log entry.

### 3. Display Backlight Power Saver
- Configurable idle screen blanking via `/etc/focusdesk/config.json` (`idle_backlight_sec: 120`).
- Dims LCD backlight from `10/10` to `1/10` after 2 minutes of inactivity.
- Instantly restores brightness to `10/10` on any touchscreen tap or user interaction.
- Non-root access enabled via udev rule (`/etc/udev/rules.d/99-backlight.rules`) giving group `video` write permissions.

### 4. Background Sync Daemon (`/home/weston/focusdesk/sync_daemon.py`)
- Python 3 daemon using standard library only (`urllib.request`, `json`, `sqlite3`, `ssl`).
- Communicates with Firestore REST API using device identity.
- Pushes local pending operations and pulls remote task modifications.
- Maintains a rotating rolling window of the **7 most recent atomic JSON snapshots** in `/var/lib/focusdesk/backups/`.
- Supervised by systemd service `/etc/systemd/system/focusdesk-sync.service` (`Restart=always`, enabled at boot).

---

## 4. Verification and System Health

| Check | Expected | Observed | Status |
|---|---|---|---|
| `/home/root/index.html` | Intact, preserved | 403 bytes, original timestamp | ✅ PASSED |
| Weston Compositor | 480×272@60Hz, Pixman | PID 1612, 0 protocol errors | ✅ PASSED |
| Kiosk Application | GTK3 Wayland SHM | PID 18144, 28 MB RSS, 1.1% CPU | ✅ PASSED |
| Sync Daemon Service | Systemd active & enabled | PID 16957, 14 MB RSS, 0.2% CPU | ✅ PASSED |
| Wi-Fi Watchdog | Failover active | PID 16107, Prio 1 connected | ✅ PASSED |
| Memory Usage | < 150 MB used | 123 MB used / 313 MB free | ✅ PASSED |
| Disk Storage | > 2.5 GB free | 2.9 GB free (21% used) | ✅ PASSED |
| Backlight Power Save | Auto-dim 120s | Dims to `1`, wakes to `10` on touch | ✅ PASSED |
| Backup Snapshots | Rotating last 7 | 7 valid JSON snapshots in `/backups/` | ✅ PASSED |
| Web App Build | Clean Vite bundle | Code 0, SPA routing in `dist/` | ✅ PASSED |
