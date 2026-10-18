import {
  collection,
  doc,
  getDocs,
  setDoc,
  query,
  where,
} from 'firebase/firestore';
import { db, isFirebaseConfigured } from '../firebase/config';
import type { Task, ConflictRecord, SyncStatus } from '../types/task';
import {
  getAllTasksFromDb,
  saveTasksToDb,
  getPendingOperations,
  removeOperationFromDb,
  saveConflictToDb,
  getUnresolvedConflicts,
  getMetadata,
  setMetadata,
} from '../db/indexedDb';

class SyncEngine {
  private syncTimer: any = null;
  private isSyncing = false;
  private retryDelayMs = 2000;
  private maxRetryDelayMs = 60000;
  private consecutiveFailures = 0;
  private statusListeners: Array<(status: SyncStatus) => void> = [];
  private taskChangeListeners: Array<() => void> = [];
  private activeOwnerId: string | null = null;
  private debounceTimer: any = null;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        console.log('[SyncEngine] Network restored. Triggering sync...');
        this.consecutiveFailures = 0;
        this.triggerSync();
      });

      window.addEventListener('offline', () => {
        this.emitStatus();
      });

      // Periodic Sync: 30s active
      this.syncTimer = setInterval(() => {
        if (!document.hidden) {
          this.triggerSync();
        }
      }, 30000);

      // Visibility change: immediate sync on wake
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
          this.triggerSync();
        }
      });
    }
  }

  public destroy(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
  }

  public setOwnerId(ownerId: string | null) {
    this.activeOwnerId = ownerId;
    this.triggerSync();
  }

  public subscribeStatus(listener: (status: SyncStatus) => void): () => void {
    this.statusListeners.push(listener);
    this.emitStatus();
    return () => {
      this.statusListeners = this.statusListeners.filter((l) => l !== listener);
    };
  }

  public subscribeTaskChanges(listener: () => void): () => void {
    this.taskChangeListeners.push(listener);
    return () => {
      this.taskChangeListeners = this.taskChangeListeners.filter((l) => l !== listener);
    };
  }

  public notifyLocalChange() {
    // Notify local UI immediately
    this.taskChangeListeners.forEach((l) => l());
    this.emitStatus();

    // Debounce cloud push by 500ms for rapid edits
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.triggerSync();
    }, 500);
  }

  public async getStatus(): Promise<SyncStatus> {
    const pending = await getPendingOperations();
    const conflicts = await getUnresolvedConflicts();
    const lastSyncTime = await getMetadata('lastSyncTime');

    const isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;

    let state: SyncStatus['state'] = 'synced';
    if (!isOnline || !isFirebaseConfigured) {
      state = 'offline';
    } else if (this.isSyncing) {
      state = 'syncing';
    } else if (conflicts.length > 0) {
      state = 'conflict';
    } else if (pending.length > 0) {
      state = 'pending_changes';
    }

    return {
      state,
      lastSyncTime,
      pendingCount: pending.length,
      conflictCount: conflicts.length,
    };
  }

  private async emitStatus() {
    const status = await this.getStatus();
    this.statusListeners.forEach((l) => l(status));
  }

  public async triggerSync(): Promise<void> {
    if (this.isSyncing || !isFirebaseConfigured || !db || !this.activeOwnerId) {
      this.emitStatus();
      return;
    }

    const isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;
    if (!isOnline) {
      this.emitStatus();
      return;
    }

    this.isSyncing = true;
    this.emitStatus();

    try {
      await this.pushPendingOperations();
      await this.pullRemoteTasks();

      await setMetadata('lastSyncTime', new Date().toISOString());
      this.consecutiveFailures = 0;
      this.retryDelayMs = 2000;
    } catch (err: any) {
      console.warn('[SyncEngine] Synchronization error:', err);
      this.consecutiveFailures++;
      // Exponential backoff
      this.retryDelayMs = Math.min(this.maxRetryDelayMs, this.retryDelayMs * 2);
    } finally {
      this.isSyncing = false;
      this.emitStatus();
      this.taskChangeListeners.forEach((l) => l());
    }
  }

  private async pushPendingOperations(): Promise<void> {
    if (!db || !this.activeOwnerId) return;

    const pendingOps = await getPendingOperations();
    for (const op of pendingOps) {
      try {
        const taskDocRef = doc(db, 'users', this.activeOwnerId, 'tasks', op.taskId);

        // Fetch current local task state to persist
        const localTasks = await getAllTasksFromDb();
        const currentTask = localTasks.find((t) => t.id === op.taskId);

        if (currentTask) {
          // Idempotent upsert to Firestore
          await setDoc(taskDocRef, currentTask, { merge: true });
        }

        // Successfully pushed: remove from pending queue
        await removeOperationFromDb(op.opId);
      } catch (err: any) {
        // If error is network or auth, break and retry later
        console.warn(`[SyncEngine] Operation ${op.opId} failed:`, err);
        throw err;
      }
    }
  }

  private async pullRemoteTasks(): Promise<void> {
    if (!db || !this.activeOwnerId) return;

    const tasksCol = collection(db, 'users', this.activeOwnerId, 'tasks');
    const q = query(tasksCol, where('ownerId', '==', this.activeOwnerId));
    const snapshot = await getDocs(q);

    const remoteTasks: Task[] = [];
    snapshot.forEach((docSnap) => {
      const data = docSnap.data() as Task;
      if (data && data.id) {
        remoteTasks.push(data);
      }
    });

    const localTasks = await getAllTasksFromDb();
    const localMap = new Map<string, Task>(localTasks.map((t) => [t.id, t]));
    const pendingOps = await getPendingOperations();
    const pendingTaskIds = new Set(pendingOps.map((op) => op.taskId));

    const tasksToSave: Task[] = [];

    for (const remote of remoteTasks) {
      const local = localMap.get(remote.id);

      if (!local) {
        // New remote task: save locally
        tasksToSave.push(remote);
      } else if (!pendingTaskIds.has(remote.id)) {
        // No local pending edits: accept remote if newer revision or timestamp
        if (remote.revision > local.revision || new Date(remote.updatedAt) > new Date(local.updatedAt)) {
          tasksToSave.push(remote);
        }
      } else {
        // Local has pending unpushed edits! Reconcile field by field
        if (remote.revision !== local.revision) {
          const conflictingFields = this.detectConflictingFields(local, remote);
          if (conflictingFields.length > 0) {
            // Concurrent conflicting edit! Preserve both and record conflict
            const conflict: ConflictRecord = {
              conflictId: `conflict-${remote.id}-${Date.now()}`,
              taskId: remote.id,
              localTask: local,
              cloudTask: remote,
              conflictingFields,
              detectedAt: new Date().toISOString(),
              resolved: false,
            };
            await saveConflictToDb(conflict);
          } else {
            // Non-overlapping fields: auto-merge
            const mergedTask: Task = {
              ...remote,
              ...local,
              updatedAt: new Date().toISOString(),
              revision: Math.max(local.revision, remote.revision) + 1,
            };
            tasksToSave.push(mergedTask);
          }
        }
      }
    }

    if (tasksToSave.length > 0) {
      await saveTasksToDb(tasksToSave);
    }
  }

  private detectConflictingFields(local: Task, remote: Task): string[] {
    const fieldsToCheck: (keyof Task)[] = [
      'title',
      'description',
      'priority',
      'status',
      'category',
      'dueAtUtc',
      'remindBeforeMinutes',
    ];

    const conflicts: string[] = [];
    for (const f of fieldsToCheck) {
      if (JSON.stringify(local[f]) !== JSON.stringify(remote[f])) {
        conflicts.push(f);
      }
    }
    return conflicts;
  }
}

export const syncEngine = new SyncEngine();
