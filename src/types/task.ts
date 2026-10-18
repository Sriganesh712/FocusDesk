export type Priority = 'critical' | 'high' | 'medium' | 'low';
export type TaskStatus = 'pending' | 'in_progress' | 'completed';
export type RecurrenceType = 'none' | 'daily' | 'weekly' | 'custom';

export interface RecurrenceRule {
  type: RecurrenceType;
  interval?: number; // e.g. every 2 weeks
  daysOfWeek?: number[]; // 0 = Sun, 1 = Mon, etc.
}

export interface Task {
  id: string; // Stable UUID
  ownerId: string; // Authenticated user UID
  title: string;
  description?: string;
  priority: Priority;
  status: TaskStatus;
  category: string;
  tags: string[];
  dueAtUtc?: string | null; // ISO 8601 UTC string
  timezone: string; // Local timezone (e.g. Asia/Kolkata)
  remindBeforeMinutes?: number; // Reminder lead time
  createdAt: string; // ISO 8601 UTC
  updatedAt: string; // ISO 8601 UTC
  completedAt?: string | null; // ISO 8601 UTC
  archivedAt?: string | null; // ISO 8601 UTC (soft delete)
  recurrenceRule?: RecurrenceRule | null;
  seriesId?: string | null; // Stable identifier for recurring series
  occurrenceKey?: string | null; // Unique occurrence identifier
  revision: number; // Concurrency revision
}

export type OperationType = 'CREATE' | 'UPDATE' | 'COMPLETE' | 'ARCHIVE' | 'RESTORE';

export interface SyncOperation {
  opId: string; // Unique operation UUID
  taskId: string;
  type: OperationType;
  patch: Partial<Task>; // Changed fields only
  baseRevision: number;
  timestamp: string; // ISO 8601 UTC
  retryCount: number;
  error?: string | null;
}

export interface ConflictRecord {
  conflictId: string;
  taskId: string;
  localTask: Task;
  cloudTask: Task;
  conflictingFields: string[];
  detectedAt: string;
  resolved: boolean;
}

export interface FocusDeskSettings {
  theme: 'dark' | 'light' | 'system';
  idleTimeoutMinutes: number; // For kiosk/display dimming
  reminderLeadTimeMinutes: number; // Default reminder lead time
  syncIntervalActiveSec: number;
  syncIntervalIdleSec: number;
  soundAlerts: boolean;
}

export interface SyncStatus {
  state: 'synced' | 'syncing' | 'offline' | 'pending_changes' | 'conflict' | 'error';
  lastSyncTime: string | null;
  pendingCount: number;
  conflictCount: number;
  errorMessage?: string | null;
}
