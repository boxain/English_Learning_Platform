import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { YoutubeSegmentPlayer } from '../components/YoutubeSegmentPlayer.jsx';
import { getVideo } from '../api.js';
import { formatRange } from '../lib/time.js';
import { PLAYBACK_RATES } from '../lib/youtube.js';

const MODES = [
  { id: 'off', label: '無字幕' },
  { id: 'en', label: '英文字幕' },
  { id: 'both', label: '英文＋中文' },
];

export function PracticePage() {
  const { id, position } = useParams();
  const playerRef = useRef(null);
  const [video, setVideo] = useState(null);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('off');
  const [rate, setRate] = useState(1);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState('');

  useEffect(() => {
    let alive = true;
    setVideo(null);
    setError('');
    getVideo(id)
      .then((data) => {
        if (alive) setVideo(data);
      })
      .catch((err) => {
        if (alive) setError(err.message);
      });
    return () => {
      alive = false;
    };
  }, [id]);

  useEffect(() => {
    setMode('off');
    setCopied(false);
    setCopyError('');
  }, [id, position]);

  useEffect(() => {
    if (!copied) return undefined;
    const timer = window.setTimeout(() => setCopied(false), 1200);
    return () => window.clearTimeout(timer);
  }, [copied]);

  if (error) {
    return (
      <div className="stack">
        <Link className="back-link" to={`/videos/${id}`}>
          片段列表
        </Link>
        <p className="banner" role="alert">
          {error}
        </p>
      </div>
    );
  }

  if (!video) return <p className="muted">正在準備這一段…</p>;

  const segments = [...video.segments].sort((a, b) => a.position - b.position);
  const index = segments.findIndex((segment) => String(segment.position) === String(position));
  const segment = index >= 0 ? segments[index] : null;

  if (!segment) {
    return (
      <div className="stack">
        <Link className="back-link" to={`/videos/${video.id}`}>
          片段列表
        </Link>
        <p className="banner" role="alert">
          找不到這個片段。
        </p>
      </div>
    );
  }

  const previous = index > 0 ? segments[index - 1] : null;
  const next = index < segments.length - 1 ? segments[index + 1] : null;
  const translation = segment.translation_zh;

  async function copyEnglish() {
    setCopyError('');
    try {
      await navigator.clipboard.writeText(segment.text);
      setCopied(true);
      return;
    } catch {
      // Some browsers block the async clipboard API until a fallback runs.
    }
    try {
      const area = document.createElement('textarea');
      area.value = segment.text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.left = '-9999px';
      document.body.appendChild(area);
      area.select();
      const copiedOk = document.execCommand('copy');
      area.remove();
      if (!copiedOk) throw new Error('copy failed');
      setCopied(true);
    } catch {
      setCopied(false);
      setCopyError('無法複製');
    }
  }

  return (
    <div className="practice-layout">
      <section className="practice-main">
        <Link className="back-link" to={`/videos/${video.id}`}>
          片段列表
        </Link>
        <div className="practice-heading">
          <h1>{video.title || video.youtube_id}</h1>
          <p>
            第 {index + 1} / {segments.length} 段 · {formatRange(segment.start_time, segment.end_time)}
          </p>
        </div>

        <YoutubeSegmentPlayer
          ref={playerRef}
          youtubeId={video.youtube_id}
          start={segment.start_time}
          end={segment.end_time}
          rate={rate}
        />

        <div className="transport">
          <div className="transport-nav">
            {previous ? (
              <Link className="button button-secondary" to={`/videos/${video.id}/segments/${previous.position}`}>
                上一段
              </Link>
            ) : (
              <button type="button" className="button button-secondary" disabled>
                上一段
              </button>
            )}
            <button type="button" className="button" onClick={() => playerRef.current?.replay()}>
              重播
            </button>
            {next ? (
              <Link className="button button-secondary" to={`/videos/${video.id}/segments/${next.position}`}>
                下一段
              </Link>
            ) : (
              <button type="button" className="button button-secondary" disabled>
                下一段
              </button>
            )}
          </div>
          <div className="speed-group" role="group" aria-label="播放速度">
            {PLAYBACK_RATES.map((value) => (
              <button
                key={value}
                type="button"
                className="speed-button"
                aria-pressed={rate === value}
                onClick={() => setRate(value)}
              >
                {value.toFixed(1)}
              </button>
            ))}
          </div>
        </div>

        {mode !== 'off' ? (
          <div className="subtitle-panel">
            <div className="subtitle-en-row">
              <p className="subtitle-en">{segment.text}</p>
              <button type="button" className="copy-button" onClick={copyEnglish}>
                {copied ? '已複製' : '複製'}
              </button>
            </div>
            {copyError ? (
              <p className="copy-error" role="status">
                {copyError}
              </p>
            ) : null}
            {mode === 'both' ? (
              translation ? (
                <p className="subtitle-zh">{translation}</p>
              ) : (
                <p className="notice" role="status">
                  目前沒有這段的中文翻譯。未設定 OPENAI_API_KEY 時，仍可只用英文練習。
                </p>
              )
            ) : null}
          </div>
        ) : null}
      </section>

      <aside className="mode-sidebar">
        <fieldset>
          <legend>字幕</legend>
          {MODES.map((item) => (
            <label key={item.id} className={mode === item.id ? 'mode-option is-selected' : 'mode-option'}>
              <input
                type="radio"
                name="subtitle-mode"
                value={item.id}
                checked={mode === item.id}
                onChange={() => setMode(item.id)}
              />
              <span>{item.label}</span>
            </label>
          ))}
        </fieldset>
        <p className="sidebar-note">進入片段時不顯示字幕，可在這裡打開。</p>
      </aside>
    </div>
  );
}
