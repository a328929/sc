import { BarChart3, CheckCircle2, HardDrive, XCircle } from 'lucide-react';
import { ProgressBar } from '../components/ProgressBar';
import { StatCard } from '../components/StatCard';
import type { UploadTaskSummary, UploadableFile } from '../types/upload';
import { formatBytes } from '../utils/formatters';

interface OverviewSectionProps {
  summary: UploadTaskSummary;
  totalProgress: number;
  currentFile?: UploadableFile;
}

export function OverviewSection({ summary, totalProgress, currentFile }: OverviewSectionProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>2. 上传总览</h2>
        <p>展示总任务进度与当前文件进度。</p>
      </div>

      <div className="stats-grid">
        <StatCard
          title="队列总数"
          value={`${summary.totalFiles} 个`}
          hint="已加入上传任务"
          icon={<BarChart3 size={20} />}
        />
        <StatCard
          title="已完成"
          value={`${summary.completedFiles} 个`}
          hint="上传成功文件"
          icon={<CheckCircle2 size={20} />}
        />
        <StatCard
          title="失败"
          value={`${summary.failedFiles} 个`}
          hint="可单独重试"
          icon={<XCircle size={20} />}
        />
        <StatCard
          title="数据量"
          value={formatBytes(summary.totalBytes)}
          hint={`${formatBytes(summary.uploadedBytes)} 已传输`}
          icon={<HardDrive size={20} />}
        />
      </div>

      <div className="progress-stack">
        <ProgressBar
          label="总体任务进度"
          progress={totalProgress}
          subLabel={`${summary.completedFiles}/${summary.totalFiles} 文件完成`}
          tone="purple"
        />
        <ProgressBar
          label="当前文件进度"
          progress={currentFile?.progress ?? 0}
          subLabel={
            currentFile
              ? `${currentFile.name} · ${formatBytes(currentFile.uploadedBytes)} / ${formatBytes(currentFile.size)}`
              : '暂无进行中的文件'
          }
          tone="green"
        />
      </div>
    </section>
  );
}
