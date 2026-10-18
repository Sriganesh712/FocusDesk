import React from 'react';
import {
  CheckCircle2,
  Circle,
  Clock,
  Repeat,
  Tag,
  Edit3,
  Trash2,
  AlertCircle,
  PlayCircle,
} from 'lucide-react';
import type { Task, Priority } from '../types/task';

interface TaskItemProps {
  task: Task;
  onToggleComplete: (task: Task) => void;
  onToggleInProgress: (task: Task) => void;
  onEdit: (task: Task) => void;
  onDelete: (taskId: string) => void;
}

export const TaskItem: React.FC<TaskItemProps> = ({
  task,
  onToggleComplete,
  onToggleInProgress,
  onEdit,
  onDelete,
}) => {
  const isCompleted = task.status === 'completed';
  const isInProgress = task.status === 'in_progress';

  // Format relative deadline
  const formatDeadline = (utcString?: string | null) => {
    if (!utcString) return null;
    const due = new Date(utcString);
    const now = new Date();
    const diffMs = due.getTime() - now.getTime();
    const diffHours = Math.round(diffMs / (1000 * 60 * 60));
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

    const isOverdue = diffMs < 0 && !isCompleted;

    let text = '';
    if (isOverdue) {
      const absHours = Math.abs(diffHours);
      if (absHours < 24) {
        text = `Overdue by ${absHours}h`;
      } else {
        text = `Overdue by ${Math.abs(diffDays)}d`;
      }
    } else if (diffHours >= 0 && diffHours < 24) {
      text = `Due today at ${due.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (diffDays === 1) {
      text = `Due tomorrow at ${due.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else {
      text = `Due ${due.toLocaleDateString([], { month: 'short', day: 'numeric' })} at ${due.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }

    return { text, isOverdue, isNear: diffHours >= 0 && diffHours <= 24 };
  };

  const deadlineInfo = formatDeadline(task.dueAtUtc);

  const getPriorityClass = (priority: Priority) => {
    switch (priority) {
      case 'critical':
        return 'priority-critical';
      case 'high':
        return 'priority-high';
      case 'medium':
        return 'priority-medium';
      case 'low':
        return 'priority-low';
      default:
        return 'priority-medium';
    }
  };

  return (
    <div className={`task-card card-glass ${isCompleted ? 'task-completed' : ''} ${deadlineInfo?.isOverdue ? 'task-overdue-border' : ''}`}>
      <div className="task-left">
        {/* Touch-friendly completion toggle */}
        <button
          className="btn-checkbox"
          onClick={() => onToggleComplete(task)}
          title={isCompleted ? 'Mark pending' : 'Mark complete'}
          aria-label={isCompleted ? 'Mark pending' : 'Mark complete'}
        >
          {isCompleted ? (
            <CheckCircle2 size={24} className="checkbox-icon checked" />
          ) : (
            <Circle size={24} className="checkbox-icon unchecked" />
          )}
        </button>

        <div className="task-content">
          <div className="task-header-row">
            <span className={`task-title ${isCompleted ? 'line-through' : ''}`}>
              {task.title}
            </span>
            <span className={`priority-badge ${getPriorityClass(task.priority)}`}>
              {task.priority.toUpperCase()}
            </span>
            {task.recurrenceRule && task.recurrenceRule.type !== 'none' && (
              <span className="recurrence-badge" title={`Recurring: ${task.recurrenceRule.type}`}>
                <Repeat size={12} />
                <span>{task.recurrenceRule.type}</span>
              </span>
            )}
            {isInProgress && !isCompleted && (
              <span className="status-badge-inprogress">
                <PlayCircle size={12} />
                <span>IN PROGRESS</span>
              </span>
            )}
          </div>

          {task.description && (
            <p className="task-description">{task.description}</p>
          )}

          <div className="task-metadata-row">
            {task.category && (
              <span className="category-pill">{task.category}</span>
            )}

            {task.tags && task.tags.length > 0 && (
              <div className="tags-container">
                {task.tags.map((t, idx) => (
                  <span key={idx} className="tag-pill">
                    <Tag size={10} />
                    {t}
                  </span>
                ))}
              </div>
            )}

            {deadlineInfo && (
              <span
                className={`deadline-pill ${
                  deadlineInfo.isOverdue
                    ? 'deadline-overdue'
                    : deadlineInfo.isNear
                    ? 'deadline-near'
                    : 'deadline-normal'
                }`}
              >
                {deadlineInfo.isOverdue ? (
                  <AlertCircle size={13} />
                ) : (
                  <Clock size={13} />
                )}
                <span>{deadlineInfo.text}</span>
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="task-actions">
        {!isCompleted && (
          <button
            className={`action-btn ${isInProgress ? 'action-active' : ''}`}
            onClick={() => onToggleInProgress(task)}
            title={isInProgress ? 'Pause progress' : 'Start progress'}
          >
            <PlayCircle size={18} />
          </button>
        )}
        <button
          className="action-btn"
          onClick={() => onEdit(task)}
          title="Edit task"
        >
          <Edit3 size={18} />
        </button>
        <button
          className="action-btn action-danger"
          onClick={() => onDelete(task.id)}
          title="Archive/Delete task"
        >
          <Trash2 size={18} />
        </button>
      </div>
    </div>
  );
};
