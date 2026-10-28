import assert from 'node:assert/strict';
import test from 'node:test';

import { codeFromBody, messageFromBody } from './errors.js';

test('reads the backend error message and code', () => {
  const body = { detail: { code: 'youtube_blocked', message: '無法從 YouTube 取得字幕。' } };
  assert.equal(messageFromBody(body), '無法從 YouTube 取得字幕。');
  assert.equal(codeFromBody(body), 'youtube_blocked');
});

test('reads validation errors', () => {
  assert.equal(messageFromBody({ detail: [{ msg: 'Field required' }] }), 'Field required');
  assert.equal(messageFromBody({}), '請求失敗，請稍後再試。');
});
