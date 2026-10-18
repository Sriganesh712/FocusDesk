import React, { useState, useEffect } from 'react';
import {
  X,
  Calendar,
  AlertTriangle,
  Tag,
  Folder,
  Repeat,
  Bell,
  Save,
} from 'lucide-react';
import type { Task, Priority, RecurrenceType } from '../types/task';
import { saveTaskToDb, enqueueOperation } from '../db/indexedDb';
import { syncEngine } from '../sync/syncEngine';

interface TaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskToEdit?: Task | null;
  ownerId: string;
}

export const TaskModal: React.FC<TaskModalProps> = ({
  isOpen,
  onClose,
  taskToEdit,
  ownerId,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<Priority>('medium');
  const [category, setCategory] = useState('General');
  const [tagsInput, setTagsInput] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [dueTime, setDueTime] = useState('17:00');
  const [hasDueTime, setHasDueTime] = useState(false);
  const [remindBeforeMinutes, setRemindBeforeMinutes] = useState<number>(15);
  const [recurrence, setRecurrence] = useState<RecurrenceType>('none');

  useEffect(() => {
    if (taskToEdit) {
      setTitle(taskToEdit.title);
      setDescription(taskToEdit.description || '');
      setPriority(taskToEdit.priority);
      setCategory(taskToEdit.category || 'General');
      setTagsInput(taskToEdit.tags ? taskToEdit.tags.join(', ') : '');
      setRemindBeforeMinutes(taskToEdit.remindBeforeMinutes ?? 15);
      setRecurrence(taskToEdit.recurrenceRule?.type || 'none');

      if (taskToEdit.dueAtUtc) {
        const d = new Date(taskToEdit.dueAtUtc);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        setDueDate(`${yyyy}-${mm}-${dd}`);

        const hh = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        setDueTime(`${hh}:${min}`);
        setHasDueTime(true);
      } else {
        setDueDate('');
        setHasDueTime(false);
      }
    } else {
      // New task default
      setTitle('');
      setDescription('');
      setPriority('medium');
      setCategory('General');
      setTagsInput('');
      setRemindBeforeMinutes(15);
      setRecurrence('none');

      // Default due today at 18:00
      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      setDueDate(`${yyyy}-${mm}-${dd}`);
      setDueTime('18:00');
      setHasDueTime(true);
    }
  }, [taskToEdit, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    let dueAtUtc: string | null = null;
    if (hasDueTime && dueDate) {
      const [year, month, day] = dueDate.split('-').map(Number);
      const [hour, minute] = dueTime.split(':').map(Number);
      const localDate = new Date(year, month - 1, day, hour || 0, minute || 0, 0);
      dueAtUtc = localDate.toISOString();
    }

    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const nowIso = new Date().toISOString();

    if (taskToEdit) {
      // Update existing
      const updatedTask: Task = {
        ...taskToEdit,
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        category: category.trim() || 'General',
        tags,
        dueAtUtc,
        remindBeforeMinutes,
        recurrenceRule: recurrence !== 'none' ? { type: recurrence } : null,
        updatedAt: nowIso,
        revision: (taskToEdit.revision || 1) + 1,
      };

      await saveTaskToDb(updatedTask);
      await enqueueOperation({
        opId: `op-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        taskId: updatedTask.id,
        type: 'UPDATE',
        patch: updatedTask,
        baseRevision: taskToEdit.revision,
        timestamp: nowIso,
        retryCount: 0,
      });
    } else {
      // Create new
      const taskId = `task-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const newTask: Task = {
        id: taskId,
        ownerId,
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        status: 'pending',
        category: category.trim() || 'General',
        tags,
        dueAtUtc,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        remindBeforeMinutes,
        createdAt: nowIso,
        updatedAt: nowIso,
        completedAt: null,
        archivedAt: null,
        recurrenceRule: recurrence !== 'none' ? { type: recurrence } : null,
        seriesId: recurrence !== 'none' ? `series-${taskId}` : null,
        occurrenceKey: null,
        revision: 1,
      };

      await saveTaskToDb(newTask);
      await enqueueOperation({
        opId: `op-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        taskId: newTask.id,
        type: 'CREATE',
        patch: newTask,
        baseRevision: 0,
        timestamp: nowIso,
        retryCount: 0,
      });
    }

    syncEngine.notifyLocalChange();
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content card-glass" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{taskToEdit ? 'Edit Task' : 'Create New Task'}</h2>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>Task Title *</label>
            <input
              type="text"
              required
              placeholder="e.g. Verify STM32 SPI communication"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="form-input"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Description / Notes</label>
            <textarea
              rows={3}
              placeholder="Add key requirements, links, or notes..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="form-textarea"
            />
          </div>

          <div className="form-row">
            <div className="form-group flex-1">
              <label>
                <AlertTriangle size={14} className="label-icon" /> Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as Priority)}
                className="form-select"
              >
                <option value="critical">Critical (Highest)</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div className="form-group flex-1">
              <label>
                <Folder size={14} className="label-icon" /> Category
              </label>
              <input
                type="text"
                placeholder="e.g. Embedded, Work, Personal"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="form-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label>
              <Tag size={14} className="label-icon" /> Tags (comma separated)
            </label>
            <input
              type="text"
              placeholder="firmware, spi, test"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              className="form-input"
            />
          </div>

          {/* Due Date & Time */}
          <div className="form-section-box">
            <div className="form-section-title">
              <Calendar size={15} />
              <span>Deadline & Schedule</span>
              <label className="checkbox-toggle">
                <input
                  type="checkbox"
                  checked={hasDueTime}
                  onChange={(e) => setHasDueTime(e.target.checked)}
                />
                <span>Set Deadline</span>
              </label>
            </div>

            {hasDueTime && (
              <div className="form-row mt-2">
                <div className="form-group flex-1">
                  <label>Due Date</label>
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="form-input"
                  />
                </div>
                <div className="form-group flex-1">
                  <label>Due Time</label>
                  <input
                    type="time"
                    value={dueTime}
                    onChange={(e) => setDueTime(e.target.value)}
                    className="form-input"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Recurrence & Reminder */}
          <div className="form-row">
            <div className="form-group flex-1">
              <label>
                <Repeat size={14} className="label-icon" /> Recurrence
              </label>
              <select
                value={recurrence}
                onChange={(e) => setRecurrence(e.target.value as RecurrenceType)}
                className="form-select"
              >
                <option value="none">Does not repeat</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>

            <div className="form-group flex-1">
              <label>
                <Bell size={14} className="label-icon" /> Reminder Lead Time
              </label>
              <select
                value={remindBeforeMinutes}
                onChange={(e) => setRemindBeforeMinutes(Number(e.target.value))}
                className="form-select"
              >
                <option value={0}>At time of event</option>
                <option value={5}>5 minutes before</option>
                <option value={15}>15 minutes before</option>
                <option value={30}>30 minutes before</option>
                <option value={60}>1 hour before</option>
              </select>
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              <Save size={16} />
              <span>{taskToEdit ? 'Save Changes' : 'Create Task'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
