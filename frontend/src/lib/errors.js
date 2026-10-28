export function messageFromBody(body) {
  const detail = body?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.message) {
    return String(detail.message);
  }
  if (Array.isArray(detail)) {
    const text = detail
      .map((item) => item?.msg || item?.message)
      .filter(Boolean)
      .join(' ');
    if (text) return text;
  }
  return '請求失敗，請稍後再試。';
}

export function codeFromBody(body) {
  const detail = body?.detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.code) {
    return String(detail.code);
  }
  return '';
}
