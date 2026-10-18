import React, { useState, useEffect } from 'react';
import {
  X,
  Tv,
  Trash2,
  HardDrive,
  Cpu,
  Info,
} from 'lucide-react';
import type { FocusDeskSettings, Task } from '../types/task';
import { getMetadata, setMetadata, saveTasksToDb } from '../db/indexedDb';
import { syncEngine } from '../sync/syncEngine';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  tasks: Task[];
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  tasks,
}) => {
  const [settings, setSettings] = useState<FocusDeskSettings>({
    theme: 'dark',
    idleTimeoutMinutes: 2,
    reminderLeadTimeMinutes: 15,
    syncIntervalActiveSec: 30,
    syncIntervalIdleSec: 300,
    soundAlerts: true,
  });

  useEffect(() => {
    if (isOpen) {
      getMetadata('user_settings').then((stored) => {
        if (stored) setSettings(stored);
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async (updated: FocusDeskSettings) => {
    setSettings(updated);
    await setMetadata('user_settings', updated);
  };

  const handleClearCompleted = async () => {
    if (confirm('Archive all completed tasks? They can still be exported in backups.')) {
      const nowIso = new Date().toISOString();
      const updatedTasks = tasks.map((t) => {
        if (t.status === 'completed' && !t.archivedAt) {
          return { ...t, archivedAt: nowIso, revision: t.revision + 1 };
        }
        return t;
      });
      await saveTasksToDb(updatedTasks);
      syncEngine.notifyLocalChange();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-settings card-glass" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>FocusDesk Settings</h2>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body-section">
          {/* Display & Screen Blanking */}
          <div className="settings-card card-glass p-4 mb-4">
            <h4 className="flex items-center gap-2 mb-3">
              <Tv size={18} className="text-primary" />
              <span>STM32 Kiosk & Display Settings</span>
            </h4>

            <div className="form-group mb-3">
              <label className="flex items-center justify-between text-sm">
                <span>Display Idle Timeout (Screen Dimming)</span>
                <span className="text-primary font-mono">{settings.idleTimeoutMinutes} min</span>
              </label>
              <select
                value={settings.idleTimeoutMinutes}
                onChange={(e) =>
                  handleSave({ ...settings, idleTimeoutMinutes: Number(e.target.value) })
                }
                className="form-select mt-1"
              >
                <option value={1}>1 Minute</option>
                <option value={2}>2 Minutes (Recommended for LCD longevity)</option>
                <option value={5}>5 Minutes</option>
                <option value={10}>10 Minutes</option>
                <option value={0}>Never Dim (Always Active)</option>
              </select>
              <p className="text-muted text-xs mt-1">
                On the STM32MP135F-DK, the backlight automatically dims to save power and restores instantly on touch.
              </p>
            </div>
          </div>

          {/* Sync & Frequency */}
          <div className="settings-card card-glass p-4 mb-4">
            <h4 className="flex items-center gap-2 mb-3">
              <Cpu size={18} className="text-primary" />
              <span>Synchronization Frequency</span>
            </h4>

            <div className="form-row">
              <div className="form-group flex-1">
                <label className="text-xs text-muted">Active Window Sync</label>
                <div className="text-sm font-semibold mt-1">Every 30 seconds</div>
              </div>
              <div className="form-group flex-1">
                <label className="text-xs text-muted">Background/Idle Sync</label>
                <div className="text-sm font-semibold mt-1">Every 5 minutes</div>
              </div>
            </div>
            <p className="text-muted text-xs mt-2">
              Syncing is automatic on tab focus, network recovery, or task edits (debounced by 500ms).
            </p>
          </div>

          {/* Data & Storage Management */}
          <div className="settings-card card-glass p-4 mb-4">
            <h4 className="flex items-center gap-2 mb-3">
              <HardDrive size={18} className="text-primary" />
              <span>Local Storage & Maintenance</span>
            </h4>

            <div className="flex items-center justify-between py-2 border-b border-subtle">
              <div>
                <div className="text-sm font-medium">Active Tasks</div>
                <div className="text-xs text-muted">
                  {tasks.filter((t) => !t.archivedAt && t.status !== 'completed').length} pending,{' '}
                  {tasks.filter((t) => !t.archivedAt && t.status === 'completed').length} completed
                </div>
              </div>
              <button className="btn-secondary btn-tiny" onClick={handleClearCompleted}>
                <Trash2 size={14} />
                <span>Archive Completed</span>
              </button>
            </div>
          </div>

          {/* STM32 Integration Notes */}
          <div className="kiosk-guide-box p-3 bg-base border rounded text-xs text-muted">
            <div className="flex items-center gap-1.5 text-primary font-semibold mb-1">
              <Info size={14} />
              <span>STM32MP135F-DK Kiosk Integration</span>
            </div>
            <p>
              The embedded touchscreen kiosk displays tasks fullscreen at 480×272 via native Wayland GTK3.
              Tasks completed on the touch panel sync bidirectionally with this web dashboard via HTTPS REST.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
