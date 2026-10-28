/** YouTube IFrame API player state for PLAYING. */
export const PLAYING = 1;

const END_EPSILON_SECONDS = 0.05;

/**
 * Pause once playback reaches the segment end.
 * A short suppress window avoids pausing during seek/replay.
 */
export function shouldPauseAtEnd({ currentTime, endTime, playerState, now = 0, suppressUntil = 0 }) {
  if (!Number.isFinite(currentTime) || !Number.isFinite(endTime)) return false;
  if (now < suppressUntil) return false;
  if (playerState !== PLAYING) return false;
  return currentTime >= endTime - END_EPSILON_SECONDS;
}
