import assert from 'node:assert/strict';
import test from 'node:test';

import { formatRange, formatTimestamp } from './time.js';

test('formats timestamps with one decimal', () => {
  assert.equal(formatTimestamp(0), '0:00.0');
  assert.equal(formatTimestamp(5), '0:05.0');
  assert.equal(formatTimestamp(10.24), '0:10.2');
  assert.equal(formatTimestamp(65.24), '1:05.2');
  assert.equal(formatTimestamp(59.96), '1:00.0');
  assert.equal(formatTimestamp(Number.NaN), '0:00.0');
});

test('formats a practice range', () => {
  assert.equal(formatRange(8.5, 16), '0:08.5–0:16.0');
});
