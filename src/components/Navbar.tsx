import React from 'react';
import {
  CheckSquare,
  Cloud,
  CloudOff,
  RefreshCw,
  AlertTriangle,
  Download,
  Settings,
  Plus,
  LogIn,
  LogOut,
  User as UserIcon,
} from 'lucide-react';
import type { SyncStatus } from '../types/task';
import type { User } from 'firebase/auth';

interface NavbarProps {
  syncStatus: SyncStatus;
  user: User | null;
  onOpenTaskModal: () => void;
  onOpenConflictModal: () => void;
  onOpenExportImportModal: () => void;
  onOpenSettingsModal: () => void;
  onOpenAuthModal: () => void;
  onLogout: () => void;
  onTriggerSync: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  syncStatus,
  user,
  onOpenTaskModal,
  onOpenConflictModal,
  onOpenExportImportModal,
  onOpenSettingsModal,
  onOpenAuthModal,
  onLogout,
  onTriggerSync,
}) => {
  return (
    <header className="navbar-container">
      <div className="navbar-left">
        <div className="logo-badge">
          <CheckSquare className="logo-icon" size={24} />
          <span className="logo-title">FocusDesk</span>
        </div>

        {/* Sync Status Badge */}
        <div
          className={`sync-badge sync-badge-${syncStatus.state}`}
          onClick={onTriggerSync}
          title={
            syncStatus.lastSyncTime
              ? `Last synced: ${new Date(syncStatus.lastSyncTime).toLocaleTimeString()}`
              : 'Click to trigger sync'
          }
        >
          {syncStatus.state === 'synced' && (
            <>
              <Cloud size={15} className="status-icon" />
              <span className="status-text">Synced</span>
            </>
          )}
          {syncStatus.state === 'syncing' && (
            <>
              <RefreshCw size={15} className="status-icon spin" />
              <span className="status-text">Syncing...</span>
            </>
          )}
          {syncStatus.state === 'pending_changes' && (
            <>
              <Cloud size={15} className="status-icon" />
              <span className="status-text">{syncStatus.pendingCount} pending</span>
            </>
          )}
          {syncStatus.state === 'offline' && (
            <>
              <CloudOff size={15} className="status-icon" />
              <span className="status-text">Local Only</span>
            </>
          )}
          {syncStatus.state === 'conflict' && (
            <div
              className="conflict-trigger"
              onClick={(e) => {
                e.stopPropagation();
                onOpenConflictModal();
              }}
            >
              <AlertTriangle size={15} className="status-icon alert" />
              <span className="status-text">{syncStatus.conflictCount} conflict(s)</span>
            </div>
          )}
        </div>
      </div>

      <div className="navbar-right">
        {syncStatus.conflictCount > 0 && (
          <button
            className="nav-btn btn-conflict"
            onClick={onOpenConflictModal}
            title="Resolve synchronization conflicts"
          >
            <AlertTriangle size={16} />
            <span>Resolve ({syncStatus.conflictCount})</span>
          </button>
        )}

        <button
          className="nav-btn btn-secondary"
          onClick={onOpenExportImportModal}
          title="Backup and Restore tasks"
        >
          <Download size={16} />
          <span className="btn-label-desktop">Backup</span>
        </button>

        <button
          className="nav-btn btn-secondary"
          onClick={onOpenSettingsModal}
          title="Settings & STM32 Kiosk Guide"
        >
          <Settings size={16} />
          <span className="btn-label-desktop">Settings</span>
        </button>

        {user ? (
          <div className="user-profile-badge">
            <UserIcon size={16} className="user-icon" />
            <span className="user-email" title={user.email || 'Cloud User'}>
              {user.email ? user.email.split('@')[0] : 'User'}
            </span>
            <button
              className="icon-btn-compact"
              onClick={onLogout}
              title="Sign Out"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <button
            className="nav-btn btn-auth"
            onClick={onOpenAuthModal}
            title="Connect Cloud Account"
          >
            <LogIn size={16} />
            <span>Sign In</span>
          </button>
        )}

        <button
          className="nav-btn btn-primary"
          onClick={onOpenTaskModal}
          title="Create New Task"
        >
          <Plus size={18} />
          <span>New Task</span>
        </button>
      </div>
    </header>
  );
};
