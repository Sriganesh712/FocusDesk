import { useState, useEffect, useCallback } from 'react';
import type { Task, SyncStatus } from './types/task';
import {
  getAllTasksFromDb,
  saveTaskToDb,
  enqueueOperation,
} from './db/indexedDb';
import { syncEngine } from './sync/syncEngine';
import { subscribeToAuth, logout, type AuthState } from './firebase/auth';

import { Navbar } from './components/Navbar';
import { TaskList } from './components/TaskList';
import { TaskModal } from './components/TaskModal';
import { ConflictModal } from './components/ConflictModal';
import { ExportImportModal } from './components/ExportImportModal';
import { SettingsModal } from './components/SettingsModal';
import { AuthModal } from './components/AuthModal';

import './App.css';

export function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    state: 'synced',
    lastSyncTime: null,
    pendingCount: 0,
    conflictCount: 0,
  });
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    localOwnerId: 'local-owner-focusdesk',
    loading: true,
    isCloudAuth: false,
  });

  // Modal open states
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [taskToEdit, setTaskToEdit] = useState<Task | null>(null);
  const [isConflictModalOpen, setIsConflictModalOpen] = useState(false);
  const [isExportImportModalOpen, setIsExportImportModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Load tasks from local IndexedDB
  const loadTasks = useCallback(async () => {
    try {
      const all = await getAllTasksFromDb();
      setTasks(all);
    } catch (err) {
      console.error('[FocusDesk] Error loading tasks from IndexedDB:', err);
    }
  }, []);

  // Initialize Auth & Sync Subscriptions
  useEffect(() => {
    loadTasks();

    const unsubAuth = subscribeToAuth((state) => {
      setAuthState(state);
      syncEngine.setOwnerId(state.user ? state.user.uid : state.localOwnerId);
    });

    const unsubSync = syncEngine.subscribeStatus((status) => {
      setSyncStatus(status);
    });

    const unsubTasks = syncEngine.subscribeTaskChanges(() => {
      loadTasks();
    });

    return () => {
      unsubAuth();
      unsubSync();
      unsubTasks();
    };
  }, [loadTasks]);

  // Handle Complete / Uncomplete
  const handleToggleComplete = async (task: Task) => {
    const isCompleted = task.status === 'completed';
    const nowIso = new Date().toISOString();

    const updatedTask: Task = {
      ...task,
      status: isCompleted ? 'pending' : 'completed',
      completedAt: isCompleted ? null : nowIso,
      updatedAt: nowIso,
      revision: task.revision + 1,
    };

    await saveTaskToDb(updatedTask);

    await enqueueOperation({
      opId: `op-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      taskId: updatedTask.id,
      type: 'COMPLETE',
      patch: {
        status: updatedTask.status,
        completedAt: updatedTask.completedAt,
        updatedAt: updatedTask.updatedAt,
        revision: updatedTask.revision,
      },
      baseRevision: task.revision,
      timestamp: nowIso,
      retryCount: 0,
    });

    // If recurring task was marked complete, automatically generate next occurrence
    if (!isCompleted && task.recurrenceRule && task.recurrenceRule.type !== 'none' && task.dueAtUtc) {
      const currentDue = new Date(task.dueAtUtc);
      const nextDue = new Date(currentDue);

      if (task.recurrenceRule.type === 'daily') {
        nextDue.setDate(nextDue.getDate() + 1);
      } else if (task.recurrenceRule.type === 'weekly') {
        nextDue.setDate(nextDue.getDate() + 7);
      }

      const nextTaskId = `task-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const nextTask: Task = {
        ...task,
        id: nextTaskId,
        status: 'pending',
        completedAt: null,
        dueAtUtc: nextDue.toISOString(),
        createdAt: nowIso,
        updatedAt: nowIso,
        seriesId: task.seriesId || task.id,
        revision: 1,
      };

      await saveTaskToDb(nextTask);
      await enqueueOperation({
        opId: `op-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        taskId: nextTask.id,
        type: 'CREATE',
        patch: nextTask,
        baseRevision: 0,
        timestamp: nowIso,
        retryCount: 0,
      });
    }

    syncEngine.notifyLocalChange();
  };

  // Handle In-Progress toggle
  const handleToggleInProgress = async (task: Task) => {
    const nextStatus = task.status === 'in_progress' ? 'pending' : 'in_progress';
    const nowIso = new Date().toISOString();

    const updatedTask: Task = {
      ...task,
      status: nextStatus,
      updatedAt: nowIso,
      revision: task.revision + 1,
    };

    await saveTaskToDb(updatedTask);
    await enqueueOperation({
      opId: `op-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      taskId: updatedTask.id,
      type: 'UPDATE',
      patch: { status: nextStatus, updatedAt: nowIso, revision: updatedTask.revision },
      baseRevision: task.revision,
      timestamp: nowIso,
      retryCount: 0,
    });

    syncEngine.notifyLocalChange();
  };

  // Handle Edit
  const handleEdit = (task: Task) => {
    setTaskToEdit(task);
    setIsTaskModalOpen(true);
  };

  // Handle Soft-Delete / Archive
  const handleDelete = async (taskId: string) => {
    const task = tasks.find((t) => t.id === taskId);
    if (!task) return;

    const nowIso = new Date().toISOString();
    const archivedTask: Task = {
      ...task,
      archivedAt: nowIso,
      updatedAt: nowIso,
      revision: task.revision + 1,
    };

    await saveTaskToDb(archivedTask);
    await enqueueOperation({
      opId: `op-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      taskId: archivedTask.id,
      type: 'ARCHIVE',
      patch: { archivedAt: nowIso, updatedAt: nowIso, revision: archivedTask.revision },
      baseRevision: task.revision,
      timestamp: nowIso,
      retryCount: 0,
    });

    syncEngine.notifyLocalChange();
  };

  return (
    <div className="app-root">
      <Navbar
        syncStatus={syncStatus}
        user={authState.user}
        onOpenTaskModal={() => {
          setTaskToEdit(null);
          setIsTaskModalOpen(true);
        }}
        onOpenConflictModal={() => setIsConflictModalOpen(true)}
        onOpenExportImportModal={() => setIsExportImportModalOpen(true)}
        onOpenSettingsModal={() => setIsSettingsModalOpen(true)}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onLogout={logout}
        onTriggerSync={() => syncEngine.triggerSync()}
      />

      <main className="main-content">
        <TaskList
          tasks={tasks}
          onToggleComplete={handleToggleComplete}
          onToggleInProgress={handleToggleInProgress}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onOpenCreateModal={() => {
            setTaskToEdit(null);
            setIsTaskModalOpen(true);
          }}
        />
      </main>

      {/* Modals */}
      <TaskModal
        isOpen={isTaskModalOpen}
        onClose={() => {
          setIsTaskModalOpen(false);
          setTaskToEdit(null);
        }}
        taskToEdit={taskToEdit}
        ownerId={authState.user ? authState.user.uid : authState.localOwnerId}
      />

      <ConflictModal
        isOpen={isConflictModalOpen}
        onClose={() => setIsConflictModalOpen(false)}
      />

      <ExportImportModal
        isOpen={isExportImportModalOpen}
        onClose={() => setIsExportImportModalOpen(false)}
        taskCount={tasks.length}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        tasks={tasks}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
}

export default App;
