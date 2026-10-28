import assert from 'node:assert/strict';
import test from 'node:test';

import { PLAYING, shouldPauseAtEnd } from './playback.js';

test('pauses at the segment end while playing', () => {
  assert.equal(
    shouldPauseAtEnd({ currentTime: 15, endTime: 15, playerState: PLAYING }),
    true,
  );
  assert.equal(
    shouldPauseAtEnd({ currentTime: 14.96, endTime: 15, playerState: PLAYING }),
    true,
  );
});

test('keeps playing before the end, when paused, or during replay seek', () => {
  assert.equal(
    shouldPauseAtEnd({ currentTime: 14.9, endTime: 15, playerState: PLAYING }),
    false,
  );
  assert.equal(
    shouldPauseAtEnd({ currentTime: 20, endTime: 15, playerState: 2 }),
    false,
  );
  assert.equal(
    shouldPauseAtEnd({
      currentTime: 20,
      endTime: 15,
      playerState: PLAYING,
      now: 1000,
      suppressUntil: 1500,
    }),
    false,
  );
});
