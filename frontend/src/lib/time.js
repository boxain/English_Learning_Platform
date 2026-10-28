/** Format a timestamp in seconds as m:ss.s for practice ranges. */
export function formatTimestamp(value) {
  const total = Number.isFinite(value) ? Math.max(0, value) : 0;
  const rounded = Math.round(total * 10) / 10;
  const minutes = Math.floor(rounded / 60);
  const seconds = rounded - minutes * 60;
  const secondsText = seconds.toFixed(1).padStart(4, '0');
  return `${minutes}:${secondsText}`;
}

export function formatRange(start, end) {
  return `${formatTimestamp(start)}–${formatTimestamp(end)}`;
}

export function formatDuration(start, end) {
  const seconds = Number.isFinite(end - start) ? Math.max(0, end - start) : 0;
  return `${(Math.round(seconds * 10) / 10).toFixed(1)} 秒`;
}
