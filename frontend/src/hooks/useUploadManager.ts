import { useMemo, useRef, useState } from 'react';
import {
  connectTaskWs,
  createTaskByUpload,
  getTaskDetail,
  getTaskEvents,
  pauseTask,
  startTask,
} from '../services/apiClient';
import type { UploadLog, UploadTaskSummary, UploadableFile } from '../types/upload';

const defaultSummary: UploadTaskSummary = {
  totalFiles: 0,
  completedFiles: 0,
  failedFiles: 0,
  totalBytes: 0,
  uploadedBytes: 0,
  status: 'pending',
};

export function useUploadManager() {
  const wsRef = useRef<WebSocket | null>(null);
  const [files, setFiles] = useState<UploadableFile[]>([]);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [logs, setLogs] = useState<UploadLog[]>([]);
  const [summary, setSummary] = useState<UploadTaskSummary>(defaultSummary);
  const [isUploading, setIsUploading] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const currentFile = useMemo(
    () => files.find((file) => file.stage === 'uploading') ?? files.find((file) => file.stage === 'pending'),
    [files],
  );

  const totalProgress = useMemo(() => {
    if (summary.totalBytes === 0) return 0;
    return (summary.uploadedBytes / summary.totalBytes) * 100;
  }, [summary]);

  function enqueue(selectedFiles: File[]): void {
    setPendingFiles((prev) => [...prev, ...selectedFiles]);
    const queuedFiles: UploadableFile[] = selectedFiles.map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
      name: file.name,
      size: file.size,
      type: file.type || 'text/plain',
      stage: 'pending',
      progress: 0,
      speedKbps: 0,
      uploadedBytes: 0,
    }));
    setFiles((prev) => [...prev, ...queuedFiles]);
    pushLog({ id: `queue-${Date.now()}`, level: 'info', message: `已加入队列：${selectedFiles.length} 个文件。`, timestamp: new Date().toISOString() });
  }

  async function refreshTask(taskId: number): Promise<void> {
    const detail = await getTaskDetail(taskId);
    setSummary(detail.summary);
    setFiles(detail.files);
    const events = await getTaskEvents(taskId);
    setLogs(events);
    setIsUploading(detail.summary.status === 'running');
    setIsPaused(detail.summary.status === 'paused');
  }

  async function startUpload(): Promise<void> {
    try {
      if (pendingFiles.length === 0 && !summary.id) {
        pushLog({ id: `warn-${Date.now()}`, level: 'warning', message: '请先选择至少一个文件。', timestamp: new Date().toISOString() });
        return;
      }

      let taskId = summary.id;
      if (!taskId) {
        taskId = await createTaskByUpload(`上传任务 ${new Date().toLocaleString('zh-CN')}`, pendingFiles);
        setPendingFiles([]);
      }
      await startTask(taskId);
      await refreshTask(taskId);

      wsRef.current?.close();
      wsRef.current = connectTaskWs(taskId, async () => {
        await refreshTask(taskId!);
      });
      setIsUploading(true);
      setIsPaused(false);
    } catch (error) {
      pushLog({ id: `error-${Date.now()}`, level: 'error', message: String(error), timestamp: new Date().toISOString() });
    }
  }

  async function pauseUpload(): Promise<void> {
    if (!summary.id) return;
    await pauseTask(summary.id);
    await refreshTask(summary.id);
  }

  async function resumeUpload(): Promise<void> {
    if (!summary.id) return;
    await startTask(summary.id);
    await refreshTask(summary.id);
  }

  function clearCompleted(): void {
    setFiles((prev) => prev.filter((file) => file.stage !== 'completed'));
  }

  function resetAll(): void {
    wsRef.current?.close();
    wsRef.current = null;
    setPendingFiles([]);
    setFiles([]);
    setSummary(defaultSummary);
    setLogs([]);
    setIsUploading(false);
    setIsPaused(false);
  }

  function pushLog(log: UploadLog): void {
    setLogs((prev) => [log, ...prev].slice(0, 400));
  }

  return {
    files,
    logs,
    summary,
    currentFile,
    totalProgress,
    isUploading,
    isPaused,
    enqueue,
    startUpload,
    pauseUpload,
    resumeUpload,
    clearCompleted,
    resetAll,
  };
}
