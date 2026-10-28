const SCRIPT_SRC = 'https://www.youtube.com/iframe_api';
const LOAD_TIMEOUT_MS = 12000;

let loadPromise = null;

export function loadYouTubeIframeApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error('YouTube IFrame API timed out'));
    }, LOAD_TIMEOUT_MS);

    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      window.clearTimeout(timer);
      if (typeof previous === 'function') previous();
      resolve(window.YT);
    };

    const script = document.createElement('script');
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onerror = () => {
      window.clearTimeout(timer);
      reject(new Error('YouTube IFrame API failed to load'));
    };
    document.head.appendChild(script);
  }).catch((error) => {
    loadPromise = null;
    throw error;
  });

  return loadPromise;
}

export const PLAYBACK_RATES = [0.8, 0.9, 1.0];
export const PLAYBACK_RATE_STORAGE_KEY = 'elp-playback-rate';

export function normalizePlaybackRate(value) {
  const rate = Number(value);
  return PLAYBACK_RATES.find((item) => Math.abs(item - rate) < 0.001) ?? 1;
}

export function applyPlaybackRate(player, rate) {
  if (!player || typeof player.setPlaybackRate !== 'function') return;
  player.setPlaybackRate(rate);
}
