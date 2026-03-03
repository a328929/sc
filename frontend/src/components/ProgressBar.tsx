interface ProgressBarProps {
  label: string;
  progress: number;
  subLabel?: string;
  tone?: 'blue' | 'green' | 'purple';
}

export function ProgressBar({ label, progress, subLabel, tone = 'blue' }: ProgressBarProps) {
  const safeProgress = Math.min(Math.max(progress, 0), 100);

  return (
    <div className="progress-card">
      <div className="progress-head">
        <span>{label}</span>
        <span>{safeProgress.toFixed(1)}%</span>
      </div>
      <div className="progress-track" aria-label={label}>
        <div className={`progress-fill tone-${tone}`} style={{ width: `${safeProgress}%` }} />
      </div>
      {subLabel ? <p className="progress-sub-label">{subLabel}</p> : null}
    </div>
  );
}
