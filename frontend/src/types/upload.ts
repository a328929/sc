export type FileStage = 'pending' | 'uploading' | 'completed' | 'failed' | 'paused';

export interface UploadableFile {
  id: string;
  name: string;
  size: number;
  type: string;
  stage: FileStage;
  progress: number;
  speedKbps: number;
  uploadedBytes: number;
  error?: string;
}

export interface UploadTaskSummary {
  id?: number;
  totalFiles: number;
  completedFiles: number;
  failedFiles: number;
  totalBytes: number;
  uploadedBytes: number;
  status?: string;
}

export interface UploadLog {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}
