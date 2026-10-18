import React, { useState, useMemo } from 'react';
import {
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle,
  Layers,
  Search,
  Filter,
  ArrowUpDown,
  Sparkles,
} from 'lucide-react';
import type { Task } from '../types/task';
import { TaskItem } from './TaskItem';

export type TaskTab = 'today' | 'upcoming' | 'overdue' | 'completed' | 'all';

interface TaskListProps {
  tasks: Task[];
  onToggleComplete: (task: Task) => void;
  onToggleInProgress: (task: Task) => void;
  onEdit: (task: Task) => void;
  onDelete: (taskId: string) => void;
  onOpenCreateModal: () => void;
}

export const TaskList: React.FC<TaskListProps> = ({
  tasks,
  onToggleComplete,
  onToggleInProgress,
  onEdit,
  onDelete,
  onOpenCreateModal,
}) => {
  const [activeTab, setActiveTab] = useState<TaskTab>('today');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'due' | 'priority' | 'updated'>('due');

  // Derive unique categories
  const categories = useMemo(() => {
    const set = new Set<string>();
    tasks.forEach((t) => {
      if (t.category && !t.archivedAt) {
        set.add(t.category);
      }
    });
    return Array.from(set).sort();
  }, [tasks]);

  // Tab counts
  const counts = useMemo(() => {
    const now = new Date();
    const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);

    let today = 0;
    let upcoming = 0;
    let overdue = 0;
    let completed = 0;
    let all = 0;

    tasks.forEach((t) => {
      if (t.archivedAt) return;
      all++;
      if (t.status === 'completed') {
        completed++;
        return;
      }

      if (t.dueAtUtc) {
        const due = new Date(t.dueAtUtc);
        if (due < now) {
          overdue++;
          today++; // Overdue tasks roll into Today
        } else if (due <= todayEnd) {
          today++;
        } else {
          upcoming++;
        }
      } else {
        // No due date defaults to Today
        today++;
      }
    });

    return { today, upcoming, overdue, completed, all };
  }, [tasks]);

  // Filtered and sorted tasks
  const filteredTasks = useMemo(() => {
    const now = new Date();
    const todayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);

    return tasks
      .filter((t) => {
        if (t.archivedAt) return false;

        // Search query filter
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchTitle = t.title.toLowerCase().includes(q);
          const matchDesc = t.description?.toLowerCase().includes(q) ?? false;
          const matchCat = t.category?.toLowerCase().includes(q) ?? false;
          const matchTags = t.tags?.some((tag) => tag.toLowerCase().includes(q)) ?? false;
          if (!matchTitle && !matchDesc && !matchCat && !matchTags) return false;
        }

        // Category filter
        if (selectedCategory !== 'all' && t.category !== selectedCategory) {
          return false;
        }

        // Tab filter
        switch (activeTab) {
          case 'today':
            if (t.status === 'completed') return false;
            if (!t.dueAtUtc) return true;
            return new Date(t.dueAtUtc) <= todayEnd;
          case 'upcoming':
            if (t.status === 'completed') return false;
            if (!t.dueAtUtc) return false;
            return new Date(t.dueAtUtc) > todayEnd;
          case 'overdue':
            if (t.status === 'completed') return false;
            if (!t.dueAtUtc) return false;
            return new Date(t.dueAtUtc) < now;
          case 'completed':
            return t.status === 'completed';
          case 'all':
          default:
            return true;
        }
      })
      .sort((a, b) => {
        if (sortBy === 'priority') {
          const priorityWeight = { critical: 4, high: 3, medium: 2, low: 1 };
          return (priorityWeight[b.priority] || 0) - (priorityWeight[a.priority] || 0);
        }
        if (sortBy === 'updated') {
          return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
        }
        // Default sort by due date
        if (!a.dueAtUtc && !b.dueAtUtc) return 0;
        if (!a.dueAtUtc) return 1;
        if (!b.dueAtUtc) return -1;
        return new Date(a.dueAtUtc).getTime() - new Date(b.dueAtUtc).getTime();
      });
  }, [tasks, activeTab, selectedCategory, searchQuery, sortBy]);

  return (
    <div className="tasklist-container">
      {/* Top Filter and Search Bar */}
      <div className="filter-bar">
        {/* Navigation Tabs */}
        <div className="tabs-container">
          <button
            className={`tab-btn ${activeTab === 'today' ? 'active' : ''}`}
            onClick={() => setActiveTab('today')}
          >
            <Calendar size={15} />
            <span>Today</span>
            <span className="tab-badge">{counts.today}</span>
          </button>

          <button
            className={`tab-btn ${activeTab === 'upcoming' ? 'active' : ''}`}
            onClick={() => setActiveTab('upcoming')}
          >
            <Clock size={15} />
            <span>Upcoming</span>
            <span className="tab-badge">{counts.upcoming}</span>
          </button>

          {counts.overdue > 0 && (
            <button
              className={`tab-btn tab-btn-overdue ${activeTab === 'overdue' ? 'active' : ''}`}
              onClick={() => setActiveTab('overdue')}
            >
              <AlertCircle size={15} />
              <span>Overdue</span>
              <span className="tab-badge badge-overdue">{counts.overdue}</span>
            </button>
          )}

          <button
            className={`tab-btn ${activeTab === 'completed' ? 'active' : ''}`}
            onClick={() => setActiveTab('completed')}
          >
            <CheckCircle size={15} />
            <span>Completed</span>
            <span className="tab-badge">{counts.completed}</span>
          </button>

          <button
            className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            <Layers size={15} />
            <span>All Tasks</span>
            <span className="tab-badge">{counts.all}</span>
          </button>
        </div>

        {/* Search & Sort Controls */}
        <div className="search-sort-group">
          <div className="search-box">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search tasks, tags, notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button className="clear-search-btn" onClick={() => setSearchQuery('')}>
                ×
              </button>
            )}
          </div>

          <div className="sort-box">
            <ArrowUpDown size={15} className="sort-icon" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="sort-select"
            >
              <option value="due">Sort by Due Date</option>
              <option value="priority">Sort by Priority</option>
              <option value="updated">Sort by Recent</option>
            </select>
          </div>
        </div>
      </div>

      {/* Category Pills Bar */}
      {categories.length > 0 && (
        <div className="category-scroll-bar">
          <Filter size={14} className="category-filter-icon" />
          <button
            className={`category-filter-pill ${selectedCategory === 'all' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('all')}
          >
            All Categories
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              className={`category-filter-pill ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* Task Items List */}
      <div className="tasks-scroll-area">
        {filteredTasks.length > 0 ? (
          <div className="tasks-grid">
            {filteredTasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                onToggleComplete={onToggleComplete}
                onToggleInProgress={onToggleInProgress}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state card-glass">
            <Sparkles size={40} className="empty-state-icon" />
            <h3>No tasks found</h3>
            <p>
              {searchQuery
                ? `No tasks matching "${searchQuery}"`
                : activeTab === 'today'
                ? "You're all caught up for today! Add a task to focus on."
                : activeTab === 'overdue'
                ? 'No overdue tasks. Great job staying on schedule!'
                : 'No tasks in this view.'}
            </p>
            <button className="btn-primary mt-4" onClick={onOpenCreateModal}>
              + Create a Task
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
