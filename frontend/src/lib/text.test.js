import assert from 'node:assert/strict';
import test from 'node:test';

import { practiceText } from './text.js';

test('removes lyric note markers', () => {
  assert.equal(practiceText('♪ Hello there. ♪'), 'Hello there.');
  assert.equal(practiceText('  '), '');
  assert.equal(practiceText(null), '');
});
