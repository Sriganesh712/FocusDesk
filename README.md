# FocusDesk

**FocusDesk** is a reliable, local-first personal task manager featuring a modern React web application, Cloud Firestore synchronization, and an offline-capable touchscreen kiosk running on the **STM32MP135F-DK** (480×272 LCD via Weston).

---

## 📁 Repository Structure

```
D:/Files/FocusDesk/
├── src/                        # React 19 + TypeScript source code
│   ├── components/             # TaskList, TaskItem, TaskModal, ConflictModal, etc.
│   ├── db/                     # IndexedDB layer (idb v8) with 4 stores
│   ├── firebase/               # Firebase Auth & Cloud Firestore config
│   ├── sync/                   # 2-way debounced sync engine with auto-merge
│   ├── types/                  # Task, SyncOperation, Conflict data models
│   └── utils/                  # JSON backup export and validated import
├── public/                     # Static assets, favicon, icons, manifest.json
│   └── sw.js                   # Service Worker for offline PWA shell caching
├── dist/                       # Production-ready built bundle (Vite)
├── embedded/                   # STM32MP135F-DK Kiosk & Daemon Source
│   ├── html_viewer.py          # Native GTK3/Cairo Wayland SHM Kiosk (Tasks Tab)
│   ├── sync_daemon.py          # Python 3 HTTPS REST sync daemon (zero 3rd-party libs)
│   ├── init_db.py              # SQLite database schema and WAL mode initializer
│   ├── launch-html-viewer.sh   # Resilient auto-boot kiosk loop script
│   ├── focusdesk-sync.service  # Systemd service unit for sync daemon
│   ├── wifi_watchdog.py        # Sub-second Wi-Fi failover watchdog
│   ├── wifi-watchdog.service   # Systemd service unit for Wi-Fi watchdog
│   └── config.json             # Device configuration & backlight timeout settings
├── scripts/                    # Board Deployment & Communication Utilities
│   ├── deploy_to_board.py      # Resilient stdin base64 file deployer via SSH
│   ├── serial_cmd.py           # USB Serial COM4 (115200 baud) command tool
│   └── ssh_run.py              # PuTTY plink SSH execution utility
├── docs/                       # Architecture diagrams and test reports
│   └── focusdesk_implementation_report.md
├── firestore.rules             # Least-privilege Firestore security rules
├── vercel.json                 # SPA routing and Service Worker caching headers
└── package.json                # Project dependencies and build scripts
```

---

## 🚀 Web Application

### Prerequisites
- Node.js (v18+)
- npm

### Development
```bash
npm install
npm run dev
```

### Production Build
```bash
npm run build
```
Generates a production build in `dist/` ready for hosting on Vercel or any static host.

### Cloud Synchronization Setup
Copy `.env.example` to `.env` and provide your Firebase project credentials:
```ini
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_messaging_id
VITE_FIREBASE_APP_ID=your_app_id
```
*Note: FocusDesk operates 100% offline using local IndexedDB if Firebase credentials are omitted.*

---

## 📟 STM32MP135F-DK Embedded Kiosk

### Features
1. **Native Wayland GTK3 Kiosk**: Runs at 60 FPS on Pixman renderer (`/dev/dri/card0`) without GPU dependencies.
2. **Dedicated Touch Tasks View**: Fast touch-to-complete buttons (`[✓ Done]` and `[↺ Undo]`), deadline alerts, priority badges.
3. **Local SQLite Persistence**: High-concurrency WAL mode (`/var/lib/focusdesk/tasks.db`).
4. **Auto-Dimming Backlight**: Power saving dims LCD from `10/10` to `1/10` after 2 minutes of idle time. Wakes instantly on any touch.
5. **Background Sync Daemon**: Lightweight (`sync_daemon.py`) supervised by systemd (`focusdesk-sync.service`).
6. **Automatic Snapshot Rotation**: Maintains 7 rolling atomic JSON backups in `/var/lib/focusdesk/backups/`.
7. **Boot Auto-Start**: Automatically launches on startup via Weston's graphical session.

---

## 🛡️ Boot & Supervision Configuration

On the STM32 board:
- `/etc/default/demo-launcher` -> points to `/usr/local/demo/launch-html-viewer.sh`
- `launch-html-viewer.sh` -> waits for Wayland socket and launches `/home/weston/html_viewer.py` in a persistent restart loop
- `focusdesk-sync.service` -> enabled under systemd (`systemctl enable focusdesk-sync.service`)
- `wifi-watchdog.service` -> enabled under systemd (`systemctl enable wifi-watchdog.service`)
