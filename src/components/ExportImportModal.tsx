import React, { useState, useRef } from 'react';
import {
  X,
  Download,
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import {
  exportTasksToJson,
  downloadJsonFile,
  validateImportPayload,
  applyImportedTasks,
} from '../utils/exportImport';
import type { Task } from '../types/task';
import { syncEngine } from '../sync/syncEngine';

interface ExportImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskCount: number;
}

export const ExportImportModal: React.FC<ExportImportModalProps> = ({
  isOpen,
  onClose,
  taskCount,
}) => {
  const [importStatus, setImportStatus] = useState<'idle' | 'preview' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [previewTasks, setPreviewTasks] = useState<Task[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    try {
      const json = await exportTasksToJson();
      const dateStr = new Date().toISOString().split('T')[0];
      downloadJsonFile(`focusdesk-backup-${dateStr}.json`, json);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        const result = validateImportPayload(parsed);

        if (!result.valid) {
          setErrorMessage(result.error || 'Invalid backup file');
          setImportStatus('error');
        } else {
          setPreviewTasks(result.tasks);
          setImportStatus('preview');
        }
      } catch (err: any) {
        setErrorMessage('Failed to parse JSON file');
        setImportStatus('error');
      }
    };
    reader.readAsText(file);
  };

  const handleApplyImport = async () => {
    if (previewTasks.length === 0) return;
    try {
      await applyImportedTasks(previewTasks);
      syncEngine.notifyLocalChange();
      setImportStatus('success');
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: any) {
      setErrorMessage(err.message);
      setImportStatus('error');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content card-glass" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Backup & Restore</h2>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body-section">
          {/* Export Section */}
          <div className="export-card card-glass p-4 mb-4">
            <div className="flex-row items-center justify-between">
              <div>
                <h4 className="flex items-center gap-2">
                  <Download size={18} className="text-primary" />
                  <span>Export Tasks Backup</span>
                </h4>
                <p className="text-muted text-sm mt-1">
                  Download all {taskCount} local tasks as an offline JSON snapshot.
                </p>
              </div>
              <button className="btn-primary" onClick={handleExport}>
                <Download size={16} />
                <span>Export JSON</span>
              </button>
            </div>
          </div>

          {/* Import Section */}
          <div className="import-card card-glass p-4">
            <h4 className="flex items-center gap-2 mb-2">
              <Upload size={18} className="text-primary" />
              <span>Restore from Backup</span>
            </h4>
            <p className="text-muted text-sm mb-3">
              Import a FocusDesk JSON file to restore tasks across browsers or devices.
            </p>

            <input
              type="file"
              ref={fileInputRef}
              accept=".json"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            {importStatus === 'idle' && (
              <button
                className="btn-secondary w-full"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileText size={16} />
                <span>Select JSON File</span>
              </button>
            )}

            {importStatus === 'preview' && (
              <div className="preview-box p-3 bg-base border rounded mt-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-success">
                    ✓ Valid backup: {previewTasks.length} task(s) ready
                  </span>
                  <button
                    className="btn-tiny"
                    onClick={() => {
                      setImportStatus('idle');
                      setPreviewTasks([]);
                    }}
                  >
                    Change file
                  </button>
                </div>
                <ul className="text-xs text-muted mb-3 max-h-32 overflow-y-auto">
                  {previewTasks.slice(0, 5).map((t, i) => (
                    <li key={i} className="truncate py-0.5">
                      • {t.title} ({t.priority})
                    </li>
                  ))}
                  {previewTasks.length > 5 && (
                    <li className="italic">+ {previewTasks.length - 5} more tasks</li>
                  )}
                </ul>

                <button className="btn-primary w-full" onClick={handleApplyImport}>
                  <RefreshCw size={16} />
                  <span>Restore {previewTasks.length} Tasks</span>
                </button>
              </div>
            )}

            {importStatus === 'success' && (
              <div className="p-3 text-center text-success flex items-center justify-center gap-2">
                <CheckCircle size={20} />
                <span>Tasks successfully restored!</span>
              </div>
            )}

            {importStatus === 'error' && (
              <div className="p-3 text-danger flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle size={18} />
                  <span className="text-sm">{errorMessage}</span>
                </div>
                <button
                  className="btn-tiny"
                  onClick={() => {
                    setImportStatus('idle');
                    setErrorMessage('');
                  }}
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
