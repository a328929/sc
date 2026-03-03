import clsx from 'clsx';
import type { UploadLog } from '../types/upload';
import { formatTime } from '../utils/formatters';

interface LogSectionProps {
  logs: UploadLog[];
}

export function LogSection({ logs }: LogSectionProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>4. 实时日志</h2>
        <p>记录上传过程事件，便于排查失败原因。</p>
      </div>

      {logs.length === 0 ? (
        <p className="empty-hint">暂无日志。</p>
      ) : (
        <ul className="log-list" role="list">
          {logs.map((log) => (
            <li className={clsx('log-item', `log-${log.level}`)} key={log.id}>
              <span className="log-time">{formatTime(log.timestamp)}</span>
              <span>{log.message}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
