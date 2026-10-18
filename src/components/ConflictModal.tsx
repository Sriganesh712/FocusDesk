import React, { useState, useEffect } from 'react';
import {
  X,
  AlertTriangle,
  CheckCircle,
  Copy,
  Laptop,
  Cloud,
} from 'lucide-react';
import type { ConflictRecord, Task } from '../types/task';
import {
  getUnresolvedConflicts,
  markConflictResolvedInDb,
  saveTaskToDb,
  enqueueOperation,
} from '../db/indexedDb';
import { syncEngine } from '../sync/syncEngine';

interface ConflictModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ConflictModal: React.FC<ConflictModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [conflicts, setConflicts] = useState<ConflictRecord[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  const loadConflicts = async () => {
    const list = await getUnresolvedConflicts();
    setConflicts(list);
    if (currentIndex >= list.length) {
      setCurrentIndex(Math.max(0, list.length - 1));
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConflicts();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const currentConflict = conflicts[currentIndex];

  const handleResolve = async (
    choice: 'keep_local' | 'keep_cloud' | 'keep_both',
  ) => {
    if (!currentConflict) return;

    const { conflictId, localTask, cloudTask } = currentConflict;
    const nowIso = new Date().toISOString();

    if (choice === 'keep_local') {
      // Overwrite cloud with local version
      const resolvedTask: Task = {
        ...localTask,
        updatedAt: nowIso,
        revision: Math.max(localTask.revision, cloudTask.revision) + 1,
      };
      await saveTaskToDb(resolvedTask);
      await enqueueOperation({
        opId: `op-res-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        taskId: resolvedTask.id,
        type: 'UPDATE',
        patch: resolvedTask,
        baseRevision: cloudTask.revision,
        timestamp: nowIso,
        retryCount: 0,
      });
    } else if (choice === 'keep_cloud') {
      // Accept cloud version
      await saveTaskToDb(cloudTask);
    } else if (choice === 'keep_both') {
      // Keep cloud version on existing ID
      await saveTaskToDb(cloudTask);
      // Fork local version as a new task
      const forkedTask: Task = {
        ...localTask,
        id: `task-fork-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        title: `${localTask.title} (Local Copy)`,
        updatedAt: nowIso,
        revision: 1,
      };
      await saveTaskToDb(forkedTask);
      await enqueueOperation({
        opId: `op-fork-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        taskId: forkedTask.id,
        type: 'CREATE',
        patch: forkedTask,
        baseRevision: 0,
        timestamp: nowIso,
        retryCount: 0,
      });
    }

    await markConflictResolvedInDb(conflictId);
    syncEngine.notifyLocalChange();
    await loadConflicts();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-conflict card-glass" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="flex-row items-center gap-2">
            <AlertTriangle className="text-warning" size={22} />
            <h2>Resolve Sync Conflict</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {conflicts.length === 0 ? (
          <div className="p-6 text-center">
            <CheckCircle size={44} className="text-success mx-auto mb-3" />
            <h3>No Unresolved Conflicts</h3>
            <p className="text-muted mt-2">All tasks are in sync with cloud storage.</p>
            <button className="btn-secondary mt-4" onClick={onClose}>
              Close
            </button>
          </div>
        ) : (
          <div className="conflict-body">
            <div className="conflict-stepper">
              <span>
                Conflict {currentIndex + 1} of {conflicts.length}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((i) => i - 1)}
                  className="btn-tiny"
                >
                  Previous
                </button>
                <button
                  disabled={currentIndex >= conflicts.length - 1}
                  onClick={() => setCurrentIndex((i) => i + 1)}
                  className="btn-tiny"
                >
                  Next
                </button>
              </div>
            </div>

            <div className="conflict-diff-grid">
              {/* Local Version Column */}
              <div className="conflict-card local-card">
                <div className="card-top-badge">
                  <Laptop size={16} />
                  <span>Local Device Version</span>
                </div>
                <div className="card-detail">
                  <div className="detail-item">
                    <span className="detail-label">Title</span>
                    <strong className="detail-val">{currentConflict.localTask.title}</strong>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Status / Priority</span>
                    <span className="detail-val">
                      {currentConflict.localTask.status} | {currentConflict.localTask.priority}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Due Date</span>
                    <span className="detail-val">
                      {currentConflict.localTask.dueAtUtc
                        ? new Date(currentConflict.localTask.dueAtUtc).toLocaleString()
                        : 'None'}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Notes</span>
                    <p className="detail-val text-muted">
                      {currentConflict.localTask.description || 'No notes'}
                    </p>
                  </div>
                  <div className="detail-item text-muted text-xs">
                    Updated: {new Date(currentConflict.localTask.updatedAt).toLocaleTimeString()} (rev {currentConflict.localTask.revision})
                  </div>
                </div>
                <button
                  className="btn-resolve btn-keep-local"
                  onClick={() => handleResolve('keep_local')}
                >
                  Keep Local Version
                </button>
              </div>

              {/* Cloud Version Column */}
              <div className="conflict-card cloud-card">
                <div className="card-top-badge">
                  <Cloud size={16} />
                  <span>Cloud / STM32 Version</span>
                </div>
                <div className="card-detail">
                  <div className="detail-item">
                    <span className="detail-label">Title</span>
                    <strong className="detail-val">{currentConflict.cloudTask.title}</strong>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Status / Priority</span>
                    <span className="detail-val">
                      {currentConflict.cloudTask.status} | {currentConflict.cloudTask.priority}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Due Date</span>
                    <span className="detail-val">
                      {currentConflict.cloudTask.dueAtUtc
                        ? new Date(currentConflict.cloudTask.dueAtUtc).toLocaleString()
                        : 'None'}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Notes</span>
                    <p className="detail-val text-muted">
                      {currentConflict.cloudTask.description || 'No notes'}
                    </p>
                  </div>
                  <div className="detail-item text-muted text-xs">
                    Updated: {new Date(currentConflict.cloudTask.updatedAt).toLocaleTimeString()} (rev {currentConflict.cloudTask.revision})
                  </div>
                </div>
                <button
                  className="btn-resolve btn-keep-cloud"
                  onClick={() => handleResolve('keep_cloud')}
                >
                  Keep Cloud Version
                </button>
              </div>
            </div>

            {/* Merge Option */}
            <div className="merge-both-banner">
              <div className="merge-info">
                <Copy size={18} />
                <span>Need both versions? Fork local edits into a separate task.</span>
              </div>
              <button
                className="btn-secondary btn-keep-both"
                onClick={() => handleResolve('keep_both')}
              >
                Keep Both Versions
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
