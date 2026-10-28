import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { createVideo, listVideos } from '../api.js';

function sourceLabel(source) {
  if (source === 'manual') return '手動字幕';
  if (source === 'generated') return '自動字幕';
  return source || '字幕';
}

export function VideoListPage() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    listVideos()
      .then((data) => {
        if (alive) setVideos(data);
      })
      .catch((err) => {
        if (alive) setError(err.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  async function onSubmit(event) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    setError('');
    try {
      const video = await createVideo(trimmed);
      navigate(`/videos/${video.id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-intro">
        <h1>選擇一支影片</h1>
        <p>貼上有英文字幕的 YouTube 網址。我們只抓字幕，影片仍由 YouTube 播放。</p>
      </div>

      <form className="import-form" onSubmit={onSubmit}>
        <label htmlFor="youtube-url">YouTube 網址</label>
        <div className="import-row">
          <input
            id="youtube-url"
            name="url"
            type="url"
            inputMode="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            required
          />
          <button type="submit" disabled={submitting}>
            {submitting ? '匯入中…' : '匯入'}
          </button>
        </div>
      </form>

      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? <p className="muted">正在載入影片…</p> : null}

      {!loading && videos.length === 0 ? (
        <p className="empty">還沒有影片。貼上一個有英文 CC 字幕的網址開始。</p>
      ) : null}

      <ul className="video-list">
        {videos.map((video) => (
          <li key={video.id}>
            <Link className="video-card" to={`/videos/${video.id}`}>
              <span className="video-title">{video.title || video.youtube_id}</span>
              <span className="video-meta">
                {sourceLabel(video.caption_source)} · {video.segment_count} 段
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
