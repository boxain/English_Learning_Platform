import assert from 'node:assert/strict';
import test from 'node:test';

import { chineseLine } from './subtitles.js';

test('shows cached Traditional Chinese when it exists', () => {
  const line = chineseLine({ translation_zh: ' 你好。 ' }, false);
  assert.equal(line.kind, 'translation');
  assert.equal(line.text, '你好。');
});

test('explains a missing key separately from a failed translation', () => {
  const missing = chineseLine({ translation_zh: null }, false);
  assert.equal(missing.kind, 'disabled');
  assert.match(missing.text, /OPENAI_API_KEY/);

  const pending = chineseLine({ translation_zh: '   ' }, true);
  assert.equal(pending.kind, 'pending');
  assert.match(pending.text, /重新整理/);
});
