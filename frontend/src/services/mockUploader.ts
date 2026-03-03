import type { UploadLog, UploadTaskSummary, UploadableFile } from '../types/upload';

interface MockCallbacks {
  onFileUpdate: (file: UploadableFile) => void;
  onSummaryUpdate: (summary: UploadTaskSummary) => void;
  onLog: (log: UploadLog) => void;
}

interface RunningTask {
  timerIds: number[];
  isPaused: boolean;
}

export class MockUploader {
  private runningTask: RunningTask | null = null;

  start(files: UploadableFile[], callbacks: MockCallbacks): void {
    this.stop();

    const workingFiles = files.map((file) => ({ ...file }));
    const totalBytes = workingFiles.reduce((sum, file) => sum + file.size, 0);
    const timerIds: number[] = [];

    this.runningTask = { timerIds, isPaused: false };
    callbacks.onLog(this.makeLog('info', `任务已创建，共 ${workingFiles.length} 个文件。`));

    workingFiles.forEach((file, index) => {
      const delay = index * 250;
      const timerId = window.setTimeout(() => {
        this.runSingleFile(file, workingFiles, totalBytes, callbacks);
      }, delay);
      timerIds.push(timerId);
    });
  }

  pause(callbacks: Pick<MockCallbacks, 'onLog'>): void {
    if (!this.runningTask) return;
    this.runningTask.isPaused = true;
    callbacks.onLog(this.makeLog('warning', '任务已暂停。'));
  }

  resume(files: UploadableFile[], callbacks: MockCallbacks): void {
    if (!this.runningTask) {
      this.start(files, callbacks);
      return;
    }

    this.runningTask.isPaused = false;
    callbacks.onLog(this.makeLog('info', '任务继续执行。'));
  }

  stop(): void {
    if (!this.runningTask) return;

    this.runningTask.timerIds.forEach((timerId) => window.clearTimeout(timerId));
    this.runningTask = null;
  }

  private runSingleFile(
    file: UploadableFile,
    allFiles: UploadableFile[],
    totalBytes: number,
    callbacks: MockCallbacks,
  ): void {
    const runTick = () => {
      if (!this.runningTask) return;

      if (this.runningTask.isPaused) {
        const retryTimer = window.setTimeout(runTick, 500);
        this.runningTask.timerIds.push(retryTimer);
        return;
      }

      const chunkBytes = Math.floor(Math.random() * (90_000 - 20_000) + 20_000);
      const nextUploadedBytes = Math.min(file.uploadedBytes + chunkBytes, file.size);
      const progress = (nextUploadedBytes / file.size) * 100;

      file.uploadedBytes = nextUploadedBytes;
      file.speedKbps = chunkBytes / 1024;
      file.progress = progress;
      file.stage = nextUploadedBytes >= file.size ? 'completed' : 'uploading';

      callbacks.onFileUpdate({ ...file });
      callbacks.onSummaryUpdate(this.makeSummary(allFiles, totalBytes));

      if (file.stage === 'completed') {
        callbacks.onLog(this.makeLog('info', `文件已上传：${file.name}`));
        return;
      }

      const nextTimer = window.setTimeout(runTick, Math.floor(Math.random() * 180 + 120));
      this.runningTask?.timerIds.push(nextTimer);
    };

    callbacks.onLog(this.makeLog('info', `开始上传：${file.name}`));
    runTick();
  }

  private makeSummary(files: UploadableFile[], totalBytes: number): UploadTaskSummary {
    const completedFiles = files.filter((file) => file.stage === 'completed').length;
    const failedFiles = files.filter((file) => file.stage === 'failed').length;
    const uploadedBytes = files.reduce((sum, file) => sum + file.uploadedBytes, 0);

    return {
      totalFiles: files.length,
      completedFiles,
      failedFiles,
      totalBytes,
      uploadedBytes,
    };
  }

  private makeLog(level: UploadLog['level'], message: string): UploadLog {
    return {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      level,
      message,
      timestamp: new Date().toISOString(),
    };
  }
}
