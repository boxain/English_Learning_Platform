const MUSIC_NOTES = /[♪♫♬♩]+/g;

/** Practice text without lyric note markers. */
export function practiceText(value) {
  if (typeof value !== 'string') return '';
  return value.replace(MUSIC_NOTES, ' ').replace(/\s+/g, ' ').trim();
}
