import { codeFromBody, messageFromBody } from './lib/errors.js';

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
  } catch {
    const error = new Error('無法連線到後端。請確認 API 已在連接埠 8000 執行。');
    error.code = 'network';
    throw error;
  }

  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const error = new Error(messageFromBody(body));
    error.code = codeFromBody(body);
    error.status = response.status;
    throw error;
  }
  return body;
}

export function listVideos() {
  return request('/api/videos');
}

export function getVideo(id) {
  return request(`/api/videos/${id}`);
}

export function createVideo(url) {
  return request('/api/videos', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}
