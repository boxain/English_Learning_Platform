import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { getVideo } from '../api.js';
import { formatRange } from '../lib/time.js';

export function SegmentListPage() {
  const { id } = useParams();
  const [video, setVideo] = useState(null);
  const [error, setError] = useState('');

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

  if (error) {
    return (
      <div className="stack">
        <Link className="back-link" to="/">
          所有影片
        </Link>
        <p className="banner" role="alert">
          {error}
        </p>
      </div>
    );
  }

  if (!video) return <p className="muted">正在載入片段…</p>;

  const segments = [...video.segments].sort((a, b) => a.position - b.position);

  return (
    <div className="stack">
      <Link className="back-link" to="/">
        所有影片
      </Link>
      <div className="page-intro">
        <h1>{video.title || video.youtube_id}</h1>
        <p>{segments.length} 個跟讀片段。選一段開始，播放器只會播該段。</p>
      </div>
      {segments.length === 0 ? <p className="empty">這支影片沒有可練習的片段。</p> : null}
      <ol className="segment-list">
        {segments.map((segment) => (
          <li key={segment.id}>
            <Link className="segment-row" to={`/videos/${video.id}/segments/${segment.position}`}>
              <span className="segment-index">{segment.position + 1}</span>
              <span className="segment-copy">
                <span className="segment-time">{formatRange(segment.start_time, segment.end_time)}</span>
                <span className="segment-text">{segment.text}</span>
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
