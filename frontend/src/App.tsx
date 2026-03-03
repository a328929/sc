import { Pause, Play, RotateCcw, Trash2 } from 'lucide-react';
import { FilePickerSection } from './sections/FilePickerSection';
import { LogSection } from './sections/LogSection';
import { OverviewSection } from './sections/OverviewSection';
import { QueueSection } from './sections/QueueSection';
import { useUploadManager } from './hooks/useUploadManager';

function App() {
  const {
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
  } = useUploadManager();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Telegram Uploader Dashboard</p>
          <h1>频道批量上传控制台</h1>
          <p className="subtitle">第三阶段已联通后端任务队列与 Telegram 实际上传。</p>
        </div>

        <div className="toolbar">
          <button className="btn primary" onClick={startUpload} type="button">
            <Play size={16} />
            开始上传
          </button>

          {isUploading && !isPaused ? (
            <button className="btn subtle" onClick={pauseUpload} type="button">
              <Pause size={16} />
              暂停
            </button>
          ) : (
            <button className="btn subtle" onClick={resumeUpload} type="button">
              <Play size={16} />
              继续
            </button>
          )}

          <button className="btn ghost" onClick={clearCompleted} type="button">
            <Trash2 size={16} />
            清理已完成
          </button>

          <button className="btn ghost" onClick={resetAll} type="button">
            <RotateCcw size={16} />
            重置任务
          </button>
        </div>
      </header>

      <main className="main-grid">
        <FilePickerSection onAddFiles={enqueue} />
        <OverviewSection currentFile={currentFile} summary={summary} totalProgress={totalProgress} />
        <QueueSection files={files} />
        <LogSection logs={logs} />
      </main>
    </div>
  );
}

export default App;
