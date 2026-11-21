# Memory Experience V2 implementation progress

## Current state

The existing private Telegram diary, local narration, original media, signed authentication and one-command startup are retained. The new native-module frontend, isolated browser capture, emotional collections and persisted cross-day films are integrated. See ARCHITECTURE.md for module and data ownership.

## Verified in development

- Browser capture with text, a photograph, a link and a separate uploaded-audio scenario. Both preview and publish. The uploaded track played and a replacement link could be committed.
- Chromium exercised archive search, return navigation, reading and cover editing, Day Replay, Life Replay preview, pause, save, reopen and editing a saved film. Calendar and studio layouts were exercised at widths of 360, 430 and 1250 pixels, with a separate 390-pixel walkthrough.
- Two independent demo browser contexts saw different libraries. A foreign day and its media returned 404.
- A test aiogram dispatcher received a deep link, text, two photo messages, a song link and a track-character selection. Signed test launch data opened the private Mini App; a Piper sample, cover edit, publication callback, exact saved-day link, second edit, playback and return were exercised. A live human-operated Telegram client was not used.
- Migrations ran on isolated SQLite databases. Alembic reported head 0008 and no pending metadata differences. The frontend consists of native browser modules. It has no bundle step.
- Backend regressions cover ownership, draft media, saved-film source protection, recurring reminders, idempotent day publication and preserving a playable version through a failed edit.

## V2 delivery

- The common dark screening-room palette, editorial type, photo controls and paper reading surfaces are live across the dashboard, onboarding, studio, settings, archive, date views and both players. The latest-day poster has a selectable strip of the memory's actual photographs.
- Archive cards now have a direct playback action and a multi-selection action. Selecting three days in the archive opened exactly those three chapters in the film studio. Custom and empty historical periods were exercised.
- Day Replay Studio now persists shot order, photographic treatment, per-frame captions, camera intensity and a target duration. The walkthrough reordered photographs, selected a graphic treatment, disabled movement and requested 12 seconds. The previous scene remained available through preview. Reopening after confirmation reproduced the new order, treatment, 12-second duration and still frames.
- Ten backend tests passed, including concurrent-version checks, private media, source preservation, caption edits and studio persistence. The checked-in Playwright walkthrough passed. Additional browser runs exercised the three distinct original demo scenes, reduced motion, an invalid upload, empty search, retry after a service error, a song replacement, and a second edit of a saved film.
- The existing private service was restarted. Both its local and configured HTTPS origins served the updated shell with HTTP 200. Both denied anonymous film reads with HTTP 401. No test messages or browser-created memories were sent to real accounts.
- A selection of actual Chromium screenshots from the isolated fictional demo is in [the visual review](docs/design-review.jpg).

## Next device check

Open the existing bot in Telegram on Android or iOS, use its menu to launch the Mini App, open a Day Replay and a saved Life Replay, then return with Telegram's native back button. Browser and signed test-transport checks exercised these code paths. Physical-device audio policy and native system volume remain unverified.

## Scope

Both players produce interactive films. Video encoding/export, music streaming from commercial catalogues and linked-provider synchronization remain outside this implementation. Browser audio policy can require a tap to enable sound. The local analysis uses waveform cues; it does not identify individual instruments. A public installation with many visitors needs a retention policy for demo libraries. Clearing a demo cookie loses access to that browser library.
