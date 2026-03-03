import type { UploadLog, UploadTaskSummary, UploadableFile } from '../types/upload';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8080/api';

type TaskDetailResponse = {
  id: number;
  status: string;
  total_files: number;
  completed_files: number;
  failed_files: number;
  total_bytes: number;
  uploaded_bytes: number;
  files: Array<{
    id: number;
    name: string;
    size: number;
    mime_type?: string;
    status: UploadableFile['stage'];
    progress: number;
    uploaded_bytes: number;
    speed_kbps: number;
    error_message?: string;
  }>;
};

const UPLOAD_BATCH_SIZE = 40;

async function uploadTaskBatch(label: string, files: File[], taskId?: number): Promise<number> {
  const formData = new FormData();
  formData.append('label', label);
  if (taskId) formData.append('task_id', String(taskId));
  files.forEach((file) => formData.append('files', file));

  const response = await fetch(`${API_BASE}/tasks/upload`, { method: 'POST', body: formData });
  if (!response.ok) throw new Error(`创建任务失败: ${response.status}`);
  const body = await response.json();
  return body.task.id as number;
}

export async function createTaskByUpload(label: string, files: File[]): Promise<number> {
  if (files.length === 0) throw new Error('至少需要一个文件');

  let taskId: number | undefined;
  for (let i = 0; i < files.length; i += UPLOAD_BATCH_SIZE) {
    const batch = files.slice(i, i + UPLOAD_BATCH_SIZE);
    taskId = await uploadTaskBatch(label, batch, taskId);
  }

  if (!taskId) throw new Error('创建任务失败: 无任务ID');
  return taskId;
}

export async function startTask(taskId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/start`, { method: 'POST' });
  if (!response.ok) throw new Error(`启动任务失败: ${response.status}`);
}

export async function pauseTask(taskId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/pause`, { method: 'POST' });
  if (!response.ok) throw new Error(`暂停任务失败: ${response.status}`);
}

export async function getTaskDetail(taskId: number): Promise<{ summary: UploadTaskSummary; files: UploadableFile[] }> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!response.ok) throw new Error(`任务详情获取失败: ${response.status}`);
  const body = (await response.json()) as TaskDetailResponse;

  return {
    summary: {
      id: body.id,
      status: body.status,
      totalFiles: body.total_files,
      completedFiles: body.completed_files,
      failedFiles: body.failed_files,
      totalBytes: body.total_bytes,
      uploadedBytes: body.uploaded_bytes,
    },
    files: body.files.map((file) => ({
      id: String(file.id),
      name: file.name,
      size: file.size,
      type: file.mime_type ?? 'application/octet-stream',
      stage: file.status,
      progress: file.progress,
      speedKbps: file.speed_kbps,
      uploadedBytes: file.uploaded_bytes,
      error: file.error_message,
    })),
  };
}

export async function getTaskEvents(taskId: number): Promise<UploadLog[]> {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/events`);
  if (!response.ok) return [];
  const body = (await response.json()) as Array<{ id: number; level: UploadLog['level']; message: string; created_at: string }>;
  return body.map((event) => ({
    id: String(event.id),
    level: event.level,
    message: event.message,
    timestamp: event.created_at,
  }));
}

export function connectTaskWs(taskId: number, onMessage: (data: unknown) => void): WebSocket {
  const wsBase = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://').replace('/api', '');
  const ws = new WebSocket(`${wsBase}/api/ws/tasks/${taskId}`);
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      // noop
    }
  };
  ws.onopen = () => ws.send('ping');
  return ws;
}
