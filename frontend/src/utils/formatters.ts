export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;

  return `${value.toFixed(exponent === 0 ? 0 : 2)} ${units[exponent]}`;
}

export function formatPercent(value: number): string {
  return `${Math.min(Math.max(value, 0), 100).toFixed(1)}%`;
}

export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
