import { openDB, type IDBPDatabase } from 'idb';
import type { Task, SyncOperation, ConflictRecord } from '../types/task';

const DB_NAME = 'focusdesk_db';
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase> | null = null;

export function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // Tasks Store
        if (!db.objectStoreNames.contains('tasks')) {
          const taskStore = db.createObjectStore('tasks', { keyPath: 'id' });
          taskStore.createIndex('ownerId', 'ownerId', { unique: false });
          taskStore.createIndex('status', 'status', { unique: false });
          taskStore.createIndex('dueAtUtc', 'dueAtUtc', { unique: false });
          taskStore.createIndex('updatedAt', 'updatedAt', { unique: false });
        }

        // Operation Queue Store (for offline mutations)
        if (!db.objectStoreNames.contains('operationQueue')) {
          const opStore = db.createObjectStore('operationQueue', { keyPath: 'opId' });
          opStore.createIndex('taskId', 'taskId', { unique: false });
          opStore.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // Conflicts Store
        if (!db.objectStoreNames.contains('conflicts')) {
          const conflictStore = db.createObjectStore('conflicts', { keyPath: 'conflictId' });
          conflictStore.createIndex('taskId', 'taskId', { unique: false });
          conflictStore.createIndex('resolved', 'resolved', { unique: false });
        }

        // Sync & App Metadata Store
        if (!db.objectStoreNames.contains('metadata')) {
          db.createObjectStore('metadata', { keyPath: 'key' });
        }
      },
    });
  }
  return dbPromise;
}

// ----------------------------------------------------------------------------
// TASK OPERATIONS
// ----------------------------------------------------------------------------

export async function getAllTasksFromDb(): Promise<Task[]> {
  const db = await getDb();
  return db.getAll('tasks');
}

export async function getTaskFromDb(id: string): Promise<Task | undefined> {
  const db = await getDb();
  return db.get('tasks', id);
}

export async function saveTaskToDb(task: Task): Promise<void> {
  const db = await getDb();
  await db.put('tasks', task);
}

export async function saveTasksToDb(tasks: Task[]): Promise<void> {
  const db = await getDb();
  const tx = db.transaction('tasks', 'readwrite');
  for (const t of tasks) {
    await tx.store.put(t);
  }
  await tx.done;
}

export async function deleteTaskFromDb(id: string): Promise<void> {
  const db = await getDb();
  await db.delete('tasks', id);
}

// ----------------------------------------------------------------------------
// OPERATION QUEUE OPERATIONS (OFFLINE MUTATIONS)
// ----------------------------------------------------------------------------

export async function enqueueOperation(op: SyncOperation): Promise<void> {
  const db = await getDb();
  await db.put('operationQueue', op);
}

export async function getPendingOperations(): Promise<SyncOperation[]> {
  const db = await getDb();
  const ops = await db.getAll('operationQueue');
  // Return in chronological order
  return ops.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
}

export async function removeOperationFromDb(opId: string): Promise<void> {
  const db = await getDb();
  await db.delete('operationQueue', opId);
}

export async function updateOperationInDb(op: SyncOperation): Promise<void> {
  const db = await getDb();
  await db.put('operationQueue', op);
}

// ----------------------------------------------------------------------------
// CONFLICT OPERATIONS
// ----------------------------------------------------------------------------

export async function saveConflictToDb(conflict: ConflictRecord): Promise<void> {
  const db = await getDb();
  await db.put('conflicts', conflict);
}

export async function getUnresolvedConflicts(): Promise<ConflictRecord[]> {
  const db = await getDb();
  const all = await db.getAll('conflicts');
  return all.filter((c) => !c.resolved);
}

export async function markConflictResolvedInDb(conflictId: string): Promise<void> {
  const db = await getDb();
  const conflict = await db.get('conflicts', conflictId);
  if (conflict) {
    conflict.resolved = true;
    await db.put('conflicts', conflict);
  }
}

// ----------------------------------------------------------------------------
// METADATA OPERATIONS
// ----------------------------------------------------------------------------

export async function getMetadata(key: string): Promise<any> {
  const db = await getDb();
  const entry = await db.get('metadata', key);
  return entry ? entry.value : null;
}

export async function setMetadata(key: string, value: any): Promise<void> {
  const db = await getDb();
  await db.put('metadata', { key, value });
}
