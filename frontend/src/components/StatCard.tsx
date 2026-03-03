import type { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string;
  hint?: string;
  icon: ReactNode;
}

export function StatCard({ title, value, hint, icon }: StatCardProps) {
  return (
    <article className="stat-card">
      <div className="stat-icon">{icon}</div>
      <div>
        <p className="stat-title">{title}</p>
        <h3 className="stat-value">{value}</h3>
        {hint ? <p className="stat-hint">{hint}</p> : null}
      </div>
    </article>
  );
}
