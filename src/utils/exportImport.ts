import type { Task } from '../types/task';
import { getAllTasksFromDb, saveTasksToDb } from '../db/indexedDb';

export interface ExportData {
  version: 1;
  exportedAt: string;
  source: 'FocusDesk Web';
  taskCount: number;
  tasks: Task[];
}

export async function exportTasksToJson(): Promise<string> {
  const tasks = await getAllTasksFromDb();
  const exportPayload: ExportData = {
    version: 1,
    exportedAt: new Date().toISOString(),
    source: 'FocusDesk Web',
    taskCount: tasks.length,
    tasks,
  };
  return JSON.stringify(exportPayload, null, 2);
}

export function downloadJsonFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function validateImportPayload(raw: any): { valid: boolean; tasks: Task[]; error?: string } {
  if (!raw || typeof raw !== 'object') {
    return { valid: false, tasks: [], error: 'Invalid JSON payload structure' };
  }

  const tasks = Array.isArray(raw.tasks) ? raw.tasks : Array.isArray(raw) ? raw : null;
  if (!tasks) {
    return { valid: false, tasks: [], error: 'No tasks array found in import data' };
  }

  const validTasks: Task[] = [];
  for (const t of tasks) {
    if (!t.id || typeof t.id !== 'string') continue;
    if (!t.title || typeof t.title !== 'string') continue;

    validTasks.push({
      id: t.id,
      ownerId: t.ownerId || 'imported',
      title: t.title,
      description: t.description || '',
      priority: ['critical', 'high', 'medium', 'low'].includes(t.priority) ? t.priority : 'medium',
      status: ['pending', 'in_progress', 'completed'].includes(t.status) ? t.status : 'pending',
      category: t.category || 'General',
      tags: Array.isArray(t.tags) ? t.tags : [],
      dueAtUtc: t.dueAtUtc || null,
      timezone: t.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      remindBeforeMinutes: typeof t.remindBeforeMinutes === 'number' ? t.remindBeforeMinutes : 0,
      createdAt: t.createdAt || new Date().toISOString(),
      updatedAt: t.updatedAt || new Date().toISOString(),
      completedAt: t.completedAt || null,
      archivedAt: t.archivedAt || null,
      recurrenceRule: t.recurrenceRule || null,
      seriesId: t.seriesId || null,
      occurrenceKey: t.occurrenceKey || null,
      revision: typeof t.revision === 'number' ? t.revision : 1,
    });
  }

  if (validTasks.length === 0) {
    return { valid: false, tasks: [], error: 'No valid task records could be parsed' };
  }

  return { valid: true, tasks: validTasks };
}

export async function applyImportedTasks(tasks: Task[]): Promise<number> {
  await saveTasksToDb(tasks);
  return tasks.length;
}
