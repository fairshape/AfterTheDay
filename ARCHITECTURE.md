# Memory Experience

## Runtime and ownership

One Python process runs FastAPI and, in private mode, aiogram polling and the anniversary dispatcher. FastAPI serves HTML, CSS, fonts and native JavaScript modules from the same origin. SQLite holds records and versioned JSON edits. Media bytes live in directories named after stable day IDs outside the static tree. Existing day URLs, IDs and scene versions retain their meaning.

The Telegram handshake verifies the launch signature and timestamp, then issues an eight-hour session. JSON requests carry the bearer token. For native image loading and seekable audio, the handshake also issues an HTTP-only, path-scoped media cookie. The client checks whether the cookie works for the current identity. WebViews that block it use authenticated blob requests. Each media read checks the asset against the owner's day. Music service URLs open at their provider.

Browser demo mode has a separate database. A random HTTP-only cookie identifies a browser's demo library. The six fictional source days are copied as metadata, with hard links to the bundled example media on the same filesystem. Editing one library keeps other browsers' copies independent. Losing the cookie starts a new library. The demo caps the number of issued libraries in `app/web/routes/demo.py`.

## Capture and publication

Telegram handlers and the four-step web capture screen use the same `Diary` and owner draft. `/api/capture` resumes that draft. Fields and upload routes check its revision, verify image or audio bytes and preserve photo order. Review calls the scene preview route. Publication checks the candidate token, switches the saved version atomically, then notifies the bot. The published ID equals the draft ID.

Cover, favorite-frame, narration, soundtrack and metadata edits have explicit commit actions. A soundtrack replacement builds a candidate with the existing story and photographs. Prior uploaded tracks referenced by older films remain addressable through the owning day. Deleting a published day also removes its media and anniversary records. A foreign key protects source days while a saved Life Replay uses them.

## Emotional and visual engine

| Input | Decision | Source |
| --- | --- | --- |
| Story, explicit detail and mood tags | Opening, key phrase, final hold and overlapping emotional collections | `app/services/story.py`, `anniversaries.py`, `emotion.py` |
| Image thumbnails | Sampled cover field, shadow, contrast-safe foreground and accent | `app/services/palette.py` |
| Uploaded track | Bounded local waveform analysis, candidate cut times and an excerpt offset | `app/infrastructure/audio/analysis.py`, `app/services/timing.py` |
| Track link or weak measurements | Character-based cut spacing, transitions and camera movement | `app/services/scene.py` |
| User corrections | Cover style, main photo, tags, music cue, quote and voice settings | `app/services/diary.py`, `voice_workflow.py` |

The engine's normalized dimensions describe artistic choices. An unclassified day can have no primary emotion. New scenes store the interpretation together with their frames. Measured energy and confirmed tags adjust the camera gain, transition multiplier and caption entrance. Explicit stillness and manual motion settings take precedence. `app/services/studio.py` defines the photographic treatment, camera override and montage order. A requested length of 8–45 seconds is limited by usable audio. Shot order is independent of original upload order. Legacy scenes and subsequently corrected labels can derive it from saved inputs. Machine learning credentials are unnecessary. Local Piper speech and FFmpeg mixing remain optional integrations.

## Two replay formats

**Day Replay** reads the saved frame order, crops, caption timing, transitions, excerpt and narration mix. Uploaded audio supplies the playback clock. A linked day uses a visual clock and an external song action.

**Life Replay** accepts two to twenty distinct published days owned by the same user. The studio proposes a shortlist, then allows selection, order, caption, duration and soundtrack changes. The assembler builds chapters from each day's opening and key frame, budgets time for the caption and looks for nearby measured accents where applicable. The score can follow chapters, use one authorized local track or be silent. A saved film snapshots the resulting shots and settings. Editing it uses a revision check. `film_sources` links it to the original days. `life_films` contains no media bytes.

## Frontend

`experience.js` owns session setup, routes, Telegram back handling and the shared-photo transition. `museum.js` provides dashboard and preview components. `screens.js` owns collections, chronology, search and studio selection. `capture.js` manages draft entry. `folder.js`, `sheet.js`, `scene-tools.js`, `remix.js` and `voice.js` handle the editing surfaces. The day and cross-day players live in `player.js` and `life-player.js`. The cross-day editor lives in `life.js`. The default route renders the personal Memory Table. `web/scripts/memory-table.js` composes its spreads, the full note and the cover preview. `web/styles/table.css` owns the desk, paper materials and responsive compositions. The shelf remains available as a secondary feed. `app/services/emotion.py` separates camera character from musical energy; the diary records a print layout using up to four previous scenes owned by the same user. Base components live in `web/styles/museum.css`, with reusable media, cover and motion styles in the same directory.

## Schema upgrades

Revision 0007 adds saved films. Revision 0008 adds indexed source foreign keys and backfills films already created at 0007. Existing diary tables and original media do not require conversion. Keep the database and the entire media directory together when backing up. See the README for launch commands and the asset credits in `docs/product.md`.
