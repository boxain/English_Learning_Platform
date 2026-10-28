import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizePlaybackRate } from './youtube.js';

test('keeps only the three practice speeds', () => {
  assert.equal(normalizePlaybackRate('0.8'), 0.8);
  assert.equal(normalizePlaybackRate('0.9'), 0.9);
  assert.equal(normalizePlaybackRate('1'), 1);
  assert.equal(normalizePlaybackRate('0.75'), 1);
  assert.equal(normalizePlaybackRate('nope'), 1);
});
