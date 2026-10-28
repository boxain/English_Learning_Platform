import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

import { shouldPauseAtEnd } from '../lib/playback.js';
import { applyPlaybackRate, loadYouTubeIframeApi } from '../lib/youtube.js';

const SEEK_SUPPRESS_MS = 700;

function segmentKey(range) {
  return `${range.youtubeId}:${range.start}:${range.end}`;
}

export const YoutubeSegmentPlayer = forwardRef(function YoutubeSegmentPlayer(
  { youtubeId, start, end, rate },
  ref,
) {
  const frameRef = useRef(null);
  const playerRef = useRef(null);
  const rangeRef = useRef({ youtubeId, start, end, rate });
  const loadedKeyRef = useRef('');
  const suppressUntilRef = useRef(0);
  const [error, setError] = useState('');

  rangeRef.current = { youtubeId, start, end, rate };

  function loadRange(player, { autoplaySuppress = true } = {}) {
    const range = rangeRef.current;
    const key = segmentKey(range);
    if (!player || typeof player.loadVideoById !== 'function') return;
    if (loadedKeyRef.current === key) {
      applyPlaybackRate(player, range.rate);
      return;
    }
    loadedKeyRef.current = key;
    if (autoplaySuppress) suppressUntilRef.current = Date.now() + SEEK_SUPPRESS_MS;
    player.loadVideoById({
      videoId: range.youtubeId,
      startSeconds: range.start,
      endSeconds: range.end,
    });
    applyPlaybackRate(player, range.rate);
    window.setTimeout(() => {
      if (playerRef.current !== player || loadedKeyRef.current !== key) return;
      applyPlaybackRate(player, rangeRef.current.rate);
    }, 350);
  }

  useImperativeHandle(ref, () => ({
    replay() {
      const player = playerRef.current;
      const range = rangeRef.current;
      if (!player || typeof player.seekTo !== 'function') return;
      suppressUntilRef.current = Date.now() + SEEK_SUPPRESS_MS;
      player.seekTo(range.start, true);
      applyPlaybackRate(player, range.rate);
      player.playVideo();
    },
    getPlaybackRate() {
      const player = playerRef.current;
      if (!player || typeof player.getPlaybackRate !== 'function') return null;
      return player.getPlaybackRate();
    },
  }));

  useEffect(() => {
    let alive = true;
    let poll = 0;
    let created = null;
    const mount = document.createElement('div');
    mount.className = 'player-mount';
    frameRef.current?.appendChild(mount);
    loadedKeyRef.current = '';

    loadYouTubeIframeApi()
      .then((YT) => {
        if (!alive) return;
        created = new YT.Player(mount, {
          host: 'https://www.youtube.com',
          width: '100%',
          height: '100%',
          playerVars: {
            rel: 0,
            modestbranding: 1,
            playsinline: 1,
            cc_load_policy: 0,
            iv_load_policy: 3,
            controls: 1,
            origin: window.location.origin,
            enablejsapi: 1,
          },
          events: {
            onReady: (event) => {
              if (!alive) return;
              playerRef.current = event.target;
              try {
                event.target.unloadModule('captions');
              } catch {
                // The captions module is not always present.
              }
              loadRange(event.target);
              poll = window.setInterval(() => {
                const current = playerRef.current;
                if (!current || typeof current.getCurrentTime !== 'function') return;
                const range = rangeRef.current;
                const playing = current.getPlayerState() === YT.PlayerState.PLAYING;
                if (
                  shouldPauseAtEnd({
                    currentTime: current.getCurrentTime(),
                    endTime: range.end,
                    playerState: current.getPlayerState(),
                    now: Date.now(),
                    suppressUntil: suppressUntilRef.current,
                  })
                ) {
                  current.pauseVideo();
                  return;
                }
                if (!playing || typeof current.getPlaybackRate !== 'function') return;
                const actual = current.getPlaybackRate();
                if (typeof actual !== 'number' || Math.abs(actual - range.rate) >= 0.01) {
                  applyPlaybackRate(current, range.rate);
                }
              }, 120);
            },
            onError: (event) => {
              if (!alive) return;
              const code = event?.data;
              if (code === 101 || code === 150) {
                setError('無法在這裡播放這支影片。可能是影片不允許嵌入，或 YouTube 擋住了目前的網路。');
                return;
              }
              setError('無法播放這支 YouTube 影片。');
            },
          },
        });
      })
      .catch(() => {
        if (alive) setError('無法載入 YouTube 播放器。請檢查網路後重新整理。');
      });

    return () => {
      alive = false;
      window.clearInterval(poll);
      playerRef.current = null;
      loadedKeyRef.current = '';
      try {
        created?.destroy?.();
      } catch {
        // The iframe may already have been removed.
      }
      frameRef.current?.replaceChildren();
    };
    // The player instance follows the YouTube video. Segment bounds reload below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [youtubeId]);

  useEffect(() => {
    loadRange(playerRef.current);
    // loadRange reads the latest bounds from rangeRef.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [youtubeId, start, end]);

  useEffect(() => {
    applyPlaybackRate(playerRef.current, rate);
  }, [rate]);

  return (
    <div className="player-frame">
      <div ref={frameRef} className="player-host" />
      {error ? <p className="player-error">{error}</p> : null}
    </div>
  );
});
