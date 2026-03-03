import clsx from 'clsx';
import type { UploadableFile } from '../types/upload';
import { formatBytes, formatPercent } from '../utils/formatters';

interface QueueSectionProps {
  files: UploadableFile[];
}

const stageTextMap: Record<UploadableFile['stage'], string> = {
  pending: '等待中',
  uploading: '上传中',
  completed: '已完成',
  failed: '失败',
  paused: '已暂停',
};

export function QueueSection({ files }: QueueSectionProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>3. 文件队列</h2>
        <p>逐项查看状态、速率和每个文件的进度。</p>
      </div>

      {files.length === 0 ? (
        <p className="empty-hint">暂无文件，请先选择文件并加入队列。</p>
      ) : (
        <div className="table-shell">
          <table className="queue-table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>大小</th>
                <th>状态</th>
                <th>进度</th>
                <th>速率</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.id}>
                  <td className="name-cell" title={file.name}>
                    {file.name}
                  </td>
                  <td>{formatBytes(file.size)}</td>
                  <td>
                    <span className={clsx('status-pill', `status-${file.stage}`)}>{stageTextMap[file.stage]}</span>
                  </td>
                  <td>
                    <div className="table-progress">
                      <div className="table-progress-track">
                        <div className="table-progress-fill" style={{ width: `${file.progress}%` }} />
                      </div>
                      <span>{formatPercent(file.progress)}</span>
                    </div>
                  </td>
                  <td>{file.stage === 'uploading' ? `${file.speedKbps.toFixed(1)} KB/s` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
